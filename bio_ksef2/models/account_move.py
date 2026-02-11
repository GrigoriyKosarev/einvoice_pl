# -*- coding: utf-8 -*-
"""Account Move Extension for KSeF"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    ksef_number = fields.Char(
        string='KSeF Number',
        readonly=True,
        copy=False,
        help='KSeF invoice number assigned after successful submission',
    )
    ksef_reference = fields.Char(
        string='KSeF Reference',
        readonly=True,
        copy=False,
        help='KSeF reference number from submission',
    )
    ksef_status = fields.Selection(
        [
            ('draft', 'Not Sent'),
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        string='KSeF Status',
        default='draft',
        readonly=True,
        copy=False,
    )
    ksef_status_code = fields.Integer(
        string='KSeF Status Code',
        readonly=True,
        copy=False,
    )
    ksef_status_description = fields.Text(
        string='KSeF Status Description',
        readonly=True,
        copy=False,
    )
    ksef_sent_date = fields.Datetime(
        string='KSeF Sent Date',
        readonly=True,
        copy=False,
    )

    has_ksef_config = fields.Boolean(
        string='Has KSeF Configuration',
        related='company_id.has_ksef_config',
        store=False,
        readonly=True,
        help='Indicates if the company has KSeF configuration',
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        copy=False,
        help='Delivery note number from stock picking (for KSeF WZ field)',
    )

    # Credit note (Faktura Korygująca) fields
    # Note: Standard 'ref' field is used for correction reason (PrzyczynaKorekty)
    ksef_correction_type = fields.Selection(
        [
            ('1', 'W dacie faktury pierwotnej (effective from original invoice date)'),
            ('2', 'W dacie faktury korygującej (effective from credit note date)'),
            ('3', 'W innej dacie (effective from other date)'),
        ],
        string='KSeF Correction Type',
        default='2',
        help='Typ skutku korekty w ewidencji VAT (TypKorekty)',
        copy=False,
    )

    def action_send_to_ksef(self):
        """Send invoice to KSeF"""
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                raise UserError(_('Only customer invoices can be sent to KSeF'))

            if move.state != 'posted':
                raise UserError(_('Only posted invoices can be sent to KSeF'))

            if move.ksef_number:
                raise UserError(_('Invoice already sent to KSeF with number: %s') % move.ksef_number)

            # Open wizard
            return {
                'name': _('Send to KSeF'),
                'type': 'ir.actions.act_window',
                'res_model': 'ksef.send.invoice',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_invoice_id': move.id,
                },
            }

    def action_check_ksef_status(self):
        """Check KSeF invoice status"""
        self.ensure_one()

        if not self.ksef_reference:
            raise UserError(_('No KSeF reference found for this invoice'))

        try:
            from ..ksef_client import auth, invoice as ksef_invoice

            # Get config
            config = self.env['ksef.config'].get_config(self.company_id.id)

            # Authenticate
            auth_client = auth.Auth(config.api_url, config.ksef_token)
            if not auth_client.token:
                raise UserError(_('Failed to authenticate with KSeF API'))

            # Open session and check status
            session = ksef_invoice.InvoiceSession(config.api_url, auth_client.token)
            if not session.open():
                raise UserError(_('Failed to open KSeF session'))

            status = session.get_invoice_status(self.ksef_reference)
            session.close()

            if status:
                status_info = status.get('status', {})

                # Build detailed error message including details array
                status_description = status_info.get('description', '')
                details = status_info.get('details', [])
                if details:
                    details_str = '\n\n' + '\n'.join(f'• {detail}' for detail in details)
                    status_description += details_str

                self.write({
                    'ksef_status_code': status_info.get('code'),
                    'ksef_status_description': status_description,
                    'ksef_number': status.get('ksefNumber'),
                })

                if status_info.get('code') == 200:
                    self.ksef_status = 'accepted'
                    message = _('KSeF Status: Accepted\nKSeF Number: %s') % self.ksef_number
                elif status_info.get('code', 0) >= 400:
                    self.ksef_status = 'rejected'
                    message = _('KSeF Status: Rejected\n%s') % self.ksef_status_description
                else:
                    self.ksef_status = 'pending'
                    message = _('KSeF Status: %s') % self.ksef_status_description

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('KSeF Status'),
                        'message': message,
                        'type': 'success' if self.ksef_status == 'accepted' else 'warning',
                        'sticky': True,
                    }
                }
            else:
                raise UserError(_('Failed to get status from KSeF'))

        except Exception as e:
            _logger.error(f'KSeF status check failed: {e}')
            raise UserError(_('Status check failed: %s') % str(e))

    @api.model
    def _cron_check_ksef_pending(self):
        """Cron job to check status of pending KSeF invoices"""
        pending_invoices = self.search([
            ('ksef_status', '=', 'pending'),
            ('ksef_reference', '!=', False),
        ])

        _logger.info(f'Checking {len(pending_invoices)} pending KSeF invoices')

        for invoice in pending_invoices:
            try:
                invoice.action_check_ksef_status()
            except Exception as e:
                _logger.error(f'Failed to check KSeF status for invoice {invoice.name}: {e}')

    def _get_delivery_note_number(self):
        """Get delivery note number from last stock picking of related sale order"""
        self.ensure_one()

        # Get sale order from invoice lines
        sale_orders = self.mapped('invoice_line_ids.sale_line_ids.order_id')
        if not sale_orders:
            return False

        # Get last delivery (stock.picking) from sale order
        sale_order = sale_orders[0]
        pickings = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
        ).sorted(key=lambda p: p.date_done, reverse=True)

        if pickings:
            return pickings[0].name

        return False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-populate delivery_note_number"""
        moves = super(AccountMove, self).create(vals_list)

        for move in moves:
            if move.move_type in ('out_invoice', 'out_refund') and not move.delivery_note_number:
                delivery_note = move._get_delivery_note_number()
                if delivery_note:
                    move.delivery_note_number = delivery_note

        return moves
