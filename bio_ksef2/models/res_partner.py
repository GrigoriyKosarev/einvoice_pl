# -*- coding: utf-8 -*-
"""Partner Extension for KSeF"""
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ksef_code = fields.Char(
        string='Code',
        help='Customer code for logistics activities (Aktywność Logistyczna) - used in KSeF invoices',
    )
