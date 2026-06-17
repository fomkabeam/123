# -*- mode: python ; coding: utf-8 -*-
# Сборка анализатора C++ и GUI в один исполняемый файл (PyInstaller).

import os

# Каталог с исходниками (каталог, где лежит этот .spec)
project_dir = SPECPATH
graph_analyser_dir = os.path.join(project_dir, 'GraphAnalyserC++')

# Модули «движка» анализа, запускаемые через _Starter и --run-script
analyzer_modules = [
    '_Starter',
    '_Start_Multy_Java',
    'dbFolder',
    'find_files',
    'createReport',
    'findUseFunction',
    'findUseFunction_V2',
    'findFunction',
    'funcToNormal',
    'NEW_3_F_Line_Seg',
    'NEW_4_Variabels_C',
    'usingVariables',
    'NEW_5_JSensor_NEW_Variant',
    'NEW_5_JSensor_NEW_Variant_mod',
    'create_sensoragramma_table',
    'sensor_registry_builder',
    'sensor_coverage_report',
    'real_sensor_analyzer',
    'clang_runner',
    'clang_ast_runner',
    'clang_ast_classes',
    'clang_ast_connect',
    'clang_ast_var_view',
    'clang_ast_variables',
    'Find_border_secses_V2',
    'NEW_1_ComOrText',
    'NEW_SUP_CHECK_POS',
    'NEW_SUP_info_class_or_func',
    'NEW_SAVE_Param_STR',
    'findBrk',
    'pasteSensor',
    'make_file_connect',
    'findConnectionBetweenFilesCpp',
    'findDefind',
    'finderCommentAndQuoatsInCppLineCode',
    'perl_calls_qprocess',
    'perl_files_in_quoats',
    'startQprocess',
    'QProcess',
    'commentsAndQuotes',
]

a = Analysis(
    ['gui_main.py'],
    pathex=[project_dir, graph_analyser_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        # служебные и внешние модули
        'runpy',
        'psycopg2',
        # libclang (Python-обёртка для CLANG_AST; нативная libclang.so — из пакета ОС)
        'clang',
        'clang.cindex',
        # модули GUI
        'gui_config',
        'gui_method_labels',
        'gui_analyzer',
        'gui_results',
        'gui_redundancy',
        'gui_checksums',
        'gui_graph',
        'gui_dynamic',
        'graph_runner',
        'find_nodes_clang_cpp',
        # граф вызовов — в PYZ, без извлечения в tmp
        'structures',
        'find_files_cpp',
        'find_nodes_cpp',
        'find_nodes_regex_cpp',
        'create_graph_cpp',
        'set_block_id_cpp',
        'find_func_cpp',
        'sync_cpp_func_from_ccc',
        'graphviz',
        'networkx',
        # основной «движок» анализа
    ] + analyzer_modules,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='cpp-analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI без консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

