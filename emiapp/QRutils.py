# utils.py (create this file)
import hashlib
import requests

def generate_checksum_from_url(url):
    sha256 = hashlib.sha256()

    response = requests.get(url, stream=True)
    response.raise_for_status()

    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            sha256.update(chunk)

    return sha256.hexdigest()