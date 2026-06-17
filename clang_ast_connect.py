# -*- coding: utf-8 -*-
"""
clang_ast_connect.py - Заполнение ccc_connect_list на основе AST Clang.

Анализирует #include директивы в каждом файле и создаёт связи между файлами.
Требуется: compile_commands.json (COMPILE_COMMANDS в LOG_PATH.txt), libclang.
Запускать после find_files (clang_ast_runner не обязателен для path_to_id).

Почему много «пропущено»: find_files добавляет в БД все .cpp/.cc/.c/.h/.hpp/.hxx из дерева проекта,
а в compile_commands.json обычно только единицы компиляции (.cc/.cpp/.c). Заголовки (.h/.hpp) там
редко есть — для них нет флагов -I/-D, поэтому разбор Clang ненадёжен; такие файлы пропускаются.
Связи по #include всё равно получаем из обработанных .cpp/.c (кто какой заголовок подключает).
"""

import os
import sys
import psycopg2

from dbFolder import folder
from clang_runner import get_compile_commands_path, get_build_dir, get_source_files_from_compile_commands
from clang_ast_runner import get_path_to_file_id, parse_file_with_clang, _path_norm, clang


def collect_includes(tu, file_path_norm, path_to_id):
    """
    Сбор #include директив из файла.
    Возвращает список кортежей (file_id включённого файла, номер_строки).
    Один и тот же заголовок на разных строках даёт несколько записей.
    """
    includes = []  # (included_id, line)

    def visit(cursor):
        # libclang новее, чем python-пакет clang: на части узлов .kind даёт
        # ValueError: Unknown template argument kind N — обходим узел без потери поддерева.
        try:
            cur_kind = cursor.kind
        except ValueError:
            cur_kind = None
        except Exception:
            cur_kind = None

        if cur_kind == clang.CursorKind.INCLUSION_DIRECTIVE:
            try:
                loc = cursor.location
                if loc and loc.file:
                    cursor_file = _path_norm(loc.file.name)
                    if cursor_file == file_path_norm:
                        included = cursor.get_included_file()
                        if included:
                            included_path = _path_norm(included.name)
                            included_id = path_to_id.get(included_path)
                            line = loc.line if loc.line else None
                            if included_id:
                                includes.append((included_id, line))
            except Exception:
                pass
        try:
            for child in cursor.get_children():
                visit(child)
        except ValueError:
            pass
        except Exception:
            pass

    visit(tu.cursor)
    return includes


def ensure_table(conn, drop_tbl):
    """Создать/очистить таблицу ccc_connect_list (id_file, connectToID, lineID)."""
    cur = conn.cursor()
    if drop_tbl:
        cur.execute("DROP TABLE IF EXISTS ccc_connect_list CASCADE")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ccc_connect_list (
            id_file     INTEGER,
            connectToID INTEGER,
            lineID      INTEGER
        )
    """)
    try:
        cur.execute("""
            DO $$ BEGIN
                ALTER TABLE ccc_connect_list ADD COLUMN lineID INTEGER;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_connect_file ON ccc_connect_list(id_file)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_connect_to ON ccc_connect_list(connectToID)")
    except Exception:
        pass
    if drop_tbl:
        cur.execute("TRUNCATE TABLE ccc_connect_list")
    conn.commit()


def main():
    if clang is None:
        print("clang_ast_connect: модуль libclang не найден")
        print("Установите: pip3 install libclang или укажите CLANG_LIB в LOG_PATH.txt")
        return

    compile_commands = get_compile_commands_path()
    if not compile_commands:
        print("clang_ast_connect: COMPILE_COMMANDS не задан в LOG_PATH.txt")
        return

    build_dir = get_build_dir(compile_commands)

    try:
        conn = psycopg2.connect(
            database=folder["DB_NAME"],
            user=folder["DB_USER"],
            password=folder["DB_PASS"],
            host=folder["DB_HOST"],
            port=folder["DB_PORT"],
        )
    except Exception as e:
        print("clang_ast_connect: ошибка подключения к БД: {}".format(e))
        return

    path_to_id = get_path_to_file_id(conn)
    if not path_to_id:
        print("clang_ast_connect: ccc_file_list пуст. Сначала выполните find_files.")
        conn.close()
        return

    drop_tbl = int(folder.get("DROP_TBL", "0"))
    ensure_table(conn, drop_tbl)

    cur = conn.cursor()
    cur.execute("SELECT id_file, path FROM ccc_file_list ORDER BY id_file")
    files = cur.fetchall()
    print("clang_ast_connect: файлов в БД: {}".format(len(files)))

    source_files = get_source_files_from_compile_commands(compile_commands)
    source_files_set = {_path_norm(f) for f in source_files}

    total_connections = 0
    processed = 0
    skipped_headers = 0   # .h/.hpp/.hxx не в compile_commands — нет флагов -I/-D
    skipped_not_found = 0
    skipped_parse_failed = 0

    for idx, (file_id, file_path) in enumerate(files, 1):
        file_path_norm = _path_norm(file_path)
        if not os.path.isfile(file_path):
            skipped_not_found += 1
            continue
        is_source = file_path.endswith(('.cpp', '.cc', '.cxx', '.c', '.C'))
        if not is_source and file_path_norm not in source_files_set:
            skipped_headers += 1
            continue
        print("clang_ast_connect: [{}/{}] {}".format(idx, len(files), os.path.basename(file_path)), flush=True)
        sys.stdout.flush()
        tu = parse_file_with_clang(file_path, build_dir, None)
        if tu is None:
            skipped_parse_failed += 1
            continue
        includes = collect_includes(tu, file_path_norm, path_to_id)
        for included_id, line in includes:
            cur.execute(
                "INSERT INTO ccc_connect_list (id_file, connectToID, lineID) VALUES (%s, %s, %s)",
                (file_id, included_id, line),
            )
            total_connections += 1
        processed += 1

    skipped_total = skipped_headers + skipped_not_found + skipped_parse_failed

    conn.commit()

    print("\n" + "=" * 60)
    print("clang_ast_connect: ИТОГО")
    print("=" * 60)
    print("Обработано файлов: {}".format(processed))
    print("Пропущено всего:   {} (см. разбивку ниже)".format(skipped_total))
    print("  — заголовки .h/.hpp/.hxx не из compile_commands: {} (для них нет -I/-D, разбор ненадёжен)".format(skipped_headers))
    print("  — файл не найден на диске: {}".format(skipped_not_found))
    print("  — ошибка разбора Clang:   {}".format(skipped_parse_failed))
    print("Связей создано:    {}".format(total_connections))
    print("=" * 60)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
