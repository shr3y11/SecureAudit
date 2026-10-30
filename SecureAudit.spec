# -*- mode: python ; coding: utf-8 -*-


from pathlib import Path
from core.catalog_sig import verify_catalog_directory
from core.catalog_trust import PUBLIC_KEY_SHA256
verify_catalog_directory(Path('checks'), require_signed=True, trusted_public_key_sha256=PUBLIC_KEY_SHA256)
signature_data = [(str(Path('checks') / name), 'checks') for name in ('catalog.pub.pem', 'catalog.sig.json')]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=signature_data + [('checks\\catalog.json', 'checks'), ('checks\\powershell\\firewall.ps1', 'checks\\powershell'), ('checks\\powershell\\defender.ps1', 'checks\\powershell'), ('checks\\powershell\\bitlocker.ps1', 'checks\\powershell'), ('checks\\powershell\\guest_account.ps1', 'checks\\powershell'), ('checks\\powershell\\smbv1.ps1', 'checks\\powershell')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SecureAudit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
