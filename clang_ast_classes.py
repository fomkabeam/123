#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clang_ast_classes.py - Заполнение ccc_class_list на основе AST Clang

Заменяет findCppClass при SEARH_METH=CLANG/CLANG_AST и заданном COMPILE_COMMANDS.

Обрабатывает: class, struct, union, вложенные классы, шаблоны.
Исключает forward declarations.

Требуется: compile_commands.json (COMPILE_COMMANDS в LOG_PATH.txt), libclang.
"""

import os
import sys
import json
import psycopg2

from dbFolder import folder

# Настройка libclang (как в clang_ast_runner)
CLANG_LIB_ENV = "CLANG_LIB"
_CLANG_SO_SEARCH_PATHS = [
    "/usr/lib/llvm-6.0/lib/libclang.so.1", "/usr/lib/llvm-6.0/lib/libclang.so",
    "/usr/lib/llvm-14/lib/libclang.so.1", "/usr/lib/llvm-14/lib/libclang.so",
    "/usr/lib/x86_64-linux-gnu/libclang-14.so.1",
    "/usr/lib/llvm-11/lib/libclang.so.1", "/usr/lib/llvm-11/lib/libclang.so",
    "/usr/lib/llvm-10/lib/libclang.so.1", "/usr/lib/llvm-10/lib/libclang.so",
    "/usr/lib/libclang.so.1", "/usr/lib/libclang.so",
]

def _get_libclang_path():
    lib = folder.get(CLANG_LIB_ENV, "").strip() or os.environ.get(CLANG_LIB_ENV)
    if lib and os.path.isfile(lib):
        return lib
    for path in _CLANG_SO_SEARCH_PATHS:
        if os.path.isfile(path):
            return path
    return None

_libclang_path = _get_libclang_path()
if _libclang_path:
    os.environ["LIBCLANG_LIBRARY_FILE"] = _libclang_path
    _libclang_dir = os.path.dirname(_libclang_path)
    _ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    if _libclang_dir not in _ld_path.split(os.pathsep):
        os.environ["LD_LIBRARY_PATH"] = _libclang_dir + (os.pathsep + _ld_path if _ld_path else "")

try:
    import clang.cindex as clang
    if _libclang_path and clang:
        try:
            clang.Config.set_library_file(_libclang_path)
        except Exception:
            pass
except ImportError:
    clang = None

from clang_runner import get_compile_commands_path, get_build_dir
from clang_ast_runner import get_path_to_file_id, parse_file_with_clang


def _path_norm(p):
    if not p:
        return ""
    return os.path.normpath(os.path.abspath(p))


def load_compile_commands(cc_path):
    if not cc_path or not os.path.isfile(cc_path):
        return []
    try:
        with open(cc_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def collect_class_definitions(tu, path_to_id, path_norm, class_id_counter=None):
    """
    Обход AST и сбор определений классов, структур, union.
    class_id_counter — список [следующий_id]; если не передан, создаётся [1] (для одного файла).
    При вызове для многих файлов передавайте один и тот же список, чтобы ID не повторялись.
    Возвращает список кортежей:
    (classID, start_line, end_line, name, id_file, kind, is_template, parent_class_id)
    """
    results = []
    if class_id_counter is None:
        class_id_counter = [1]

    _class_kinds = (
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
    )

    def visit_children(cursor, parent_class_id):
        """Обход потомков; ValueError — несовпадение версий libclang и пакета clang."""
        try:
            for child in cursor.get_children():
                visit(child, parent_class_id)
        except ValueError:
            pass
        except Exception:
            pass

    def visit(cursor, parent_class_id=None):
        try:
            cur_kind = cursor.kind
        except ValueError:
            visit_children(cursor, parent_class_id)
            return
        except Exception:
            visit_children(cursor, parent_class_id)
            return

        if cur_kind not in _class_kinds:
            visit_children(cursor, parent_class_id)
            return

        try:
            is_def = cursor.is_definition()
        except Exception:
            visit_children(cursor, parent_class_id)
            return

        if not is_def:
            visit_children(cursor, parent_class_id)
            return

        loc = cursor.location
        if not loc or not loc.file:
            visit_children(cursor, parent_class_id)
            return

        path = _path_norm(loc.file.name)
        file_id = path_to_id.get(path)
        if file_id is None:
            visit_children(cursor, parent_class_id)
            return

        name = cursor.spelling or cursor.displayname or "?"
        if not name or name == "?":
            visit_children(cursor, parent_class_id)
            return

        start_line = loc.line
        extent = cursor.extent
        end_line = extent.end.line if extent and extent.end else start_line

        if cur_kind == clang.CursorKind.STRUCT_DECL:
            kind = "struct"
        elif cur_kind == clang.CursorKind.UNION_DECL:
            kind = "union"
        else:
            kind = "class"
        is_template = 1 if cur_kind == clang.CursorKind.CLASS_TEMPLATE else 0

        current_classID = class_id_counter[0]
        class_id_counter[0] += 1

        results.append(
            (
                current_classID,
                start_line,
                end_line,
                name,
                file_id,
                kind,
                is_template,
                parent_class_id,
            )
        )

        try:
            for child in cursor.get_children():
                visit(child, parent_class_id=current_classID)
        except ValueError:
            pass
        except Exception:
            pass

    visit(tu.cursor)
    return results


def ensure_table(conn, drop_tbl):
    cur = conn.cursor()
    if drop_tbl:
        cur.execute("DROP TABLE IF EXISTS ccc_class_list CASCADE")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ccc_class_list (
            classID         INTEGER NOT NULL PRIMARY KEY,
            start           INTEGER,
            end_            INTEGER,
            name            TEXT,
            id_file         INTEGER,
            kind            TEXT DEFAULT 'class',
            is_template     INTEGER DEFAULT 0,
            parent_class_id INTEGER
        )
    """)
    for col, col_type, default in [
        ('kind', 'TEXT', "'class'"),
        ('is_template', 'INTEGER', '0'),
        ('parent_class_id', 'INTEGER', 'NULL')
    ]:
        try:
            cur.execute("SELECT {} FROM ccc_class_list LIMIT 0".format(col))
        except Exception:
            try:
                cur.execute("ALTER TABLE ccc_class_list ADD COLUMN {} {} DEFAULT {}".format(col, col_type, default))
                conn.commit()
            except Exception:
                pass
    if drop_tbl:
        cur.execute("TRUNCATE TABLE ccc_class_list")
    conn.commit()


