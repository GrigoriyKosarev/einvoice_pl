from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Legacy API Key ID and Key fields are kept for backward compatibility but no longer used.
    ksef_api_key_id = fields.Char(
        string='KSeF API Key ID (deprecated)',
        help='(Deprecated) Identifier for KSeF 1.x basic authentication. Not used in KSeF 2.0.'
    )
    ksef_api_key = fields.Char(
        string='KSeF API Key (deprecated)',
        help='(Deprecated) Secret key for KSeF 1.x basic authentication. Not used in KSeF 2.0.'
    )
    # KSeF 2.0 environment selection
    ksef_environment = fields.Selection(
        [
            ('te', 'Test (TE)'),
            ('tr', 'Demo (TR)'),
            ('prd', 'Production (PRD)'),
        ],
        string='KSeF Environment',
        default='te',
        help='Select the KSeF API environment to use: TE (test), TR (demo) or PRD (production).'
    )
    # Context identifier used to open sessions (NIP or delegated token)
    ksef_context_identifier = fields.Char(
        string='KSeF Context Identifier',
        help='Identifier of the context used to open sessions in KSeF (e.g. company NIP or delegated token).'
    )
    # JWT access token for KSeF 2.0
    ksef_access_token = fields.Char(
        string='KSeF Access Token',
        help='JWT access token used for Bearer authentication with KSeF 2.0.'
    )
    # Refresh token for renewing the access token
    ksef_refresh_token = fields.Char(
        string='KSeF Refresh Token',
        help='Refresh token used to obtain a new access token.'
    )
    # Optional system token for token-based authentication
    ksef_token = fields.Char(
        string='KSeF System Token',
        help='System token used in the token-based authentication flow.'
    )
