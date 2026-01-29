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

        # Migrate FA3 configs back to FA2 (FA3 doesn't actually exist as separate schema)
        # Both FA2 and FA3 generate identical XML: kodSystemowy="FA (2)", WariantFormularza=2
        fa3_configs = env['ksef.config'].search([('fa_version', '=', 'FA3')])
        if fa3_configs:
            fa3_configs.write({'fa_version': 'FA2'})
            _logger.info(f'Migrated {len(fa3_configs)} KSeF configs from FA3 to FA2 (FA3 is deprecated)')

    except Exception as e:
        _logger.error(f'Failed to run post_init_hook: {e}')
        # Don't raise - allow module installation to continue
