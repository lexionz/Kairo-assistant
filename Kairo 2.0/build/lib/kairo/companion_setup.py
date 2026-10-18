"""Local certificate preparation; never changes trust stores, firewall or router rules."""
import base64
import ipaddress
import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from kairo.companion import lan_address

def local_addresses():
    found = set()
    for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
        try:
            found.add(lan_address(info[4][0]))
        except ValueError:
            pass
    return sorted(found)

def prepare(directory, address):
    if address not in local_addresses():
        raise ValueError('Choose an available local LAN address')
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    root = Path(directory) / 'companion-tls'
    root.mkdir(parents=True, exist_ok=True)
    metadata = root / 'setup.json'
    if metadata.exists():
        data = json.loads(metadata.read_text())
        if data['address'] == address and datetime.fromisoformat(data['expires']) > datetime.now(timezone.utc) + timedelta(days=1):
            return {**data, 'certificate': base64.b64encode((root/'KAIRO-Phone-Trust.cer').read_bytes()).decode()}
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=30)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'KAIRO local companion trust')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(expiry).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True).add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=None,decipher_only=None), critical=True).sign(ca_key, hashes.SHA256()))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'KAIRO companion')])).issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(expiry).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(address))]),critical=False).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(ca_key,hashes.SHA256()))
    (root/'KAIRO-Phone-Trust.cer').write_bytes(ca.public_bytes(serialization.Encoding.DER))
    (root/'server.pem').write_bytes(leaf.public_bytes(serialization.Encoding.PEM)+ca.public_bytes(serialization.Encoding.PEM))
    (root/'server-key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    data = {'address':address,'port':8766,'certfile':str(root/'server.pem'),'keyfile':str(root/'server-key.pem'),'trust_file':str(root/'KAIRO-Phone-Trust.cer'),'fingerprint':ca.fingerprint(hashes.SHA256()).hex(),'expires':expiry.isoformat()}
    metadata.write_text(json.dumps(data,indent=2))
    return {**data,'certificate':base64.b64encode((root/'KAIRO-Phone-Trust.cer').read_bytes()).decode()}
