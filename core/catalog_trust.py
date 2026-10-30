"""Owner-managed trust anchor embedded with verifier code, outside checks/.

tools/sign_catalog.py sign pins the owner's public key here. Development
checkouts may be unsigned. Frozen releases require this anchor and signatures.
An attacker able to replace verifier code itself is outside this boundary.
"""
PUBLIC_KEY_SHA256 = None
