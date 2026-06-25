import os
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Button, Label, Static, Header, Footer, Checkbox
from textual.containers import Vertical, Horizontal, Container
from textual.validation import Function
from textual import events

from thunderhead.config import hash_password, save_config, DATA_DIR, CERT_PATH, KEY_PATH


class SetupScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Container(
            Static("⚡ Thunderhead Setup", classes="title"),
            Static("Turn this PC into your personal VPS", classes="subtitle"),
            Static("", classes="spacer"),
            Label("Admin Password", classes="field-label"),
            Input(
                placeholder="Enter admin password",
                password=True,
                id="password",
                classes="field",
            ),
            Label("VPS Storage Root", classes="field-label"),
            Input(
                placeholder="D:\\ThunderData",
                id="storage_root",
                classes="field",
            ),
            Label("Server Port", classes="field-label"),
            Input(
                value="8443",
                id="port",
                classes="field",
                validators=[Function(self._validate_port)],
            ),
            Label("", classes="spacer"),
            Button("⚡  Launch Thunderhead", id="launch", variant="primary"),
            Static("", id="status", classes="status"),
            classes="form",
        )
        yield Footer()

    def _validate_port(self, value: str) -> bool:
        try:
            p = int(value)
            return 1024 <= p <= 65535
        except ValueError:
            return False

    def on_button_pressed(self, event: Button.Pressed):
        password = self.query_one("#password", Input).value
        root = self.query_one("#storage_root", Input).value or "D:\\ThunderData"
        port_str = self.query_one("#port", Input).value

        if not password:
            self.query_one("#status", Static).update("Password is required")
            return

        try:
            port = int(port_str)
        except ValueError:
            self.query_one("#status", Static).update("Invalid port number")
            return

        root = os.path.abspath(os.path.expandvars(root))

        os.makedirs(root, exist_ok=True)

        config = {
            "configured": True,
            "password_hash": hash_password(password),
            "storage_root": root,
            "port": port,
        }

        save_config(config)
        self._generate_cert()

        self.query_one("#status", Static).update("✓ Thunderhead is ready to launch!")
        self.app.exit(result=config)

    def _generate_cert(self):
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PrivateFormat,
            NoEncryption,
        )
        import datetime

        os.makedirs(DATA_DIR, exist_ok=True)

        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        with open(KEY_PATH, "wb") as f:
            f.write(
                key.private_bytes(
                    Encoding.PEM,
                    PrivateFormat.TraditionalOpenSSL,
                    NoEncryption(),
                )
            )

        subject = issuer = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "Thunderhead")]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName("localhost"), x509.IPAddress(x509.IPAddress("127.0.0.1"))]
                ),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        with open(CERT_PATH, "wb") as f:
            f.write(cert.public_bytes(Encoding.PEM))


class SetupApp(App):
    SCREENS = {"setup": SetupScreen}

    def on_mount(self):
        self.push_screen("setup")


def run_setup() -> dict:
    app = SetupApp()
    result = app.run()
    if hasattr(result, "get"):
        return result  # type: ignore
    raise RuntimeError("Setup was cancelled")
