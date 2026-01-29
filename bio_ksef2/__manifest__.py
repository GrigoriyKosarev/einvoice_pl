# -*- coding: utf-8 -*-
{
    'name': 'KSeF Integration',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Polish KSeF (Krajowy System e-Faktur) Integration for Odoo',
    'description': """
Polish KSeF Integration
========================
Integration with Polish National e-Invoice System (KSeF).

Features:
---------
* Send invoices to KSeF
* Automatic KSeF number assignment
* Invoice status tracking
* Token-based authentication
* Support for FA_VAT format
* Session management

Requirements:
-------------
* Python 3.10+
* cryptography library
* requests library
    """,
    'author': 'Biosphera',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'external_dependencies': {
        'python': ['cryptography', 'requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/ksef_config_views.xml',
        'views/account_move_views.xml',
        'wizard/ksef_send_invoice_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