def insert_classes(conn, classes_list):
    cur = conn.cursor()
    for cls in classes_list:
        cur.execute("""
            INSERT INTO ccc_class_list
            (classID, start, end_, name, id_file, kind, is_template, parent_class_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, cls)
    conn.commit()


def main():
    print("clang_ast_classes: Starting...")
    if clang is None:
        print("ERROR: libclang not found. Install: pip3 install libclang")
        return

    try:
        conn = psycopg2.connect(
            database=folder['DB_NAME'],
            user=folder['DB_USER'],
            password=folder['DB_PASS'],
            host=folder['DB_HOST'],
            port=folder['DB_PORT']
        )
    except Exception as e:
        print("ERROR: Cannot connect to database: {}".format(e))
        return

    cc_path = get_compile_commands_path()
    if not cc_path:
        print("ERROR: COMPILE_COMMANDS not set in LOG_PATH.txt")
        return

    build_dir = get_build_dir(cc_path)
    if not build_dir:
        print("ERROR: Cannot determine build directory")
        return

    print("Using compile_commands.json: {}".format(cc_path))

    drop_tbl = int(folder.get('DROP_TBL', 1))
    ensure_table(conn, drop_tbl)

    path_to_id = get_path_to_file_id(conn)
    print("Found {} files in ccc_file_list".format(len(path_to_id)))

    commands = load_compile_commands(cc_path)
    print("Found {} entries in compile_commands.json".format(len(commands)))

    all_classes = []
    processed = 0
    skipped = 0
    class_id_counter = [1]

    for entry in commands:
        file_path = entry.get('file', '')
        if not os.path.isabs(file_path):
            file_path = os.path.join(entry.get('directory', ''), file_path)
        file_norm = _path_norm(file_path)
        file_id = path_to_id.get(file_norm)
        if file_id is None:
            skipped += 1
            continue

        if folder.get('CLANG_DEBUG') == '1':
            print("Parsing {}...".format(file_path))

        tu = parse_file_with_clang(file_path, build_dir, None)
        if tu is None:
            if folder.get('CLANG_DEBUG') == '1':
                print("  ERROR: Failed to parse")
            skipped += 1
            continue

        classes = collect_class_definitions(tu, path_to_id, file_norm, class_id_counter)
        if folder.get('CLANG_DEBUG') == '1':
            print("  Found {} classes".format(len(classes)))
        all_classes.extend(classes)
        processed += 1

    print("Inserting {} classes into database...".format(len(all_classes)))
    insert_classes(conn, all_classes)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ccc_class_list")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ccc_class_list WHERE kind='class'")
    classes_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ccc_class_list WHERE kind='struct'")
    structs_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ccc_class_list WHERE kind='union'")
    unions_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ccc_class_list WHERE parent_class_id IS NOT NULL")
    nested_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ccc_class_list WHERE is_template=1")
    template_count = cur.fetchone()[0]

    print("\n" + "="*60)
    print("STATISTICS:")
    print("="*60)
    print("Files processed: {}".format(processed))
    print("Files skipped:   {}".format(skipped))
    print("Total classes:   {}".format(total))
    print("  - class:       {}".format(classes_count))
    print("  - struct:      {}".format(structs_count))
    print("  - union:       {}".format(unions_count))
    print("  - nested:      {}".format(nested_count))
    print("  - template:    {}".format(template_count))
    print("="*60)

    conn.close()
    print("clang_ast_classes: Done!")


if __name__ == '__main__':
    main()
