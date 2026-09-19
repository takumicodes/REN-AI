# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/Coding projects/REN-AI-main (1)/REN-AI-main/Ren_Desktop_Assistant/main.py'],
    pathex=['D:/Coding projects/REN-AI-main (1)/REN-AI-main/Ren_Desktop_Assistant'],
    binaries=[],
    datas=[('D:/Coding projects/REN-AI-main (1)/REN-AI-main/Ren_Desktop_Assistant/ren_logo.ico', '.'), ('D:/Coding projects/REN-AI-main (1)/REN-AI-main/Ren_Desktop_Assistant/ren_logo.png', '.')],
    hiddenimports=['preferences', 'system_status', 'system_info', 'system_observer', 'downloads_organizer', 'debloat', 'modes', 'actions', 'history', 'action_registry', 'process_manager', 'startup_manager', 'services_manager', 'storage_cleaner', 'storage_analyzer', 'app_manager', 'tweaks_manager', 'privacy_center', 'network_center', 'health_diagnostics', 'restore_center', 'benchmark', 'app_gui', 'PIL', 'psutil', 'powerplan', 'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
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
    name='Ren Desktop Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/Coding projects/REN-AI-main (1)/REN-AI-main/Ren_Desktop_Assistant/ren_logo.ico'],
)
