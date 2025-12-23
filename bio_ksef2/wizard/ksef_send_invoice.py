# -*- coding: utf-8 -*-
"""Wizard for sending invoices to KSeF"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
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
        from ..ksef_client.xml_generator import generate_fa_vat_xml

        # Validate data
        if not invoice.partner_id.vat:
            raise UserError(_('Customer must have a valid NIP (VAT number)'))
        if not invoice.company_id.vat:
            raise UserError(_('Company must have a valid NIP (VAT number)'))

        company_lang = 'pl_PL'
        issue_date = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else datetime.today().strftime('%Y-%m-%d')

        # Get currency exchange rate
        # Odoo already calculates and stores currency_rate in invoice
        is_foreign_currency = invoice.currency_id != invoice.company_id.currency_id
        currency_rate = invoice.currency_rate if is_foreign_currency else None

        # Prepare invoice data
        invoice_data = {
            'invoice_number': invoice.name,
            'issue_date': issue_date,
            'sale_date': issue_date,
            'payment_date': invoice.invoice_date_due.strftime('%Y-%m-%d') if invoice.invoice_date_due else issue_date,
            'currency': invoice.currency_id.name or 'PLN',
            'currency_rate': currency_rate if is_foreign_currency else None,
            'is_foreign_currency': is_foreign_currency,

            # Seller data (company)
            'seller': {
                'nip': invoice.company_id.vat,
                'name': invoice.company_id.name,
                'street': invoice.company_id.street or '',
                'city': invoice.company_id.city or '',
                'zip': invoice.company_id.zip or '',
                'country': invoice.company_id.country_id.code or 'PL',
            },

            # Buyer data (customer)
            'buyer': {
                'nip': invoice.partner_id.vat,
                'name': invoice.partner_id.name,
                'street': invoice.partner_id.street or '',
                'city': invoice.partner_id.city or '',
                'zip': invoice.partner_id.zip or '',
                'country': invoice.partner_id.country_id.code or 'PL',
            },

            # Invoice lines
            'lines': [],

            # Totals
            'total_net': 0.0,
            'total_vat': 0.0,
            'total_gross': invoice.amount_total,
        }

        # Process invoice lines
        for line in invoice.invoice_line_ids:
            if line.display_type != 'product':  # Skip section/note lines
                continue

            # Get VAT rate
            vat_rate = 23  # Default
            if line.tax_ids:
                vat_rate = int(line.tax_ids[0].amount) if line.tax_ids[0].amount else 0

            # Get unit of measure in Polish (required by KSeF)
            unit = line.product_uom_id.with_context(lang=company_lang).name if line.product_uom_id else 'szt'

            # product_name = product_name.replace('[', '').replace(']', '')
            try:
                product_name = line.sh_line_customer_product_name or line.name or line.product_id.name or 'Product/Service'
            except:
                product_name = line.name or line.product_id.name or 'Product/Service'

            try:
                product_index = line.sh_line_customer_code or line.product_id.default_code or ""
            except:
                product_index = line.product_id.default_code or ""

            # Calculate discount for P_10 field
            discount_percent = line.discount if line.discount else 0.0
            discount_amount = 0.0
            original_price = line.price_unit

            if discount_percent > 0:
                # Calculate total discount amount for this line
                discount_amount = line.price_unit * line.quantity - line.price_subtotal

            # Determine procedure (WDT for intra-EU supply with 0% VAT)
            procedure = None
            buyer_country = invoice.partner_id.country_id.code if invoice.partner_id.country_id else 'PL'
            eu_countries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']

            # WDT - Wewnątrzwspólnotowa Dostawa Towarów (Intra-EU supply of goods)
            if buyer_country != 'PL' and buyer_country in eu_countries and vat_rate == 0:
                procedure = 'WDT'

            line_data = {
                'name': product_name,
                'index': product_index,
                'quantity': line.quantity,
                'unit': unit,
                'price_unit': original_price,  # P_9A - original price before discount (in invoice currency)
                'discount_amount': discount_amount,  # P_10 - discount amount (in invoice currency)
                'net_amount': line.price_subtotal,  # P_11 - final amount after discount (in invoice currency)
                'vat_rate': vat_rate,
                'vat_amount': line.price_total - line.price_subtotal,
                'gross_amount': line.price_total,
                'currency_rate': currency_rate if is_foreign_currency else None,  # Exchange rate for this line
                'procedure': procedure,  # WDT, EE, etc.
            }

            invoice_data['lines'].append(line_data)
            invoice_data['total_net'] += line.price_subtotal

        # Calculate total VAT
        invoice_data['total_vat'] = invoice_data['total_gross'] - invoice_data['total_net']

        # IMPORTANT: If foreign currency, convert totals to PLN for KSeF
        # According to Polish VAT law, summary fields P_13_X, P_14_X, P_15 must be in PLN
        if is_foreign_currency:
            invoice_data['total_net_pln'] = invoice_data['total_net'] * currency_rate
            invoice_data['total_vat_pln'] = invoice_data['total_vat'] * currency_rate
            invoice_data['total_gross_pln'] = invoice_data['total_gross'] * currency_rate
        else:
            invoice_data['total_net_pln'] = invoice_data['total_net']
            invoice_data['total_vat_pln'] = invoice_data['total_vat']
            invoice_data['total_gross_pln'] = invoice_data['total_gross']

        # Get config to determine format version
        config = self.env['ksef.config'].get_config(invoice.company_id.id)
        format_version = config.fa_version or 'FA2'

        # Generate XML
        return generate_fa_vat_xml(invoice_data, format_version=format_version)

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
