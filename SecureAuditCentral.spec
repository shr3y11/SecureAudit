# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

tk_fallback = []
for folder, destination in [('tcl-core-8-6-12', '_tcl_data'), ('tk-core-8-6-12', '_tk_data')]:
    library = Path('.tools') / folder / 'library'
    if library.exists():
        tk_fallback.append((str(library), destination))

psycopg_datas, psycopg_binaries, psycopg_hidden = collect_all('psycopg')
binary_datas, binary_binaries, binary_hidden = collect_all('psycopg_binary')
a = Analysis(
    ['launcher.py'], pathex=[],
    binaries=psycopg_binaries + binary_binaries,
    datas=[('secureaudit_central/static', 'secureaudit_central/static'), ('checks', 'checks')] + psycopg_datas + binary_datas + tk_fallback,
    hiddenimports=['sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.postgresql.psycopg', 'uvicorn.logging', 'uvicorn.loops.asyncio', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.lifespan.on'] + psycopg_hidden + binary_hidden,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['pytest', 'httpx'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='SecureAuditCentral', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, runtime_tmpdir=None,
          console=False, disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)
