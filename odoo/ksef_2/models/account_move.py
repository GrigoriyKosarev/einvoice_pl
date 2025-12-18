# models/account_move.py
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    ksef_session_id = fields.Char(
        string='KSeF Session ID',
        copy=False,
        help='Identifier of the interactive session in KSeF through which the invoice was sent.'
    )
    ksef_invoice_id = fields.Char(
        string='KSeF Technical Invoice ID',
        copy=False,
        help='Technical identifier returned by KSeF when the invoice is accepted for processing. Use this to check processing status.'
    )
    ksef_invoice_number = fields.Char(
        string='KSeF Invoice Number',
        copy=False,
        help='Unique KSeF number assigned to the invoice when it is fully processed in KSeF.'
    )
    ksef_state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('error', 'Error'),
    ], string='KSeF Status', default='draft', copy=False)

    # --- ADDED: extra fields for session closure and UPO attachment ---
    ksef_session_closed = fields.Boolean(
        string='KSeF Session Closed',
        copy=False,
        help='True if the interactive KSeF session has been closed.'
    )
    ksef_upo_attachment_id = fields.Many2one(
        'ir.attachment',
        string='KSeF UPO Attachment',
        copy=False,
        help='Attachment created from KSeF UPO for this session.'
    )

    def action_ksef_send(self):
        """Send selected invoices to KSeF.

        Steps performed:
            1. Open interactive session with KSeF (``ksefSessionOpen``) to obtain ``sessionId``.
            2. Generate XML content of the invoice using a helper method.
            3. Send the XML invoice to KSeF using ``ksefInvoiceSend``.
            4. Store returned technical identifier in ``ksef_invoice_id`` and session ID.
        """
        for invoice in self:
            if invoice.move_type not in ('out_invoice', 'out_refund'):
                raise UserError(_('Only customer invoices and credit notes can be sent to KSeF.'))
            company = invoice.company_id
            # Ensure an access token is configured
            if not company.ksef_access_token:
                raise UserError(_('Please configure a KSeF access token on the company.'))
            # Generate invoice XML.  For demonstration this produces a simplified FA(3)
            # structure.  In production ensure the XML complies with the official schema.
            xml_data = invoice._prepare_ksef_invoice_xml()
            # Open an online session and send the invoice
            session_id = self.env['ksef.service'].open_session(company)
            inv_ref = self.env['ksef.service'].send_invoice(company, session_id, xml_data)
            invoice.ksef_session_id = session_id
            # Store the invoice reference number returned by KSeF
            invoice.ksef_invoice_id = inv_ref if isinstance(inv_ref, str) else (inv_ref or '')
            invoice.ksef_state = 'sent'
            # Reset flags for session closure and UPO attachment
            invoice.ksef_session_closed = False
            invoice.ksef_upo_attachment_id = False
        return True

    def _prepare_ksef_invoice_xml(self):
        """Prepare a simplified structured invoice XML for demonstration.

        This method generates a very basic XML structure containing invoice fields.
        For production use, this function should produce an XML compliant with
        the FA_v2 or FA_v3 logical structure expected by KSeF. The KSeF REST API
        also provides an operation ``ksefInvoiceGenerate`` that can generate XML
        based on provided invoice data.
        """
        self.ensure_one()
        import xml.etree.ElementTree as ET
        inv = ET.Element('Invoice')
        # Basic header
        ET.SubElement(inv, 'Number').text = self.name or ''
        ET.SubElement(inv, 'Date').text = self.invoice_date.strftime('%Y-%m-%d') if self.invoice_date else ''
        # Seller and buyer information
        seller = ET.SubElement(inv, 'Seller')
        ET.SubElement(seller, 'Name').text = self.company_id.name
        ET.SubElement(seller, 'VatNumber').text = self.company_id.vat or ''
        buyer = ET.SubElement(inv, 'Buyer')
        partner = self.partner_id
        ET.SubElement(buyer, 'Name').text = partner.name
        ET.SubElement(buyer, 'VatNumber').text = partner.vat or ''
        # Lines
        lines_elem = ET.SubElement(inv, 'Lines')
        for line in self.invoice_line_ids:
            if line.display_type in ('line_section', 'line_note'):
                continue
            ln = ET.SubElement(lines_elem, 'Line')
            ET.SubElement(ln, 'Description').text = line.name or ''
            ET.SubElement(ln, 'Quantity').text = str(line.quantity)
            ET.SubElement(ln, 'UnitPrice').text = str(line.price_unit)
            ET.SubElement(ln, 'PriceSubtotal').text = str(line.price_subtotal)
        # Total
        ET.SubElement(inv, 'TotalAmount').text = str(self.amount_total)
        xml_bytes = ET.tostring(inv, encoding='utf-8')
        return xml_bytes

    def action_ksef_check_status(self):
        """Check the processing status of invoices in KSeF.

        After sending an invoice, you can call the KSeF API to check whether
        the invoice has been accepted and obtain the official KSeF number using
        the ``ksefInvoiceStatus`` operation. This method updates
        ``ksef_state`` and ``ksef_invoice_number`` based on the response.
        """
        for invoice in self:
            if not invoice.ksef_invoice_id or not invoice.ksef_session_id:
                continue
            company = invoice.company_id
            status = self.env['ksef.service'].invoice_status(company, invoice.ksef_session_id, invoice.ksef_invoice_id)
            # Interpret the response.  If a final KSeF number is present, mark as accepted.
            ksef_number = status.get('ksefNumber') or status.get('invoiceNumber') or status.get('ksefInvoiceNumber')
            processing_status = (status.get('status') or status.get('processingStatus') or '').lower()
            if ksef_number:
                invoice.ksef_state = 'accepted'
                invoice.ksef_invoice_number = ksef_number
            elif processing_status in ('processing', 'in_progress', 'pending'):
                invoice.ksef_state = 'sent'
            else:
                invoice.ksef_state = 'error'
        return True

    # --- ADDED: close session action on invoice ---
    def action_ksef_close_session(self):
        """
        Close the interactive KSeF session linked to this invoice.
        """
        for inv in self:
            if inv.move_type not in ('out_invoice', 'out_refund'):
                continue
            # Ensure access token is present
            if not inv.company_id.ksef_access_token:
                raise UserError(_('Please configure a KSeF access token on the company.'))
            if not inv.ksef_session_id:
                raise UserError(_('No KSeF session reference on this invoice.'))
            self.env['ksef.service'].close_session(inv.company_id, inv.ksef_session_id)
            inv.ksef_session_closed = True
        return True

    # --- ADDED: download UPO action on invoice ---
    def action_ksef_download_upo(self):
        """
        Fetch UPO file for the current session, attach it to the invoice,
        and return a download action.
        """
        self.ensure_one()
        inv = self
        if inv.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_('Only customer invoices and credit notes can use KSeF actions.'))
        if not inv.company_id.ksef_access_token:
            raise UserError(_('Please configure a KSeF access token on the company.'))
        if not inv.ksef_session_id:
            raise UserError(_('No KSeF session reference on this invoice.'))

        content, mimetype, filename = self.env['ksef.service'].get_session_upo(inv.company_id, inv.ksef_session_id)

        vals = {
            'name': filename,
            'datas': base64.b64encode(content),
            'res_model': inv._name,
            'res_id': inv.id,
            'mimetype': mimetype,
        }
        if inv.ksef_upo_attachment_id:
            inv.ksef_upo_attachment_id.write(vals)
            attach = inv.ksef_upo_attachment_id
        else:
            attach = self.env['ir.attachment'].create(vals)
            inv.ksef_upo_attachment_id = attach.id

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attach.id}?download=true',
            'target': 'self',
        }
