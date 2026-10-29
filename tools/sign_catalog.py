"""Owner-side catalog signing tool (audit item #7).

Run this on the owner's machine, never in CI with a committed key:

  # 1. One time — generate the keypair. Keep the private key OUTSIDE the
  #    repository (for example in a password manager or an offline file).
  python tools/sign_catalog.py generate --private-key C:\\Keys\\secureaudit-catalog.key

  #    This writes checks/catalog.pub.pem (safe to commit) and prints a
  #    warning about the private key. Commit the public key.

  # 2. After every catalog or collector-script change — re-sign:
  python tools/sign_catalog.py sign --private-key C:\\Keys\\secureaudit-catalog.key

  #    This writes checks/catalog.sig.json. Commit it together with the
  #    catalog change it covers.

The application verifies the signature at catalog load when both
catalog.pub.pem and catalog.sig.json are present.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.catalog_sig import build_manifest, sign_manifest  # noqa: E402

CHECKS = ROOT / "checks"


def _scripts() -> dict[str, bytes]:
    scripts = {}
    for script in sorted((CHECKS / "powershell").glob("*.ps1")):
        scripts[script.name] = script.read_bytes()
    return scripts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "sign"))
    parser.add_argument("--private-key", required=True, type=Path,
                        help="Path of the Ed25519 private key PEM (kept outside the repo)")
    args = parser.parse_args()

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
    )

    if args.command == "generate":
        if args.private_key.exists():
            parser.error(f"{args.private_key} already exists; refusing to overwrite a private key")
        if ROOT in args.private_key.resolve().parents:
            parser.error("The private key must live OUTSIDE the repository. Choose another path.")
        key = Ed25519PrivateKey.generate()
        args.private_key.parent.mkdir(parents=True, exist_ok=True)
        args.private_key.write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        public_path = CHECKS / "catalog.pub.pem"
        public_path.write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
        print(f"Private key written to {args.private_key} — keep it offline and never commit it.")
        print(f"Public key written to {public_path} — commit this file, then run: sign")
        return 0

    private_pem = args.private_key.read_bytes()
    manifest = build_manifest((CHECKS / "catalog.json").read_bytes(), _scripts())
    signed = sign_manifest(manifest, private_pem)
    signature_path = CHECKS / "catalog.sig.json"
    signature_path.write_text(json.dumps(signed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {signature_path} covering catalog.json and {len(manifest['scripts'])} collector scripts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
