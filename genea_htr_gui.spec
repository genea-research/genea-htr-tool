# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Get the current directory
current_dir = Path.cwd()

# Define the main script
main_script = 'genea_htr_gui.py'

# Data files to include - handle differently for macOS vs Windows/Linux
if sys.platform == 'darwin':
    # For macOS, put files in Resources folder for proper app bundle structure
    datas = [
        ('htr-app-header.png', 'Resources'),  # Include the header image in Resources folder
        ('htr_settings.json', 'Resources'),   # Include settings file if it exists
        ('README_GUI.md', 'Resources'),       # Include documentation
        ('README.md', 'Resources'),           # Include main documentation
    ]
else:
    # For Windows/Linux, put files in root directory and also in Resources for compatibility
    datas = [
        ('htr-app-header.png', '.'),          # Include the header image in root
        ('htr-app-header.png', 'Resources'),  # Also include in Resources folder for compatibility
        ('htr_settings.json', '.'),           # Include settings file if it exists
        ('htr_settings.json', 'Resources'),   # Also in Resources
        ('README_GUI.md', '.'),               # Include documentation
        ('README.md', '.'),                   # Include main documentation
    ]

# Only include files that actually exist
existing_datas = []
for src, dst in datas:
    if os.path.exists(src):
        existing_datas.append((src, dst))
    else:
        print(f"Warning: {src} not found, skipping...")

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'tkinter.scrolledtext',
    'tkinterdnd2',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'openai',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib.pagesizes',
    'reportlab.platypus',
    'reportlab.lib.styles',
    'reportlab.lib.units',
    'reportlab.lib.utils',
    'json',
    'pathlib',
    'threading',
    'queue',
    'time',
    'webbrowser',
    'base64',
    'glob',
    'datetime',
    'concurrent.futures',
    'tempfile',
    'unicodedata',
    're',
    'io',
    'shutil',
]

# Exclude unnecessary modules to reduce size
excludes = [
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
    'pytest',
    'setuptools',
    'distutils',
]

a = Analysis(
    [main_script],
    pathex=[str(current_dir)],
    binaries=[],
    datas=existing_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# For macOS, create an app bundle only
if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='GeneaHTR',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=False,
        console=False,  # Set to False for GUI app (no console window)
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=False,
        upx_exclude=[],
        name='GeneaHTR'
    )
    
    app = BUNDLE(
        coll,
        name='GeneaHTR.app',
        icon='icons/genea-htr-icon.icns',  # macOS icon
        bundle_identifier='ca.genea.htr',
        info_plist={
            'CFBundleName': 'Genea HTR Tool',
            'CFBundleDisplayName': 'Genea HTR Tool',
            'CFBundleVersion': '0.1',
            'CFBundleShortVersionString': '0.1',
            'CFBundleIdentifier': 'ca.genea.htr',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13',
        },
    )
else:
    # For other platforms, create a regular executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='GeneaHTR',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # Set to False for GUI app (no console window)
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='icons/genea-htr-icon.ico',  # Windows/Linux icon
    )
