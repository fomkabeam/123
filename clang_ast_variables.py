# -*- coding: utf-8 -*-
"""
Поиск неиспользуемых переменных по AST Clang: заполнение ccc_definition_variable,
ccc_use_variable_list и представления ccc_not_use_variable_ast.

Требуется: compile_commands.json (COMPILE_COMMANDS в LOG_PATH.txt), libclang.
Запускать после find_files и clang_ast_runner (для согласованного path_to_id).
Использует ту же инфраструктуру, что и clang_ast_runner.
"""

import os
import sys

import psycopg2

from dbFolder import folder

# Используем общую с clang_ast_runner инфраструктуру парсинга и пути
from clang_ast_runner import (
    get_compile_commands_path,
    get_build_dir,
    get_compile_command_for_file,
    get_source_files_from_compile_commands,
    get_path_to_file_id,
    parse_file_with_clang,
    _path_norm,
    _get_line_from_file,
)
import clang_ast_runner as car
clang = car.clang


def _cursor_kind_safe(cursor):
    try:
        return cursor.kind
    except ValueError:
        return None
    except Exception:
        return None


def _iter_children_safe(cursor):
    try:
        for child in cursor.get_children():
            yield child
    except ValueError:
        return
    except Exception:
        return


def _var_location_key(cursor):
    """Ключ (path, line, column) для однозначной привязки переменной (на одной строке может быть несколько объявлений)."""
    loc = cursor.location
    if not loc or not loc.file:
        return None
    path = _path_norm(loc.file.name)
    return (path, loc.line, loc.column)


def _has_initializer(cursor):
    """Есть ли у переменной инициализатор (для РД НДВ — неинициализированные потенциально опасны)."""
    try:
        for child in _iter_children_safe(cursor):
            k = _cursor_kind_safe(child)
            if k not in (
                getattr(clang.CursorKind, "TYPE_REF", None),
                getattr(clang.CursorKind, "TEMPLATE_REF", None),
            ):
                return True
        return False
    except Exception:
        return False


def _is_security_critical(cursor):
    """Признак критичности для безопасности (пароли, ключи, сертификаты и т.п.) для РД НДВ."""
    var_type = (cursor.type.spelling or "").lower()
    name = (cursor.spelling or "").lower()
    critical = ["password", "key", "token", "secret", "auth", "passwd", "pwd", "credential", "certificate"]
    return any(c in var_type or c in name for c in critical)


def collect_var_definitions(tu, path_to_id, path_norm):
    """
    Обход AST: сбор объявлений переменных (VAR_DECL, PARM_DECL, FIELD_DECL).
    Для VAR_DECL/FIELD_DECL определяется область видимости и static.
    Возвращает список кортежей для вставки и словарь (path, line, col) -> idvar.
    """
    results = []
    key_to_id = {}
    idvar_counter = [0]

    def visit(cursor):
        kind = _cursor_kind_safe(cursor)
        field_decl_kind = getattr(clang.CursorKind, "FIELD_DECL", None)
        if kind not in (clang.CursorKind.VAR_DECL, clang.CursorKind.PARM_DECL, field_decl_kind):
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        loc = cursor.location
        if not loc or not loc.file:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        path = path_norm(loc.file.name)
        file_id = path_to_id.get(path)
        if file_id is None:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        name = (cursor.spelling or "").strip()
        if not name:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        var_type = (cursor.type.spelling or "").strip()
        line_detect = loc.line
        line_text = _get_line_from_file(loc.file.name, line_detect)

        # Определяем scope и is_static
        scope = "local"
        is_static = 0
        parent = getattr(cursor, "semantic_parent", None)
        if kind == clang.CursorKind.PARM_DECL:
            scope = "parameter"
        elif kind == clang.CursorKind.VAR_DECL:
            if parent is not None:
                pk = _cursor_kind_safe(parent)
                if pk == clang.CursorKind.TRANSLATION_UNIT:
                    scope = "global"
                elif pk in (
                    clang.CursorKind.CLASS_DECL,
                    clang.CursorKind.STRUCT_DECL,
                    getattr(clang.CursorKind, "CLASS_TEMPLATE", None),
                    getattr(clang.CursorKind, "CXX_RECORD_DECL", None),
                ):
                    scope = "class_member"
                else:
                    scope = "local"
            stor_static = getattr(getattr(clang, "StorageClass", None), "STATIC", None)
            if stor_static is not None and getattr(cursor, "storage_class", None) == stor_static:
                is_static = 1
        elif field_decl_kind is not None and kind == field_decl_kind:
            scope = "class_member"
            stor_static = getattr(getattr(clang, "StorageClass", None), "STATIC", None)
            if stor_static is not None and getattr(cursor, "storage_class", None) == stor_static:
                is_static = 1

        has_init = 1 if _has_initializer(cursor) else 0
        is_sec = 1 if _is_security_critical(cursor) else 0
        key = (path, line_detect, loc.column)
        idvar_counter[0] += 1
        idvar = idvar_counter[0]
        results.append((idvar, file_id, name, var_type, line_detect, line_text, scope, is_static, has_init, is_sec, key))
        key_to_id[key] = idvar
        for child in _iter_children_safe(cursor):
            visit(child)

    visit(tu.cursor)
    return results, key_to_id


