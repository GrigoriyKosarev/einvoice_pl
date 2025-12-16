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
                self.write({
                    'ksef_status_code': status_info.get('code'),
                    'ksef_status_description': status_info.get('description'),
                    'ksef_number': status.get('ksefNumber'),
                })

                if status_info.get('code') == 200:
                    self.ksef_status = 'accepted'
                    message = _('KSeF Status: Accepted\nKSeF Number: %s') % self.ksef_number
                elif status_info.get('code', 0) >= 400:
                    self.ksef_status = 'rejected'
                    details = status_info.get('details', [])
                    details_str = '\n'.join(details) if details else ''
                    message = _('KSeF Status: Rejected\nReason: %s\nDetails: %s') % (
                        status_info.get('description'),
                        details_str
                    )
                else:
                    self.ksef_status = 'pending'
                    message = _('KSeF Status: %s') % status_info.get('description')

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
