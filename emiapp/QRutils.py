import hashlib
import requests
import base64

def generate_checksum_from_url(url):
    sha256 = hashlib.sha256()

    response = requests.get(
        url,
        stream=True,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    response.raise_for_status()

    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            sha256.update(chunk)

    # ✅ REQUIRED for Android provisioning
    return base64.b64encode(sha256.digest()).decode()