def collect_var_uses(tu, path_to_id, path_norm, var_key_to_id):
    """
    Обход AST: сбор использований переменных.
    Учитывает DECL_REF_EXPR (обычные переменные) и MEMBER_REF_EXPR (поля классов obj.member).
    Возвращает список (id, idvar, use_in_file_id, line_id, line_text).
    """
    results = []
    id_counter = [0]
    decl_ref = clang.CursorKind.DECL_REF_EXPR
    member_ref = getattr(clang.CursorKind, "MEMBER_REF_EXPR", None)
    valid_ref_kinds = {
        clang.CursorKind.VAR_DECL,
        clang.CursorKind.PARM_DECL,
    }
    field_decl_kind = getattr(clang.CursorKind, "FIELD_DECL", None)
    if field_decl_kind is not None:
        valid_ref_kinds.add(field_decl_kind)

    def add_use(ref, use_cursor):
        key = _var_location_key(ref)
        if key is None:
            return
        idvar = var_key_to_id.get(key)
        if idvar is None:
            return
        loc = use_cursor.location
        if not loc or not loc.file:
            return
        path = path_norm(loc.file.name)
        use_in_file_id = path_to_id.get(path)
        if use_in_file_id is None:
            return
        line_id = loc.line
        line_text = _get_line_from_file(loc.file.name, line_id)
        id_counter[0] += 1
        results.append((id_counter[0], idvar, use_in_file_id, line_id, line_text))

    def visit(cursor):
        kind = _cursor_kind_safe(cursor)
        ref = None
        if kind == decl_ref:
            ref = getattr(cursor, "referenced", None)
        elif member_ref is not None and kind == member_ref:
            ref = getattr(cursor, "referenced", None)
        if ref is None or _cursor_kind_safe(ref) not in valid_ref_kinds:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        add_use(ref, cursor)
        for child in _iter_children_safe(cursor):
            visit(child)

    visit(tu.cursor)
    return results


def ensure_tables(conn, drop_tbl):
    """Создать/очистить таблицы переменных и представление неиспользуемых."""
    cur = conn.cursor()
    if drop_tbl:
        cur.execute("DROP VIEW IF EXISTS ccc_not_use_variable_ast CASCADE")
        cur.execute("DROP TABLE IF EXISTS ccc_use_variable_list CASCADE")
        cur.execute("DROP TABLE IF EXISTS ccc_definition_variable CASCADE")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ccc_definition_variable(
            idvar               INTEGER PRIMARY KEY,
            file_id             INTEGER,
            name                TEXT,
            var_type            TEXT,
            line_detect         INTEGER,
            line                TEXT,
            scope               TEXT,
            is_static           INTEGER DEFAULT 0,
            has_init            INTEGER DEFAULT 0,
            is_security_critical INTEGER DEFAULT 0
        )
    """)
    # На случай старой схемы — добавляем недостающие колонки
    for col, col_type, default in [
        ("scope", "TEXT", "NULL"),
        ("is_static", "INTEGER", "0"),
        ("has_init", "INTEGER", "0"),
        ("is_security_critical", "INTEGER", "0"),
    ]:
        try:
            cur.execute("SELECT {} FROM ccc_definition_variable LIMIT 0".format(col))
        except Exception:
            try:
                cur.execute(
                    "ALTER TABLE ccc_definition_variable ADD COLUMN {} {} DEFAULT {}".format(
                        col, col_type, default
                    )
                )
            except Exception:
                pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ccc_use_variable_list(
            id      INTEGER NOT NULL PRIMARY KEY,
            idvar   INTEGER,
            use_in  INTEGER,
            line_id INTEGER,
            line    TEXT
        )
    """)
    cur.execute("TRUNCATE TABLE ccc_definition_variable")
    cur.execute("TRUNCATE TABLE ccc_use_variable_list")
    cur.execute("DROP VIEW IF EXISTS ccc_not_use_variable_ast")
    cur.execute("""
        CREATE VIEW ccc_not_use_variable_ast AS
        SELECT
            v.idvar,
            v.file_id,
            v.name,
            v.var_type,
            v.line_detect,
            v.line,
            v.scope,
            v.is_static,
            v.has_init,
            v.is_security_critical,
            CASE
                WHEN v.is_security_critical = 1 THEN 'CRITICAL'
                WHEN (v.has_init = 0 OR v.has_init IS NULL) AND v.scope IN ('local', 'global') THEN 'HIGH'
                WHEN v.scope = 'parameter' THEN 'MEDIUM'
                ELSE 'LOW'
            END AS severity
        FROM ccc_definition_variable v
        WHERE NOT EXISTS (SELECT 1 FROM ccc_use_variable_list u WHERE u.idvar = v.idvar)
          AND (
                (v.scope <> 'parameter' OR (v.scope = 'parameter' AND v.name NOT LIKE '\\_%'))
             OR (v.is_security_critical = 1)
          )
    """)
    conn.commit()


