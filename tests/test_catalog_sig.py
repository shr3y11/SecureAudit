"""Tests for catalog signing / authenticity verification (item #7)."""
import json

import pytest

from core.catalog_sig import (
    CatalogIntegrityError,
    build_manifest,
    sign_manifest,
    verify_catalog_directory,
)
from core.scanner import CatalogError, load_catalog

CATALOG = {"catalog_version": "test", "checks": []}


@pytest.fixture
def keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
    )

    key = Ed25519PrivateKey.generate()
    private_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_pem = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return private_pem, public_pem


@pytest.fixture
def checks_dir(tmp_path):
    directory = tmp_path / "checks"
    (directory / "powershell").mkdir(parents=True)
    (directory / "catalog.json").write_text(json.dumps(CATALOG), encoding="utf-8")
    (directory / "powershell" / "firewall.ps1").write_text("# fixture collector\n", encoding="utf-8")
    return directory


def _sign(directory, private_pem, public_pem):
    scripts = {p.name: p.read_bytes() for p in (directory / "powershell").glob("*.ps1")}
    signed = sign_manifest(build_manifest((directory / "catalog.json").read_bytes(), scripts), private_pem)
    (directory / "catalog.sig.json").write_text(json.dumps(signed), encoding="utf-8")
    (directory / "catalog.pub.pem").write_bytes(public_pem)


def test_unsigned_directory_loads_as_before(checks_dir):
    assert verify_catalog_directory(checks_dir) == "unsigned"
    assert load_catalog(checks_dir / "catalog.json")["catalog_version"] == "test"


def test_signed_directory_verifies(checks_dir, keypair):
    _sign(checks_dir, *keypair)
    assert verify_catalog_directory(checks_dir) == "verified"
    assert load_catalog(checks_dir / "catalog.json")["catalog_version"] == "test"


def test_tampered_catalog_is_rejected(checks_dir, keypair):
    _sign(checks_dir, *keypair)
    (checks_dir / "catalog.json").write_text(json.dumps({"catalog_version": "evil", "checks": []}), encoding="utf-8")
    with pytest.raises(CatalogIntegrityError):
        verify_catalog_directory(checks_dir)
    with pytest.raises(CatalogError, match="integrity"):
        load_catalog(checks_dir / "catalog.json")


def test_tampered_collector_script_is_rejected(checks_dir, keypair):
    """The collectors are inside the signed scope, not just the catalog."""
    _sign(checks_dir, *keypair)
    (checks_dir / "powershell" / "firewall.ps1").write_text("evil payload\n", encoding="utf-8")
    with pytest.raises(CatalogIntegrityError, match="firewall.ps1"):
        verify_catalog_directory(checks_dir)


def test_half_configured_signing_is_a_hard_error(checks_dir, keypair):
    _sign(checks_dir, *keypair)
    (checks_dir / "catalog.sig.json").unlink()
    with pytest.raises(CatalogIntegrityError, match="half-configured"):
        verify_catalog_directory(checks_dir)


def test_wrong_public_key_is_rejected(checks_dir, keypair):
    _sign(checks_dir, *keypair)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    other = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    (checks_dir / "catalog.pub.pem").write_bytes(other)
    with pytest.raises(CatalogIntegrityError, match="does not verify"):
        verify_catalog_directory(checks_dir)
