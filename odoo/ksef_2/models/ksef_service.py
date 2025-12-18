# models/ksef_service.py
import base64
import json
import requests
from odoo import models, api
from odoo.exceptions import UserError

class KsefService(models.AbstractModel):
    _name = 'ksef.service'
    _description = 'KSeF REST API Service'

    def _get_base_url(self, company):
        """Return base API URL for the given company based on environment.

        KSeF 2.0 introduces three separate environments with their own domains:
        - TE: public test environment available under https://ksef-test.mf.gov.pl/api/v2
        - TR: demo/preproduction environment available under https://ksef-demo.mf.gov.pl/api/v2
        - PRD: production environment available under https://ksef.mf.gov.pl/api/v2

        The company's ``ksef_environment`` field selects which of these base
        URLs to use. See the official documentation for details.
        """
        env = (company.ksef_environment or '').lower()
        if env == 'te':
            return 'https://ksef-test.mf.gov.pl/api/v2'
        if env == 'tr':
            return 'https://ksef-demo.mf.gov.pl/api/v2'
        # Default to production (PRD) if environment is unknown
        return 'https://ksef.mf.gov.pl/api/v2'

    def _get_auth_header(self, company):
        """Create Bearer Authorization header from the company's access token.

        All protected KSeF 2.0 endpoints require an access token obtained via
        the authentication flow.  The token must be sent as a Bearer token
        in the Authorization header.  If no token is configured on the company,
        a ``UserError`` is raised.
        """
        if not company.ksef_access_token:
            raise UserError('Missing KSeF access token on the company.')
        return {
            'Authorization': f'Bearer {company.ksef_access_token}',
            'Content-Type': 'application/json',
        }

    def open_session(self, company, encryption_key=None, init_vector=None, invoice_version='v2'):
        """Open an interactive session ("online" session) with KSeF 2.0.

        A session must be opened before invoices can be sent.  This method
        performs a POST on ``/sessions/online`` passing the context identifier
        and optional encryption parameters.  The response contains a
        ``referenceNumber`` which uniquely identifies the session.  This value
        is returned to the caller.
        """
        base_url = self._get_base_url(company)
        url = f'{base_url}/sessions/online'
        # The payload must include the context identifier of the taxpayer or
        # delegated token.  Encryption parameters can be provided if using
        # encrypted mode.
        payload = {
            "contextIdentifier": company.ksef_context_identifier or "",
        }
        if encryption_key and init_vector:
            payload.update({
                "encryptionKey": encryption_key,
                "initVector": init_vector,
            })
        headers = self._get_auth_header(company)
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        except Exception as e:
            raise UserError(f'Error while opening KSeF session: {e}')
        if response.status_code not in (200, 201):
            raise UserError(f'Failed to open KSeF session: {response.status_code} {response.text}')
        res_json = {}
        try:
            res_json = response.json()
        except Exception:
            pass
        # According to the KSeF 2.0 specification, the session reference number
        # is returned in the ``referenceNumber`` field.
        return res_json.get('referenceNumber')

    def send_invoice(self, company, session_id, xml_content):
        """Send a structured invoice XML to KSeF within an open online session.

        In KSeF 2.0, invoices are sent via the endpoint
        ``/sessions/online/{referenceNumber}/invoices``.  The payload is an
        array of invoice objects.  Each object can include the invoice data
        (base64 encoded), invoice version, and an optional hash.  This method
        sends a single invoice, returning the reference number assigned by KSeF.
        """
        if not session_id:
            raise UserError('Missing KSeF session reference number.')
        base_url = self._get_base_url(company)
        url = f'{base_url}/sessions/online/{session_id}/invoices'
        # Ensure xml_content is bytes before encoding
        if isinstance(xml_content, (bytes, bytearray)):
            invoice_b64 = base64.b64encode(xml_content).decode('utf-8')
        else:
            invoice_b64 = base64.b64encode(xml_content.encode('utf-8')).decode('utf-8')
        payload = {
            "invoices": [
                {
                    "invoiceData": invoice_b64,
                    "invoiceVersion": "FA3"  # default to FA(3) for KSeF 2.0
                }
            ]
        }
        headers = self._get_auth_header(company)
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        except Exception as e:
            raise UserError(f'Error while sending invoice to KSeF: {e}')
        if response.status_code not in (200, 201):
            raise UserError(f'Failed to send invoice to KSeF: {response.status_code} {response.text}')
        res_json = {}
        try:
            res_json = response.json()
        except Exception:
            pass
        # The response body should contain a list under ``invoices`` with a referenceNumber
        # for each invoice.  Extract the first one.
        try:
            invoice_list = res_json.get('invoices', [])
            if invoice_list:
                first = invoice_list[0]
                return first.get('referenceNumber') or first.get('referenceNumber')
        except Exception:
            pass
        # If the expected structure is not present, return the raw response
        return res_json

    def invoice_status(self, company, session_id, invoice_id):
        """Check processing status of a sent invoice in KSeF 2.0.

        Invoice status is retrieved via ``/sessions/{referenceNumber}/invoices/{invoiceReference}``.
        The response contains information about processing state and, when accepted,
        the final KSeF number.  This method returns the parsed JSON body.
        """
        if not session_id or not invoice_id:
            raise UserError('Missing KSeF session or invoice reference number.')
        base_url = self._get_base_url(company)
        url = f'{base_url}/sessions/{session_id}/invoices/{invoice_id}'
        headers = self._get_auth_header(company)
        try:
            response = requests.get(url, headers=headers, timeout=60)
        except Exception as e:
            raise UserError(f'Error while fetching invoice status from KSeF: {e}')
        if response.status_code not in (200, 202):
            raise UserError(f'Failed to fetch invoice status from KSeF: {response.status_code} {response.text}')
        try:
            return response.json()
        except Exception:
            return {}

    def query_invoices(self, company, session_id, subject_type='subject2', date_from=None, date_to=None):
        """Query invoices received or issued within a date range.

        Uses the `ksefInvoiceQueryStart` operation to define search criteria
        such as the type of invoices (sales, cost, third party, authorized)
        and date range, then returns a `queryId` which can be used to
        download results in parts.
        """
        base_url = self._get_base_url(company)
        url = f'{base_url}/ksefInvoiceQueryStart'
        range_obj = None
        if date_from and date_to:
            range_obj = {
                "from": date_from.strftime('%Y-%m-%d'),
                "this": date_to.strftime('%Y-%m-%d'),
            }
        payload = {
            "sessionId": session_id,
            "subjectType": subject_type,
        }
        if range_obj:
            payload["range"] = range_obj
        headers = self._get_auth_header(company)
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code != 200:
            raise UserError(f'Failed to start invoice query: {response.status_code} {response.text}')
        res_json = response.json()
        return res_json.get('queryId')

    # --- ADDED: close interactive session in KSeF ---
    def close_session(self, company, session_id):
        """
        Close an online session in KSeF 2.0.

        The session is closed by POSTing to ``/sessions/online/{referenceNumber}/close``.
        After closure, KSeF will generate UPO files which can be downloaded
        separately.  This method returns True when the closure request is
        accepted.
        """
        if not session_id:
            raise UserError('Missing KSeF session reference number.')
        base_url = self._get_base_url(company)
        url = f'{base_url}/sessions/online/{session_id}/close'
        headers = self._get_auth_header(company)
        try:
            resp = requests.post(url, headers=headers, data=json.dumps({}), timeout=60)
        except Exception as e:
            raise UserError(f'Failed to close KSeF session: {e}')
        if resp.status_code not in (200, 202):
            raise UserError(f'Failed to close KSeF session: {resp.status_code} {resp.text}')
        return True

    # --- ADDED: fetch session UPO file (PDF/XML) ---
    def get_session_upo(self, company, session_id):
        """
        Fetch UPO file(s) for the given session.

        In KSeF 2.0 a closed session may produce one or more UPO documents.
        This method retrieves the first available UPO for the session.  It
        first queries the session details to obtain the list of available
        UPO reference numbers and then downloads the file using the
        ``/sessions/{sessionRef}/upo/{upoRef}`` endpoint.  The content,
        MIME type and a suggested filename are returned.
        """
        if not session_id:
            raise UserError('Missing KSeF session reference number.')
        base_url = self._get_base_url(company)
        headers = self._get_auth_header(company)
        # Query session status to get UPO references
        status_url = f'{base_url}/sessions/{session_id}'
        try:
            status_resp = requests.get(status_url, headers=headers, timeout=60)
        except Exception as e:
            raise UserError(f'Failed to fetch session status: {e}')
        if status_resp.status_code not in (200, 202):
            raise UserError(f'Failed to fetch session status: {status_resp.status_code} {status_resp.text}')
        upo_ref = None
        try:
            status_data = status_resp.json()
            # The list of UPOs may be under ``upo" or ``upoList".  Extract the first reference number.
            upos = status_data.get('upo') or status_data.get('upoList') or []
            if isinstance(upos, list) and upos:
                first = upos[0]
                # Each entry may be a dict with ``referenceNumber`` and ``downloadUrl``
                if isinstance(first, dict):
                    upo_ref = first.get('referenceNumber') or first.get('referenceNumber')
        except Exception:
            pass
        if not upo_ref:
            raise UserError('No UPO available for this session yet.')
        # Construct URL for UPO download
        upo_url = f'{base_url}/sessions/{session_id}/upo/{upo_ref}'
        try:
            upo_resp = requests.get(upo_url, headers=headers, timeout=60)
        except Exception as e:
            raise UserError(f'Failed to fetch KSeF UPO: {e}')
        if upo_resp.status_code not in (200, 202):
            raise UserError(f'Failed to fetch KSeF UPO: {upo_resp.status_code} {upo_resp.text}')
        mimetype = upo_resp.headers.get('Content-Type', 'application/octet-stream').split(';')[0].strip()
        if mimetype == 'application/pdf':
            filename = f'UPO_{session_id}.pdf'
        elif mimetype in ('application/xml', 'text/xml'):
            filename = f'UPO_{session_id}.xml'
        else:
            filename = f'UPO_{session_id}'
        return upo_resp.content, mimetype, filename

    # ------------------------
    # Authentication helpers
    # ------------------------
    def get_auth_challenge(self, company):
        """Request an authentication challenge for the given context.

        This helper calls ``/auth/challenge`` with the context identifier.  The
        response typically contains a challenge identifier and a challenge
        content that must be signed with a qualified signature or encrypted
        using a KSeF token.
        """
        base_url = self._get_base_url(company)
        url = f'{base_url}/auth/challenge'
        payload = {"contextIdentifier": company.ksef_context_identifier or ""}
        try:
            resp = requests.post(url, json=payload, timeout=60)
        except Exception as e:
            raise UserError(f'Failed to request KSeF challenge: {e}')
        if resp.status_code not in (200, 201):
            raise UserError(f'Failed to request KSeF challenge: {resp.status_code} {resp.text}')
        try:
            return resp.json()
        except Exception:
            return {}

    def redeem_auth_token(self, company, challenge_id, signed_challenge):
        """Redeem an authentication challenge to obtain access and refresh tokens.

        After signing or encrypting the challenge content, send it back to
        ``/auth/token/redeem`` along with the challenge identifier.  On
        success the response returns ``accessToken`` and ``refreshToken``.
        """
        base_url = self._get_base_url(company)
        url = f'{base_url}/auth/token/redeem'
        payload = {"challengeId": challenge_id, "signedChallenge": signed_challenge}
        try:
            resp = requests.post(url, json=payload, timeout=60)
        except Exception as e:
            raise UserError(f'Failed to redeem KSeF token: {e}')
        if resp.status_code not in (200, 201):
            raise UserError(f'Failed to redeem KSeF token: {resp.status_code} {resp.text}')
        try:
            return resp.json()
        except Exception:
            return {}

    def refresh_access_token(self, company):
        """Refresh the access token using the company's refresh token.

        Calls ``/auth/token/refresh`` with the refresh token.  On success
        returns the new access token and (optionally) a new refresh token.
        """
        if not company.ksef_refresh_token:
            raise UserError('No refresh token configured for the company.')
        base_url = self._get_base_url(company)
        url = f'{base_url}/auth/token/refresh'
        payload = {"refreshToken": company.ksef_refresh_token}
        try:
            resp = requests.post(url, json=payload, timeout=60)
        except Exception as e:
            raise UserError(f'Failed to refresh KSeF token: {e}')
        if resp.status_code not in (200, 201):
            raise UserError(f'Failed to refresh KSeF token: {resp.status_code} {resp.text}')
        try:
            return resp.json()
        except Exception:
            return {}