def main():
    if clang is None:
        print("clang_ast_variables: модуль libclang не найден (зависит от clang_ast_runner).")
        return
    compile_commands = get_compile_commands_path()
    if not compile_commands:
        print("clang_ast_variables: COMPILE_COMMANDS не задан — выход.")
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
        print("clang_ast_variables: ошибка подключения к БД: {}".format(e))
        return

    path_to_id = get_path_to_file_id(conn)
    if not path_to_id:
        print("clang_ast_variables: ccc_file_list пуст. Сначала выполните find_files.")
        conn.close()
        return

    drop_tbl = int(folder.get("DROP_TBL", "0"))
    ensure_tables(conn, drop_tbl)

    files = get_source_files_from_compile_commands(compile_commands)
    if not files:
        print("clang_ast_variables: нет исходных файлов в compile_commands.json.")
        conn.close()
        return

    path_norm = _path_norm
    total_files = len(files)
    print("clang_ast_variables: файлов: {}, сбор определений и использований (один проход по файлам).".format(total_files), flush=True)
    sys.stdout.flush()

    all_defs = []
    all_uses = []
    var_key_to_id = {}
    idvar_global = [0]
    use_id = [0]
    cur = conn.cursor()

    for idx, fpath in enumerate(files, 1):
        path = path_norm(fpath)
        if path not in path_to_id:
            continue
        print("clang_ast_variables: [{}/{}] {}".format(idx, total_files, os.path.basename(fpath)), flush=True)
        sys.stdout.flush()
        tu = parse_file_with_clang(fpath, build_dir, None)
        if tu is None:
            continue
        # Один парсинг на файл: сначала определения, затем использования (корректный порядок внутри файла).
        # var_key_to_id — глобальный ключ (path, line, col) -> idvar; обновляется здесь до collect_var_uses,
        # чтобы использования получали правильный idvar.
        defs, _ = collect_var_definitions(tu, path_to_id, path_norm)
        for d in defs:
            key = d[10] if len(d) > 10 else (path, d[4], 0)
            if key in var_key_to_id:
                continue
            idvar_global[0] += 1
            idvar = idvar_global[0]
            var_key_to_id[key] = idvar
            all_defs.append((idvar, d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9]))
        uses = collect_var_uses(tu, path_to_id, path_norm, var_key_to_id)
        for u in uses:
            use_id[0] += 1
            all_uses.append((use_id[0], u[1], u[2], u[3], u[4]))

    for r in all_defs:
        cur.execute("""
            INSERT INTO ccc_definition_variable (idvar, file_id, name, var_type, line_detect, line, scope, is_static, has_init, is_security_critical)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, r)
    for u in all_uses:
        cur.execute(
            "INSERT INTO ccc_use_variable_list (id, idvar, use_in, line_id, line) VALUES (%s, %s, %s, %s, %s)",
            u
        )
    conn.commit()
    print("clang_ast_variables: определений: {}, использований: {}".format(len(all_defs), use_id[0]))
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
