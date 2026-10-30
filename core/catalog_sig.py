"""Authenticity verification for the check catalog and its collectors.

A bare hash proves nothing against an attacker who can replace both the
catalog and the stored hash (audit item #7). This module verifies an
Ed25519 signature instead:

- ``checks/catalog.sig.json`` — signature over a manifest naming the
  SHA-256 of ``catalog.json`` and of every collector script in
  ``checks/powershell``.
- ``checks/catalog.pub.pem`` — the owner's public key, shipped with the
  app. The private key is generated and held by the owner (see
  ``tools/sign_catalog.py``); it never ships and is never committed.

Behaviour is deliberately staged so the feature can be adopted safely:

- Neither file present: allowed only for unsigned development checkouts.
  Required-signature policy rejects removal of both signing files.
- Exactly one present: a hard error — a half-deployed signature setup
  must not silently degrade.
- Both present: verify the signature and every covered file. Signed releases
  also pin the public key in core/catalog_trust.py, outside checks/.
  Replacement of verifier code itself is outside this trust boundary.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

SIGNATURE_FILENAME = "catalog.sig.json"
PUBLIC_KEY_FILENAME = "catalog.pub.pem"
ALGORITHM = "Ed25519"


class CatalogIntegrityError(Exception):
    """Raised when catalog authenticity verification fails."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(catalog_bytes: bytes, scripts: dict[str, bytes]) -> dict[str, Any]:
    """Return the manifest that a signature commits to."""

    return {
        "algorithm": ALGORITHM,
        "catalog_sha256": _sha256(catalog_bytes),
        "scripts": {name: _sha256(data) for name, data in sorted(scripts.items())},
    }


def _canonical(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_manifest(manifest: dict[str, Any], private_key_pem: bytes) -> dict[str, Any]:
    """Sign a manifest with an Ed25519 private key (owner-side only)."""

    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key = load_pem_private_key(private_key_pem, password=None)
    signature = key.sign(_canonical(manifest))
    return {**manifest, "signature": base64.b64encode(signature).decode("ascii")}


def verify_signed_manifest(signed: dict[str, Any], public_key_pem: bytes) -> dict[str, Any]:
    """Verify a signed manifest and return the manifest it commits to."""

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    if signed.get("algorithm") != ALGORITHM or not isinstance(signed.get("signature"), str):
        raise CatalogIntegrityError("Signature file is missing its algorithm or signature.")
    manifest = {key: signed[key] for key in ("algorithm", "catalog_sha256", "scripts") if key in signed}
    if set(manifest) != {"algorithm", "catalog_sha256", "scripts"}:
        raise CatalogIntegrityError("Signature manifest is incomplete.")
    public_key = load_pem_public_key(public_key_pem)
    try:
        public_key.verify(base64.b64decode(signed["signature"]), _canonical(manifest))
    except InvalidSignature as exc:
        raise CatalogIntegrityError(
            "Catalog signature does not verify against the shipped public key."
        ) from exc
    return manifest


def verify_catalog_directory(checks_directory: Path, *, require_signed=False,
                             trusted_public_key_sha256=None) -> str:
    """Verify the catalog + collector scripts in a checks directory.

    Returns "verified" when a valid signature covers the exact bytes on
    disk, or "unsigned" when no signature material is present.
    """

    checks_directory = Path(checks_directory)
    require_signed = require_signed or trusted_public_key_sha256 is not None
    signature_path = checks_directory / SIGNATURE_FILENAME
    public_key_path = checks_directory / PUBLIC_KEY_FILENAME

    if not signature_path.exists() and not public_key_path.exists():
        if require_signed:
            raise CatalogIntegrityError("Signed catalog required; signature material is missing.")
        return "unsigned"
    if not signature_path.exists() or not public_key_path.exists():
        raise CatalogIntegrityError(
            "Catalog signing is half-configured: catalog.sig.json and "
            "catalog.pub.pem must be shipped together, or neither."
        )

    try:
        signed = json.loads(signature_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogIntegrityError(f"Catalog signature file is unreadable: {exc}") from exc

    public_key_bytes = public_key_path.read_bytes()
    if require_signed and trusted_public_key_sha256 is None:
        raise CatalogIntegrityError("Signed release requires a pinned public key outside the checks directory.")
    if trusted_public_key_sha256 is not None and _sha256(public_key_bytes) != trusted_public_key_sha256:
        raise CatalogIntegrityError("Catalog public key does not match the trusted fingerprint.")
    try:
        manifest = verify_signed_manifest(signed, public_key_bytes)
    except (ValueError, TypeError) as exc:
        raise CatalogIntegrityError(f"Malformed signature or public key: {exc}") from exc

    catalog_path = checks_directory / "catalog.json"
    try:
        catalog_bytes = catalog_path.read_bytes()
    except OSError as exc:
        raise CatalogIntegrityError(f"Catalog could not be read for verification: {exc}") from exc
    if _sha256(catalog_bytes) != manifest["catalog_sha256"]:
        raise CatalogIntegrityError("catalog.json does not match its signed hash.")

    scripts_directory = checks_directory / "powershell"
    actual_scripts = {}
    if scripts_directory.is_dir():
        for script in sorted(scripts_directory.glob("*.ps1")):
            actual_scripts[script.name] = script.read_bytes()
    expected = manifest["scripts"]
    if set(actual_scripts) != set(expected):
        raise CatalogIntegrityError(
            "Collector scripts on disk differ from the signed set "
            f"(signed: {sorted(expected)}, found: {sorted(actual_scripts)})."
        )
    for name, data in actual_scripts.items():
        if _sha256(data) != expected[name]:
            raise CatalogIntegrityError(f"Collector script {name} does not match its signed hash.")

    return "verified"
