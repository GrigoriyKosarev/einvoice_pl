# -*- coding: utf-8 -*-
"""Module initialization hooks"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Initialize has_ksef_config flags after module installation/upgrade"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        _logger.info('Running post_init_hook for bio_ksef2...')

        # Initialize company flags
        env['ksef.config']._init_company_ksef_flags()
        _logger.info('Successfully initialized has_ksef_config flags')

        # Migrate existing FA2 configs to FA3 (FA3 is mandatory from 01.02.2026)
        fa2_configs = env['ksef.config'].search([('fa_version', '=', 'FA2')])
        if fa2_configs:
            fa2_configs.write({'fa_version': 'FA3'})
            _logger.info(f'Migrated {len(fa2_configs)} KSeF configs from FA2 to FA3')

    except Exception as e:
        _logger.error(f'Failed to run post_init_hook: {e}')
        # Don't raise - allow module installation to continue
