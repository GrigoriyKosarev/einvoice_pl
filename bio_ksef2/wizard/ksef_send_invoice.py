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
            'date_of_receipt_by_buyer': invoice.date_of_receipt_by_buyer.strftime('%Y-%m-%d') if invoice.date_of_receipt_by_buyer else None,
            'ref': invoice.ref if invoice.ref else '',
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
                'gln': invoice.company_id.partner_id.gln_code or '',
            },

            # Buyer data (customer)
            'buyer': {
                'nip': invoice.partner_id.vat,
                'name': invoice.partner_id.name,
                'street': invoice.partner_id.street or '',
                'city': invoice.partner_id.city or '',
                'zip': invoice.partner_id.zip or '',
                'country': invoice.partner_id.country_id.code or 'PL',
                'gln': invoice.partner_id.gln_code or '',
            },

            # Invoice lines
            'lines': [],

            # Totals
            'total_net': 0.0,
            'total_vat': 0.0,
            'total_gross': invoice.amount_total,

            # Payment term - will be set below if exists
            'payment_term': None,

            # Delivery note number (WZ) from stock picking
            'delivery_note_number': invoice.delivery_note_number or '',
        }

        # Parse payment term from invoice
        if invoice.invoice_payment_term_id:
            # Get payment term name in Polish for KSeF
            payment_term_pl = invoice.invoice_payment_term_id.with_context(lang='pl_PL')
            payment_term_name = payment_term_pl.name
            # Try to extract number of days from payment term name
            # Examples: "14 dni", "30 Days", "Natychmiast", "7 days net"
            import re
            days_match = re.search(r'(\d+)', payment_term_name)
            if days_match:
                days = int(days_match.group(1))

                invoice_data['payment_term'] = {
                    'days': days,
                    'unit': 'dni',  # Always use Polish for KSeF
                    'event': 'wystawienie faktury',  # Default: invoice issue
                    'due_date': invoice.invoice_date_due.strftime('%Y-%m-%d') if invoice.invoice_date_due else None,
                }

        sale_order_ids = invoice.mapped('invoice_line_ids.sale_line_ids.order_id')
        sale_order_id = sale_order_ids[0] if sale_order_ids else None
        if sale_order_id:
            # Format date as YYYY-MM-DD for FA(3) DataZamowienia (TDataU type)
            invoice_data['order_date'] = sale_order_id.date_order.strftime('%Y-%m-%d')

        # Delivery address (Podmiot3) - if different from invoice partner
        # IMPORTANT: Get delivery address ONLY from invoice, not from sale order
        # This ensures delivery address is explicitly set and controlled
        if hasattr(invoice, 'partner_shipping_id') and invoice.partner_shipping_id:
            delivery_partner = invoice.partner_shipping_id

            # Add delivery address only if it differs from invoice partner
            if delivery_partner != invoice.partner_id:
                invoice_data['delivery_address'] = {
                    'name': delivery_partner.name,
                    'street': delivery_partner.street or '',
                    'city': delivery_partner.city or '',
                    'zip': delivery_partner.zip or '',
                    'country': delivery_partner.country_id.code if delivery_partner.country_id else 'PL',
                    'nip': delivery_partner.vat or '',
                    'gln': delivery_partner.gln_code or '',  # GLN from dedicated field
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
            # P_7 - Product name (internal product name, NOT customer name)
            product_name = line.name or line.product_id.name or 'Product/Service'

            # Indeks - Internal product code (NOT customer code)
            product_index = line.product_id.default_code or ""

            # GTIN - Barcode (clean trailing special characters like "._")
            product_gtin = ""
            if line.product_id.barcode:
                # Remove trailing special characters (e.g., "342342._" -> "342342")
                import re
                product_gtin = re.sub(r'[._\-\s]+$', '', line.product_id.barcode)

            # Customer-specific product info (for DodatkowyOpis)
            customer_product_code = ""
            customer_product_name = ""
            try:
                # Try to get customer-specific product info if available
                customer_product_code = line.sh_line_customer_code or ""
                customer_product_name = line.sh_line_customer_product_name or ""
            except AttributeError:
                # Fields not available in this Odoo setup
                pass

            # Position identifier (IdentyfikatorPozycji) - only for Auchan (VAT=5260309174)
            # Check VAT of delivery address (partner_shipping_id), not main buyer
            position_identifier = None
            buyer_vat = ""
            if hasattr(invoice, 'partner_shipping_id') and invoice.partner_shipping_id:
                buyer_vat = invoice.partner_shipping_id.vat or ""

            # Clean VAT number (remove PL prefix, spaces, etc.)
            buyer_vat_clean = buyer_vat.replace('PL', '').replace('pl', '').replace(' ', '').replace('-', '').strip()

            if buyer_vat_clean == '5260309174':  # Auchan
                # Map product type to position identifier
                # CU = Storable (consu/product), SER = Service, RC = returnable packaging
                if line.product_id.type == 'service':
                    position_identifier = 'SER'
                elif line.product_id.type in ('product', 'consu'):
                    position_identifier = 'CU'
                # RC (returnable packaging) - not implemented yet

            # Logistics activity code (AktywnoscLogistyczna) from delivery address
            logistics_code = None
            if hasattr(invoice, 'partner_shipping_id') and invoice.partner_shipping_id:
                logistics_code = invoice.partner_shipping_id.ksef_code or None

            # Calculate discount for P_10 field
            discount_percent = line.discount if line.discount else 0.0
            discount_amount = 0.0
            original_price = line.price_unit

            if discount_percent > 0:
                # Calculate total discount amount for this line
                discount_amount = line.price_unit * line.quantity - line.price_subtotal

            # Determine procedure
            # Note: WDT (intra-EU supply) does NOT use the Procedura field.
            # It's indicated by P_13_6_2 in VAT summary and P_19/P_19A annotations.
            procedure = None

            # For other special procedures, detect them here:
            # buyer_country = invoice.partner_id.country_id.code if invoice.partner_id.country_id else 'PL'
            # if special_case:
            #     procedure = 'I_42'  # or other valid procedure code

            line_data = {
                'name': product_name,
                'index': product_index,
                'gtin': product_gtin,  # GTIN barcode
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
                'customer_product_code': customer_product_code,  # For DodatkowyOpis
                'customer_product_name': customer_product_name,  # For DodatkowyOpis
                'position_identifier': position_identifier,  # For DodatkowyOpis - Auchan only
                'logistics_code': logistics_code,  # For DodatkowyOpis - from delivery address
            }

            invoice_data['lines'].append(line_data)
            invoice_data['total_net'] += line.price_subtotal

        # Calculate total VAT
        invoice_data['total_vat'] = invoice_data['total_gross'] - invoice_data['total_net']

        # NOTE: For foreign currency invoices, we keep PLN equivalents for internal accounting
        # However, in KSeF XML:
        # - P_13_*, P_14_*, P_15 remain in document currency (e.g., EUR)
        # - Only P_14_*W fields contain VAT converted to PLN (per art. 106e ust. 11)
        if is_foreign_currency:
            invoice_data['total_net_pln'] = invoice_data['total_net'] * currency_rate
            invoice_data['total_vat_pln'] = invoice_data['total_vat'] * currency_rate
            invoice_data['total_gross_pln'] = invoice_data['total_gross'] * currency_rate
        else:
            invoice_data['total_net_pln'] = invoice_data['total_net']
            invoice_data['total_vat_pln'] = invoice_data['total_vat']
            invoice_data['total_gross_pln'] = invoice_data['total_gross']

        # Determine invoice type (RodzajFaktury)
        if invoice.move_type == 'out_refund':
            # Credit note (Faktura Korygująca)
            invoice_data['rodzaj_faktury'] = 'KOR'

            # Add credit note specific data
            # Use standard 'ref' field for correction reason
            invoice_data['correction_reason'] = invoice.ref or 'Korekta'
            invoice_data['correction_type'] = invoice.ksef_correction_type or '2'

            # Get original invoice data (reversed_entry_id is Odoo's field for original invoice)
            # DaneFaKorygowanej is REQUIRED for KOR invoices!
            if not invoice.reversed_entry_id:
                raise UserError(
                    f'Credit note {invoice.name} has no reference to the original invoice!\n'
                    f'Field "reversed_entry_id" is required for sending credit notes to KSeF.\n'
                    f'Create credit note using "Credit Note" button on the original invoice.'
                )

            corrected_invoices = [{
                'date': invoice.reversed_entry_id.invoice_date.strftime('%Y-%m-%d') if invoice.reversed_entry_id.invoice_date else issue_date,
                'number': invoice.reversed_entry_id.name,
                'ksef_number': invoice.reversed_entry_id.ksef_number if invoice.reversed_entry_id.ksef_number else None,
            }]
            invoice_data['corrected_invoices'] = corrected_invoices
        else:
            # Regular invoice
            invoice_data['rodzaj_faktury'] = 'VAT'

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

            # Get fa_version from config
            fa_version = config.fa_version or 'FA2'

            # Open session with fa_version
            session = ksef_invoice.InvoiceSession(config.api_url, auth_client.token, fa_version=fa_version)
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

                # Build detailed error message including details array
                status_description = status_info.get('description', '')
                details = status_info.get('details', [])
                if details:
                    details_str = '\n\n' + '\n'.join(f'• {detail}' for detail in details)
                    status_description += details_str

                vals.update({
                    'ksef_status_code': status_info.get('code'),
                    'ksef_status_description': status_description,
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
