import json
import requests


API_URL = "https://ksef-test.mf.gov.pl"

def public_key_certificates():

    resp = requests.get(
        f"{API_URL}/api/v2/security/public-key-certificates",
        timeout=60
    )
    if resp.status_code != 200:
        # print(f'unhandled response: {resp}')
        return

    for certificate in resp.json():
        usage = certificate.get("usage")[0]
        if usage and usage == 'KsefTokenEncryption':
            certKsefTokenEncryption = certificate.get("certificate")
        elif usage and usage == 'SymmetricKeyEncryption':
            certSymmetricKeyEncryption = certificate.get("certificate")

    pass
    # with open(f'certificates-{cfg.version}.json', 'wt') as fp:
    #     fp.write(json.dumps(resp.json()))
    #
    # with open('ksef.ini', 'wt') as fp:
    #     cfg.write(fp)

public_key_certificates()