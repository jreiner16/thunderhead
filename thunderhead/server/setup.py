import os
from thunderhead.config import hash_password, save_config, DATA_DIR, CERT_PATH, KEY_PATH


def _generate_cert():
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
    import datetime
    import ipaddress

    os.makedirs(DATA_DIR, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(KEY_PATH, "wb") as f:
        f.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Thunderhead")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    with open(CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(Encoding.PEM))


def run_setup() -> dict:
    print("Thunderhead setup")
    print("----------------")

    password = input("Admin password: ").strip()
    while not password:
        password = input("Admin password (required): ").strip()

    root = input(f"Storage root [{os.path.join(os.path.expanduser('~'), 'ThunderData')}]: ").strip()
    if not root:
        root = os.path.join(os.path.expanduser("~"), "ThunderData")
    root = os.path.abspath(os.path.expandvars(root))

    port_str = input("Port [8443]: ").strip()
    try:
        port = int(port_str) if port_str else 8443
    except ValueError:
        port = 8443

    os.makedirs(root, exist_ok=True)

    config = {
        "configured": True,
        "password_hash": hash_password(password),
        "storage_root": root,
        "port": port,
    }

    save_config(config)
    _generate_cert()

    print("Setup complete")
    return config
