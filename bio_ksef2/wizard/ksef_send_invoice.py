# -*- coding: utf-8 -*-
"""Wizard for sending invoices to KSeF"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class KSefSendInvoice(models.TransientModel):
    _name = 'ksef.send.invoice'
    _description = 'Send Invoice to KSeF'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        readonly=True,
    )
    invoice_xml = fields.Text(
        string='Invoice XML (Preview)',
        readonly=True,
        compute='_compute_invoice_xml',
    )

    @api.depends('invoice_id')
    def _compute_invoice_xml(self):
        """Generate invoice XML preview"""
        for wizard in self:
            if wizard.invoice_id:
                wizard.invoice_xml = self._generate_invoice_xml(wizard.invoice_id)
            else:
                wizard.invoice_xml = ''

    def _generate_invoice_xml(self, invoice):
        """Generate FA_VAT XML for invoice"""
        from ..ksef_client.invoice import create_sample_invoice_xml
        from datetime import datetime

        # Extract data from invoice
        if not invoice.partner_id.vat:
            raise UserError(_('Customer must have a valid NIP (VAT number)'))

        if not invoice.company_id.vat:
            raise UserError(_('Company must have a valid NIP (VAT number)'))

        # Clean NIP (remove PL prefix if present)
        seller_nip = invoice.company_id.vat.replace('PL', '').replace('pl', '')
        buyer_nip = invoice.partner_id.vat.replace('PL', '').replace('pl', '')

        # Calculate totals
        # net_amount = sum(line.price_subtotal for line in invoice.invoice_line_ids)
        net_amount = invoice.amount_untaxed
        gross_amount = invoice.amount_total
        vat_amount = invoice.amount_tax
        # Get VAT rate (use first line's VAT rate)
        vat_rate = 0  # Default
        for line in invoice.invoice_line_ids:
            tax = line.tax_ids.filtered(lambda t: t.amount_type == 'percent')
            if tax:
                vat_rate = tax[0].amount
                break

        # Generate XML
        return create_sample_invoice_xml(
            invoice_number=invoice.name,
            seller_nip=seller_nip,
            seller_name=invoice.company_id.name,
            buyer_nip=buyer_nip,
            buyer_name=invoice.partner_id.name,
            net_amount=float(net_amount),
            gross_amount=float(vat_amount),
            vat_amount=float(net_amount),
            vat_rate=vat_rate,
            issue_date=invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else None,
        )

    def action_send(self):
        """Send invoice to KSeF"""
        self.ensure_one()

        try:
            from ..ksef_client import auth, invoice as ksef_invoice

            # Get config
            config = self.env['ksef.config'].get_config(self.invoice_id.company_id.id)

            _logger.info(f'Sending invoice {self.invoice_id.name} to KSeF...')

            # Authenticate
            auth_client = auth.Auth(config.api_url, config.ksef_token)
            if not auth_client.token:
                raise UserError(_('Failed to authenticate with KSeF API'))

            # Generate invoice XML
            invoice_xml = self._generate_invoice_xml(self.invoice_id)

            # Open session
            session = ksef_invoice.InvoiceSession(config.api_url, auth_client.token)
            if not session.open():
                raise UserError(_('Failed to open KSeF session'))

            # Send invoice
            result = session.send_invoice(invoice_xml)

            if not result:
                session.close()
                raise UserError(_('Failed to send invoice to KSeF'))

            # Get reference number
            invoice_ref = result.get('referenceNumber') or result.get('invoiceReferenceNumber')

            # Check status
            import time
            time.sleep(2)  # Give server time to process
            status = session.get_invoice_status(invoice_ref)

            # Close session
            session.close()

            # Update invoice
            vals = {
                'ksef_reference': invoice_ref,
                'ksef_sent_date': fields.Datetime.now(),
                'ksef_status': 'pending',
            }

            if status:
                status_info = status.get('status', {})
                vals.update({
                    'ksef_status_code': status_info.get('code'),
                    'ksef_status_description': status_info.get('description'),
                    'ksef_number': status.get('ksefNumber'),
                })

                if status_info.get('code') == 200:
                    vals['ksef_status'] = 'accepted'
                elif status_info.get('code', 0) >= 400:
                    vals['ksef_status'] = 'rejected'

            self.invoice_id.write(vals)

            # Prepare message
            if vals.get('ksef_status') == 'accepted':
                message = _('Invoice successfully sent to KSeF!\nKSeF Number: %s') % self.invoice_id.ksef_number
                msg_type = 'success'
            elif vals.get('ksef_status') == 'rejected':
                message = _('Invoice rejected by KSeF!\nReason: %s') % self.invoice_id.ksef_status_description
                msg_type = 'danger'
            else:
                message = _('Invoice sent to KSeF for processing.\nReference: %s') % self.invoice_id.ksef_reference
                msg_type = 'info'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('KSeF Submission'),
                    'message': message,
                    'type': msg_type,
                    'sticky': True,
                }
            }

        except Exception as e:
            _logger.error(f'Failed to send invoice to KSeF: {e}', exc_info=True)
            raise UserError(_('Failed to send invoice to KSeF: %s') % str(e))
