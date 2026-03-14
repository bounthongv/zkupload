# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src\\zk_tray_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('encrypted_credentials.bin', '.'),
        ('zk_upload.ico', '.') if os.path.exists('zk_upload.ico') else None,
    ],
    hiddenimports=[
        'pymysql',
        'psycopg2',
        'cryptography',
        'cryptography.fernet',
        'PyQt5',
    ],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='zkupload_tray',
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
