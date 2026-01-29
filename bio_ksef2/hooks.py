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
    except Exception as e:
        _logger.error(f'Failed to initialize has_ksef_config flags: {e}')
        # Don't raise - allow module installation to continue
