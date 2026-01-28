# -*- coding: utf-8 -*-
"""KSeF Configuration Model"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class KSefConfig(models.Model):
    _name = 'ksef.config'
    _description = 'KSeF Configuration'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    api_url = fields.Selection(
        [
            ('https://api-test.ksef.mf.gov.pl', 'Test Environment 2026'),
            ('https://ksef-test.mf.gov.pl', 'Test Environment'),
            ('https://ksef.mf.gov.pl', 'Production Environment'),
        ],
        string='API Environment',
        required=True,
        default='https://ksef-test.mf.gov.pl',
    )
    ksef_token = fields.Char(
        string='KSeF Token',
        required=True,
        help='KSeF authentication token in format: 20251209-EC-...|nip-XXXXXXXXX|...',
    )
    auto_send = fields.Boolean(
        string='Auto-send Invoices',
        default=False,
        help='Automatically send invoices to KSeF upon validation',
    )
    fa_version = fields.Selection(
        [
            ('FA2', 'FA(2) - valid until 31.01.2026'),
            ('FA3', 'FA(3) - mandatory from 01.02.2026'),
        ],
        string='Invoice Format Version',
        required=True,
        default='FA2',
        help='Select FA_VAT invoice format version to use for KSeF submissions',
    )

    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'Only one KSeF configuration per company is allowed!'),
    ]

    @api.model
    def get_config(self, company_id=None):
        """Get KSeF configuration for company"""
        if not company_id:
            company_id = self.env.company.id

        config = self.search([
            ('company_id', '=', company_id),
            ('active', '=', True),
        ], limit=1)

        if not config:
            raise UserError(_('KSeF configuration not found for this company. Please configure KSeF in Settings.'))

        return config

    def action_test_connection(self):
        """Test KSeF API connection"""
        self.ensure_one()

        try:
            from ..ksef_client import auth

            _logger.info('Testing KSeF connection...')
            auth_client = auth.Auth(self.api_url, self.ksef_token)

            if auth_client.token:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Successfully connected to KSeF API!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Failed to authenticate with KSeF API. Please check your token.'))

        except Exception as e:
            _logger.error(f'KSeF connection test failed: {e}')
            raise UserError(_('Connection failed: %s') % str(e))
