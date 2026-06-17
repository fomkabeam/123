#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ДИАГНОСТИЧЕСКИЙ СКРИПТ ДЛЯ ПРОБЛЕМЫ "ПУСТОЙ AST"

Этот скрипт проверяет:
1. Доступен ли libclang
2. Правильно ли настроен compile_commands.json
3. Совпадают ли пути файлов
4. Может ли Clang реально распарсить файл

Запуск: python3 diagnose_clang_parse.py
"""

import os
import sys
import json

# Python 3.5: os.fspath появился в 3.6; libclang при set_library_file() его использует
if not hasattr(os, "fspath"):
    def _fspath(path):
        if isinstance(path, str):
            return path
        if hasattr(path, "__fspath__"):
            return path.__fspath__()
        return str(path)
    os.fspath = _fspath

def _load_config():
    """Загрузка конфига из LOG_PATH.txt без импорта dbFolder (скрипт может запускаться из другого каталога)."""
    search_dirs = []
    if getattr(sys, "frozen", False):
        search_dirs.append(os.path.dirname(os.path.abspath(sys.executable)))
    else:
        search_dirs.append(os.path.dirname(os.path.abspath(__file__)))
    search_dirs.append(os.getcwd())
    if os.path.isdir("/opt/cpp-analyzer"):
        search_dirs.append("/opt/cpp-analyzer")
    config = {}
    for base in search_dirs:
        path = os.path.join(base, "LOG_PATH.txt")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key, value = key.strip(), value.strip()
                            if key:
                                config[key] = value
                return config
            except Exception:
                pass
    return config

print("=" * 70)
print("ДИАГНОСТИКА ПРОБЛЕМЫ CLANG AST")
print("=" * 70)

# Конфиг загружаем сразу, чтобы в шаге 1 использовать CLANG_LIB (приоритет над путём по умолчанию)
folder = _load_config()
if not folder:
    folder = {}

# ===== ШАГ 1: Проверка libclang =====
print("\n[ШАГ 1] Проверка libclang...")

try:
    import clang.cindex as clang
    print("[+] clang.cindex импортирован")
except ImportError as e:
    print("[X] КРИТИЧНО: clang.cindex не найден!")
    print("   Ошибка:", e)
    print("   Решение: pip3 install libclang")
    sys.exit(1)

# Сначала путь из конфига (CLANG_LIB), затем стандартные пути; приоритет — новым LLVM (16, 19, 14), потом 6
clang_lib_config = (folder.get("CLANG_LIB") or "").strip()
standard_paths = [
    "/usr/lib/llvm-16/lib/libclang.so.1",
    "/usr/lib/llvm-19/lib/libclang.so.1",
    "/usr/lib/llvm-14/lib/libclang.so.1",
    "/usr/lib/llvm-6.0/lib/libclang.so.1",
    "/usr/lib/x86_64-linux-gnu/libclang-14.so.1",
    "/usr/lib/libclang.so.1",
]
libclang_candidates = ([clang_lib_config] if clang_lib_config else []) + standard_paths

found_lib = None
for path in libclang_candidates:
    if path and os.path.isfile(path):
        found_lib = path
        break

if found_lib:
    if found_lib == clang_lib_config:
        print("[+] libclang из конфига (CLANG_LIB):", found_lib)
    else:
        print("[+] libclang найден:", found_lib)
    try:
        clang.Config.set_library_file(found_lib)
        print("[+] libclang загружен успешно")
    except Exception as e:
        print("[!]  Не удалось загрузить:", e)
else:
    print("[!]  libclang.so не найден в стандартных путях")
    print("   Задайте CLANG_LIB в LOG_PATH.txt или установите LLVM (см. SETUP_GUIDE.md)")

# ===== ШАГ 2: Проверка конфигурации =====
print("\n[ШАГ 2] Проверка конфигурации...")

if not folder:
    folder = _load_config()
if not folder:
    print("[X] Ошибка загрузки конфигурации: LOG_PATH.txt не найден.")
    print("   Искали в: каталог скрипта, текущий каталог, /opt/cpp-analyzer")
    sys.exit(1)
print("[+] Конфиг загружен из LOG_PATH.txt")

# Проверка ключевых параметров
checks = {
    "DB_NAME": folder.get("DB_NAME"),
    "COMPILE_COMMANDS": folder.get("COMPILE_COMMANDS"),
    "PATH_FILE": folder.get("PATH_FILE"),
}
for key, value in checks.items():
    if value:
        print("  {}: {}".format(key, value))
    else:
        print("  [X] {}: НЕ ЗАДАН!".format(key))

compile_commands_path = folder.get("COMPILE_COMMANDS", "").strip()

if not compile_commands_path:
    print("\n[X] КРИТИЧНО: COMPILE_COMMANDS не задан в LOG_PATH.txt!")
    sys.exit(1)

if not os.path.isfile(compile_commands_path):
    print("\n[X] КРИТИЧНО: Файл не найден: {}".format(compile_commands_path))
    sys.exit(1)

print("[+] compile_commands.json найден: {}".format(compile_commands_path))

# ===== ШАГ 3: Анализ compile_commands.json =====
print("\n[ШАГ 3] Анализ compile_commands.json...")

try:
    with open(compile_commands_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("[+] Загружено записей: {}".format(len(data)))
    
    if len(data) == 0:
        print("[X] КРИТИЧНО: compile_commands.json пустой!")
        sys.exit(1)
    
    # Берём первый файл для анализа
    first_entry = data[0]
    
    print("\n--- ПЕРВАЯ ЗАПИСЬ ---")
    print("file:      {}".format(first_entry.get('file', 'НЕТ')))
    print("directory: {}".format(first_entry.get('directory', 'НЕТ')))
    
    command = first_entry.get('command', '')
    if command:
        print("command:   {}...".format(command[:100]))  # Первые 100 символов
        
        # Извлекаем -I пути
        import re
        includes = re.findall(r'-I(\S+)', command)
        print("\n-I пути ({} штук):".format(len(includes)))
        for i, inc in enumerate(includes[:5], 1):  # Первые 5
            print("  {}. {}".format(i, inc))
        if len(includes) > 5:
            print("  ... и ещё {}".format(len(includes) - 5))
    else:
        print("command:   НЕТ!")
    
except json.JSONDecodeError as e:
    print("[X] КРИТИЧНО: Ошибка парсинга JSON: {}".format(e))
    sys.exit(1)
except Exception as e:
    print("[X] Ошибка чтения файла: {}".format(e))
    sys.exit(1)

# ===== ШАГ 4: Проверка БД =====
print("\n[ШАГ 4] Проверка подключения к БД...")

try:
    import psycopg2
    
    conn = psycopg2.connect(
        database=folder["DB_NAME"],
        user=folder["DB_USER"],
        password=folder["DB_PASS"],
        host=folder["DB_HOST"],
        port=folder["DB_PORT"],
    )
    
    print("[+] Подключение к БД успешно")
    
    cur = conn.cursor()
    
    # Проверка таблиц
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('ccc_file_list', 'cpp_files')
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    if tables:
        print("[+] Найдены таблицы: {}".format(', '.join(tables)))
    else:
        print("[!]  Таблицы файлов не найдены")
    
    # Проверка количества файлов
    for table in ['ccc_file_list', 'cpp_files']:
        try:
            cur.execute("SELECT COUNT(*) FROM {}".format(table))
            count = cur.fetchone()[0]
            print("  {}: {} записей".format(table, count))
        except Exception:
            pass
    
    conn.close()

except Exception as e:
    print("[X] Ошибка подключения к БД: {}".format(e))
    sys.exit(1)

# ===== ШАГ 5: РЕАЛЬНЫЙ ТЕСТ ПАРСИНГА =====
print("\n[ШАГ 5] Тестовый парсинг файла из compile_commands.json...")

test_file = first_entry.get('file')
test_dir = first_entry.get('directory')

if not test_file:
    print("[X] В первой записи нет поля 'file'")
    sys.exit(1)

if not os.path.isabs(test_file):
    test_file = os.path.join(test_dir or '', test_file)

test_file = os.path.normpath(os.path.abspath(test_file))

print("\nТестовый файл: {}".format(test_file))
print("Существует: {}".format(os.path.isfile(test_file)))

if not os.path.isfile(test_file):
    print("[X] КРИТИЧНО: Тестовый файл не найден!")
    print("   Проверьте что пути в compile_commands.json правильные")
    sys.exit(1)

# Пытаемся распарсить
print("\nПопытка парсинга с помощью libclang...")

try:
    index = clang.Index.create()
    
    # Извлекаем аргументы компиляции
    command = first_entry.get('command', '')
    
    import re
    args = []
    
    # -I пути
    for m in re.finditer(r'-I(\S+)', command):
        args.append('-I' + m.group(1))
    
    # -D макросы
    for m in re.finditer(r'-D\s*(\S+)', command):
        args.append('-D' + m.group(1))
    
    # -std=
    m_std = re.search(r'-std=(\S+)', command)
    if m_std:
        args.append('-std=' + m_std.group(1))
    
    # -fPIC
    if '-fPIC' in command:
        args.append('-fPIC')
    
    print("Аргументы компиляции ({} штук):".format(len(args)))
    for i, arg in enumerate(args[:10], 1):
        print("  {}. {}".format(i, arg))
    if len(args) > 10:
        print("  ... и ещё {}".format(len(args) - 10))
    
    print("\nПарсинг...")
    
    tu = index.parse(
        test_file,
        args=args,
        options=clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    )
    
    if not tu:
        print("[X] КРИТИЧНО: parse() вернул None!")
        print("   Clang не смог распарсить файл")
        print("\n---  ДИАГНОСТИКА:")
        print("   1. Проверьте что все include пути правильные")
        print("   2. Проверьте что все зависимости (Qt, protobuf и т.д.) установлены")
        print("   3. Попробуйте вручную скомпилировать файл:")
        print("      cd {}".format(test_dir))
        print("      g++ -fsyntax-only {} {}".format(' '.join(args[:5]), test_file))
        sys.exit(1)
    
    errors = []
    children = []
    # Проверяем диагностики (ошибки компиляции)
    diags = list(tu.diagnostics)
    
    print("[+] Файл распарсен!")
    print("   Диагностик: {}".format(len(diags)))
    
    if diags:
        print("\n[!]  ПРЕДУПРЕЖДЕНИЯ И ОШИБКИ:")
        for i, diag in enumerate(diags[:5], 1):
            severity = {
                clang.Diagnostic.Ignored: "IGNORED",
                clang.Diagnostic.Note: "NOTE",
                clang.Diagnostic.Warning: "WARNING",
                clang.Diagnostic.Error: "ERROR",
                clang.Diagnostic.Fatal: "FATAL",
            }.get(diag.severity, "?")
            
            print("  {}. [{}] {}".format(i, severity, diag.spelling))
            if diag.location and diag.location.file:
                print("     {}:{}".format(diag.location.file.name, diag.location.line))
        
        if len(diags) > 5:
            print("  ... и ещё {}".format(len(diags) - 5))
        
        # Проверка на критичные ошибки
        errors[:] = [d for d in diags if d.severity >= clang.Diagnostic.Error]
        
        if errors:
            print("\n[X] КРИТИЧНО: Обнаружено {} ошибок компиляции!".format(len(errors)))
            print("   Clang не может построить AST при наличии ошибок компиляции")
            print("\n---  ВОЗМОЖНЫЕ ПРИЧИНЫ:")
            
            # Анализируем ошибки
            error_texts = [d.spelling.lower() for d in errors[:10]]
            
            has_not_found = any('file not found' in t or 'no such file' in t for t in error_texts)
            has_undeclared = any('undeclared' in t or 'was not declared' in t for t in error_texts)
            
            if has_not_found:
                print("   ✗ Не найдены заголовочные файлы")
                print("     → Проверьте пути -I в compile_commands.json")
                print("     → Установите недостающие библиотеки (Qt, protobuf и т.д.)")
            
            if has_undeclared:
                print("   ✗ Необъявленные идентификаторы")
                print("     → Возможно не подключены нужные заголовки")
                print("     → Проверьте макросы -D")
    
    # Проверяем курсор
    cursor = tu.cursor
    
    if not cursor:
        print("\n[X] КРИТИЧНО: tu.cursor = None (пустой AST)!")
        sys.exit(1)
    
    # Считаем дочерние узлы
    children[:] = list(cursor.get_children())
    
    print("\n[+] AST построен!")
    print("   Дочерних узлов: {}".format(len(children)))
    
    if len(children) == 0:
        print("\n[X] КРИТИЧНО: AST пустой (нет дочерних узлов)!")
        print("   Это означает что Clang не смог разобрать содержимое файла")
        print("\n---  ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("   1. Файл пустой или содержит только комментарии")
        print("   2. Критичные ошибки компиляции блокируют парсинг")
        print("   3. Неправильные флаги компиляции")
    else:
        print("\n[+] ВСЁ В ПОРЯДКЕ! AST содержит узлы.")
        print("   Первые узлы:")
        for i, child in enumerate(children[:5], 1):
            print("     {}. {}: {}".format(i, child.kind, child.spelling or '(анонимный)'))
    
except clang.LibclangError as e:
    err_msg = str(e)
    print("\n[X] НЕСОВМЕСТИМОСТЬ ВЕРСИЙ libclang")
    print("   Ошибка: {}".format(err_msg))
    print("\n---  ПРИЧИНА:")
    print("   На системе установлен libclang из LLVM 6, а пакет Python 'libclang'")
    print("   с pip рассчитан на более новую версию (в PyPI нет libclang 6.x).")
    print("\n---  РЕШЕНИЕ (выберите один вариант):")
    print("\n   Вариант А — системные Python-привязки под LLVM 6 (если есть в репозитории):")
    print("      apt-cache search python3 clang")
    print("      # Если есть python3-clang-6 или python3-clang — установите его и удалите pip-пакет:")
    print("      sudo apt install python3-clang-6   # или как покажет search")
    print("      pip3 uninstall libclang")
    print("\n   Вариант Б — установить новый LLVM из репозитория apt.llvm.org:")
    print("      wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh")
    print("      sudo ./llvm.sh 14")
    print("      pip3 install 'libclang==14.0.6'")
    print("      В LOG_PATH.txt добавьте строку:")
    print("      CLANG_LIB=/usr/lib/llvm-14/lib/libclang.so.1")
    print("\n   Подробное руководство: SETUP_GUIDE.md (раздел 3 — LLVM и libclang).")
    print("\n" + "=" * 70)
    sys.exit(1)
except Exception as e:
    print("\n[X] ОШИБКА при парсинге: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== ФИНАЛЬНЫЙ ВЫВОД =====
print("\n" + "=" * 70)
print("ИТОГИ ДИАГНОСТИКИ")
print("=" * 70)

if errors:
    if len(children) > 0:
        print("\n[!] AST построен (узлов: {}), но есть ошибки компиляции (например, не найден заголовок Qt).".format(len(children)))
        print("   Libclang работает; для полного анализа без диагностик установите зависимости или проверьте пути -I.")
    else:
        print("\n[X] ПРОБЛЕМА НАЙДЕНА: Ошибки компиляции блокируют парсинг")
    print("\n---  РЕШЕНИЯ:")
    print("1. Проверьте что все зависимости установлены:")
    print("   sudo apt-get install libqt5-dev qtbase5-dev protobuf-compiler")
    print("\n2. Проверьте пути -I в compile_commands.json")
    print("\n3. Попробуйте скомпилировать файл вручную:")
    print("   cd {}".format(test_dir))
    print("   g++ -fsyntax-only {}".format(test_file))
    print("\n4. Если это Qt проект, убедитесь что используется правильный compile_commands:")
    print("   cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..")
elif len(children) == 0:
    print("\n[X] ПРОБЛЕМА: Пустой AST (нет узлов)")
    print("   Файл распарсился, но дочерних узлов нет")
else:
    print("\n[+] ВСЁ РАБОТАЕТ ПРАВИЛЬНО!")
    print("   Если при построении графа всё равно ошибки,")
    print("   проблема в другом месте (не в Clang парсинге)")

print("\n" + "=" * 70)
