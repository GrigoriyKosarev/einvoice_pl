# KSeF Integration for Odoo 16

Integration module for Polish KSeF (Krajowy System e-Faktur) - National e-Invoice System.

## Features

- ✅ Send customer invoices to KSeF
- ✅ Automatic KSeF number assignment
- ✅ Invoice status tracking (Pending, Accepted, Rejected)
- ✅ Token-based authentication
- ✅ Support for FA_VAT XML format
- ✅ Test and Production environments
- ✅ Auto-send option for invoices
- ✅ Status monitoring and updates

## Requirements

- Odoo 16.0
- Python 3.10+
- Python libraries:
  - `cryptography`
  - `requests`
  - `python-dateutil`

## Installation

1. Copy the `bio_ksef2` module to your Odoo addons directory
2. Install required Python dependencies:
   ```bash
   pip install cryptography requests python-dateutil
   ```
3. Update the app list in Odoo
4. Install the "KSeF Integration" module

## Configuration

1. Go to **Accounting → Configuration → KSeF → Configuration**
2. Click "Create"
3. Fill in the configuration:
   - **Company**: Select your company
   - **API Environment**: Choose Test or Production
   - **KSeF Token**: Enter your KSeF authentication token
   - **Auto-send Invoices**: Enable if you want automatic sending
4. Click **Test Connection** to verify the configuration
5. Save

### Getting a KSeF Token

To get a KSeF token:
1. Log in to the KSeF portal (test or production)
2. Go to token management
3. Generate a new token
4. Copy the full token string (format: `20251209-EC-...|nip-XXXXXXXXX|...`)

## Usage

### Sending Invoices Manually

1. Create and validate a customer invoice
2. Click the **Send to KSeF** button in the invoice header
3. Review the generated XML preview
4. Click **Send to KSeF** in the wizard
5. Check the **KSeF** tab in the invoice for:
   - KSeF Number (if accepted)
   - Status
   - Reference Number
   - Status Description

### Auto-send

When enabled in configuration, invoices are automatically sent to KSeF upon validation.

### Checking Status

- Click the **Check KSeF Status** button to update the invoice status
- The system periodically checks pending invoices automatically

### Filtering Invoices

Use the search filters to find invoices by KSeF status:
- KSeF Accepted
- KSeF Pending
- KSeF Rejected
- Not Sent to KSeF

## Technical Details

### Module Structure

```
bio_ksef2/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── ksef_config.py      # KSeF configuration
│   └── account_move.py      # Invoice extension
├── wizard/
│   ├── __init__.py
│   └── ksef_send_invoice.py # Send invoice wizard
├── views/
│   ├── ksef_config_views.xml
│   ├── account_move_views.xml
│   └── ksef_send_invoice_views.xml
├── security/
│   └── ir.model.access.csv
├── ksef_client/             # KSeF API client library
│   ├── __init__.py
│   ├── auth.py             # Authentication
│   ├── certificate.py       # Certificate management
│   └── invoice.py           # Invoice operations
└── static/
    └── description/
        └── index.html
```

### KSeF API Client

The module includes a simplified KSeF API client that handles:
- Token-based authentication with challenge-response
- RSA-OAEP encryption for tokens
- AES-256-CBC encryption for invoices
- Online session management
- Invoice submission and status checking

### Invoice XML Generation

The module generates FA_VAT format XML invoices with:
- Proper structure and namespaces
- Company and customer information
- Line items with VAT
- Required annotations
- DateTime formatting

## Troubleshooting

### Invoice Rejected (Status 450)

If an invoice is rejected with status code 450, check:
- Customer and company have valid NIP (VAT number)
- Invoice data is complete
- VAT rates are correct

### Authentication Failed

If authentication fails:
- Verify the KSeF token is correct and not expired
- Check the API environment (Test vs Production)
- Ensure firewall allows connections to KSeF API

### Connection Timeout

If connection times out:
- Check internet connectivity
- Verify proxy settings if applicable
- Increase timeout in code if needed

## Support

For issues or questions:
- Check the Odoo logs for detailed error messages
- Verify KSeF API status on the official portal
- Contact your system administrator

## License

LGPL-3

## Credits

Based on the ksef2 library for Python.
