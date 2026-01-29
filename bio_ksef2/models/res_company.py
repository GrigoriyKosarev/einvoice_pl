# -*- coding: utf-8 -*-
"""Company Extension for KSeF"""
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    has_ksef_config = fields.Boolean(
        string='Has KSeF Configuration',
        default=False,
        help='Indicates if the company has active KSeF configuration. '
             'This field is automatically maintained by ksef.config model.',
    )
