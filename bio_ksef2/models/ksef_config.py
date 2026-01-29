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

    @api.model_create_multi
    def create(self, vals_list):
        """Set has_ksef_config flag on company when config is created"""
        records = super().create(vals_list)
        # Skip updating company flag during module install/upgrade
        if not self.env.context.get('module_install', False):
            for record in records:
                if record.company_id:
                    try:
                        record.company_id.has_ksef_config = True
                    except Exception:
                        # Ignore errors during module initialization
                        pass
        return records

    def write(self, vals):
        """Update has_ksef_config flag when active status changes"""
        result = super().write(vals)
        # Skip updating company flag during module install/upgrade
        if not self.env.context.get('module_install', False):
            if 'active' in vals or 'company_id' in vals:
                for record in self:
                    if record.company_id:
                        try:
                            # Check if any active config exists for this company
                            has_config = self.search_count([
                                ('company_id', '=', record.company_id.id),
                                ('active', '=', True),
                            ]) > 0
                            record.company_id.has_ksef_config = has_config
                        except Exception:
                            # Ignore errors during module initialization
                            pass
        return result

    def unlink(self):
        """Clear has_ksef_config flag on company when config is deleted"""
        companies = self.mapped('company_id')
        result = super().unlink()
        # Skip updating company flag during module install/upgrade
        if not self.env.context.get('module_install', False):
            for company in companies:
                try:
                    # Check if any active config still exists for this company
                    has_config = self.search_count([
                        ('company_id', '=', company.id),
                        ('active', '=', True),
                    ]) > 0
                    company.has_ksef_config = has_config
                except Exception:
                    # Ignore errors during module initialization
                    pass
        return result

    @api.model
    def _init_company_ksef_flags(self):
        """Initialize has_ksef_config flags for all companies.
        Called after module installation/upgrade."""
        _logger.info('Initializing has_ksef_config flags for companies...')

        # Get all companies
        all_companies = self.env['res.company'].search([])

        # Reset all flags first
        all_companies.write({'has_ksef_config': False})

        # Set flag for companies that have active KSeF config
        configs = self.search([('active', '=', True)])
        companies_with_config = configs.mapped('company_id')

        if companies_with_config:
            companies_with_config.write({'has_ksef_config': True})
            _logger.info(f'Set has_ksef_config=True for {len(companies_with_config)} companies')

        return True

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
