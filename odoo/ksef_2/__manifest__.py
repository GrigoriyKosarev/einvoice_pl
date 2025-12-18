{
    'name': 'KSeF 2 Integration',
    'version': '18.2.0',
    'summary': 'Integracja z Krajowym Systemem e-Faktur (KSeF)',
    'description': 'Wysyłanie i odbiór faktur ustrukturyzowanych (e-Faktur) poprzez Krajowy System e-Faktur (KSeF).',
    'author': 'Marius Johannes Kuc',
    'website': 'https://www.odoo.com.pl/ksef',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
