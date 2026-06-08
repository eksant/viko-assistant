# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files
from pathlib import Path
import sys

block_cipher = None

VENV = Path(f'.venv/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
WEBENG = VENV / 'PyQt6/Qt6/lib/QtWebEngineCore.framework'
WEBENG_PROC = WEBENG / 'Helpers/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess'
WEBENG_RES  = WEBENG / 'Resources'

datas = [
    ('viko/prompt.txt',      'viko'),
    ('viko/skills',          'viko/skills'),
    ('viko/core',            'viko/core'),
    ('viko/agent',           'viko/agent'),
    ('viko/self_engineer',   'viko/self_engineer'),
    ('viko/ui',              'viko/ui'),
    ('assets',               'assets'),
    # QtWebEngine resources (pak files, icudtl, v8 snapshots)
    (str(WEBENG_RES / 'icudtl.dat'),                              'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources'),
    (str(WEBENG_RES / 'qtwebengine_resources.pak'),               'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources'),
    (str(WEBENG_RES / 'qtwebengine_resources_100p.pak'),          'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources'),
    (str(WEBENG_RES / 'qtwebengine_resources_200p.pak'),          'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources'),
    (str(WEBENG_RES / 'qtwebengine_devtools_resources.pak'),      'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources'),
    (str(WEBENG_RES / 'v8_context_snapshot.arm64.bin'),           'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources'),
    (str(WEBENG_RES / 'qtwebengine_locales'),                     'PyQt6/Qt6/lib/QtWebEngineCore.framework/Resources/qtwebengine_locales'),
]

for pkg in ['google.genai', 'anthropic', 'chromadb', 'PyQt6']:
    pkgdatas, binaries, hiddenimports = collect_all(pkg)
    datas += pkgdatas

binaries = [
    # QtWebEngineProcess helper executable
    (str(WEBENG_PROC), 'PyQt6/Qt6/lib/QtWebEngineCore.framework/Helpers/QtWebEngineProcess.app/Contents/MacOS'),
]

hiddenimports = [
    'viko.skills',
    'viko.core',
    'viko.agent',
    'viko.self_engineer',
    'viko.ui',
    'google.genai',
    'google.generativeai',
    'anthropic',
    'chromadb',
    'sounddevice',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebChannel',
    'objc',
    'Foundation',
    'AppKit',
]

a = Analysis(
    ['viko.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pywinauto', 'pygetwindow'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VIKO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VIKO',
)

app = BUNDLE(
    coll,
    name='VIKO.app',
    icon='assets/icon.icns',
    bundle_identifier='com.eksa.viko',
    info_plist={
        'NSLocationWhenInUseUsageDescription': 'VIKO uses your location to show your position on the map.',
        'NSLocationUsageDescription': 'VIKO uses your location to show your position on the map.',
        'NSMicrophoneUsageDescription': 'VIKO needs microphone access for voice commands.',
        'CFBundleDisplayName': 'VIKO',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIconFile': 'icon',
        'LSUIElement': False,
    },
)
