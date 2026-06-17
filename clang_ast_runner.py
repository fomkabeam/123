# -*- coding: utf-8 -*-
"""
Заполнение ccc_definition_function и ccc_use_function_list на основе AST Clang.
Требуется: compile_commands.json (COMPILE_COMMANDS в LOG_PATH.txt), libclang.

Перед запуском: find_files и при необходимости findConnectionBetweenFilesCpp уже выполнены,
ccc_file_list заполнен. Пути в compile_commands.json должны совпадать с путями в ccc_file_list
(нормализуем через os.path.normpath/abspath при сопоставлении).

Зависимость: pip3 install libclang  (или пакет ОС python3-clang / libclang-*-dev и при необходимости
CLANG_LIB в LOG_PATH.txt). При запуске из собранного exe/deb libclang не подхватывается — запускайте
из исходников: python3 main.py (после pip3 install libclang).
"""

import os
import sys
import json
import re
import time

import psycopg2

from dbFolder import folder

# Ключи для поиска libclang (опционально в LOG_PATH.txt: CLANG_LIB=/usr/lib/llvm-6.0/lib/libclang.so.1)
CLANG_LIB_ENV = "CLANG_LIB"

# Типичные пути к libclang.so на Astra / Debian (LLVM 6 на Astra, остальные — на всякий случай)
_CLANG_SO_SEARCH_PATHS = [
    "/usr/lib/llvm-6.0/lib/libclang.so.1",
    "/usr/lib/llvm-6.0/lib/libclang.so",
    "/usr/lib/llvm-14/lib/libclang.so.1",
    "/usr/lib/llvm-14/lib/libclang.so",
    "/usr/lib/x86_64-linux-gnu/libclang-14.so.1",
    "/usr/lib/llvm-11/lib/libclang.so.1",
    "/usr/lib/llvm-11/lib/libclang.so",
    "/usr/lib/x86_64-linux-gnu/libclang-11.so.1",
    "/usr/lib/llvm-10/lib/libclang.so.1",
    "/usr/lib/llvm-10/lib/libclang.so",
    "/usr/lib/libclang.so.1",
    "/usr/lib/libclang.so",
]


def _get_libclang_path_before_import():
    """Путь к libclang.so до импорта clang.cindex (для frozen exe — загрузка при импорте)."""
    lib = folder.get(CLANG_LIB_ENV, "").strip() or os.environ.get(CLANG_LIB_ENV)
    if lib and os.path.isfile(lib):
        return lib
    for path in _CLANG_SO_SEARCH_PATHS:
        if os.path.isfile(path):
            return path
    return None


# Задать путь до импорта: в frozen exe загрузчик ищет libclang.so при импорте/первом использовании
_libclang_path = _get_libclang_path_before_import()
if _libclang_path:
    os.environ["LIBCLANG_LIBRARY_FILE"] = _libclang_path
    # Каталог с .so в LD_LIBRARY_PATH — чтобы загрузчик нашёл libclang.so по короткому имени
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


def _find_system_libclang():
    """Ищем libclang.so в типичных путях (для exe/deb без pip)."""
    for path in _CLANG_SO_SEARCH_PATHS:
        if os.path.isfile(path):
            return path
    return None


def _init_libclang():
    """Повторно выставить путь (если не выставили до импорта)."""
    if clang is None:
        return False
    lib = folder.get(CLANG_LIB_ENV, "").strip() or os.environ.get(CLANG_LIB_ENV)
    if not lib or not os.path.isfile(lib):
        lib = _find_system_libclang()
    if lib and os.path.isfile(lib):
        try:
            clang.Config.set_library_file(lib)
            return True
        except Exception:
            pass
    return True

# Повторно используем утилиты из clang_runner (после блока с clang)
from clang_runner import (
    get_compile_commands_path,
    get_build_dir,
    get_compile_command_for_file,
    get_compile_command_for_file_norm,
    get_extra_args_from_command,
    get_source_files_from_compile_commands,
)


def _path_norm(p):
    if not p:
        return ""
    return os.path.normpath(os.path.abspath(p))


def get_path_to_file_id(conn):
    """Словарь normpath(path) -> id_file из ccc_file_list."""
    cur = conn.cursor()
    cur.execute("SELECT id_file, path FROM ccc_file_list")
    rows = cur.fetchall()
    return {_path_norm(r[1]): r[0] for r in rows if r[1]}


def _get_line_from_file(file_path, line_num, encoding="utf-8"):
    """Вернуть строку текста файла по номеру (1-based), иначе пустую."""
    if not file_path or not os.path.isfile(file_path):
        return ""
    try:
        with open(file_path, encoding=encoding, errors="replace") as f:
            for i, line in enumerate(f, 1):
                if i == line_num:
                    return line.rstrip("\n\r")
    except Exception:
        pass
    return ""


def _cursor_location_key(cursor):
    """Ключ (path, line) для однозначной привязки к определению функции."""
    loc = cursor.location
    if not loc or not loc.file:
        return None
    path = _path_norm(loc.file.name)
    return (path, loc.line)


def _cursor_full_name(cursor):
    """Имя функции с учётом класса/неймспейса (spelling или displayname)."""
    name = cursor.spelling or cursor.displayname or ""
    if not name and _cursor_kind_safe(cursor) == clang.CursorKind.CXX_METHOD:
        # метод без имени (конструктор и т.д.) — тип возврата не нужен для имени
        return (cursor.type.spelling or "").split("(")[0].strip() or "?"
    return name


def _cursor_kind_safe(cursor):
    """
    Безопасное чтение cursor.kind.
    На рассинхроне libclang/python bindings может падать:
    ValueError: Unknown template argument kind N.
    """
    try:
        return cursor.kind
    except ValueError:
        return None
    except Exception:
        return None


def _iter_children_safe(cursor):
    """Безопасный обход потомков курсора."""
    try:
        for child in cursor.get_children():
            yield child
    except ValueError:
        return
    except Exception:
        return


def _get_param_func(cursor):
    """Параметры функции в виде строки (упрощённо). У FUNCTION_DECL — дети PARM_DECL."""
    parts = []
    for child in _iter_children_safe(cursor):
        if _cursor_kind_safe(child) == clang.CursorKind.PARM_DECL:
            parts.append(child.type.spelling or "?")
    return "(" + ", ".join(parts) + ")"


def _param_count_from_param_func(param_func):
    """Число параметров по строке param_func вида '(int, float)' или '()'. Нужно для различения перегрузок."""
    if not param_func or param_func.strip() == "()":
        return 0
    return param_func.count(",") + 1


def _call_get_num_arguments(call_cursor):
    """Число аргументов в вызове (CALL_EXPR). Совместимо с разными версиями libclang."""
    try:
        return call_cursor.get_num_arguments()
    except Exception:
        try:
            return len(list(call_cursor.get_arguments()))
        except Exception:
            children = list(_iter_children_safe(call_cursor))
            return max(0, len(children) - 1)


def _is_template_function(cursor):
    """True, если функция — шаблон или инстанциирование шаблона (часто ложное «неиспользуемая» в header-only)."""
    try:
        kind_ft = getattr(clang.CursorKind, "FUNCTION_TEMPLATE", None)
        if kind_ft is None:
            return False
        c = cursor
        while c:
            if getattr(c, "kind", None) == kind_ft:
                return True
            try:
                c = c.semantic_parent
            except Exception:
                break
        return False
    except Exception:
        return False


def collect_function_definitions(tu, path_to_id, path_norm):
    """
    Обход AST и сбор определений функций (FUNCTION_DECL с is_definition()).
    Возвращает список кортежей для вставки в ccc_definition_function и
    словарь (path_norm, line) -> idfunc для последующего разрешения вызовов.
    """
    results = []
    key_to_id = {}
    idfunc_counter = [0]  # mutable

    def visit(cursor):
        cur_kind = _cursor_kind_safe(cursor)
        if cur_kind == clang.CursorKind.FUNCTION_DECL and cursor.is_definition():
            loc = cursor.location
            if not loc or not loc.file:
                return
            path = _path_norm(loc.file.name)
            file_id = path_to_id.get(path)
            if file_id is None:
                return
            name = _cursor_full_name(cursor)
            if not name or name == "?":
                return
            # Пропускаем шаблонные инстанцииции без имени и т.п.
            if cursor.spelling == "" and "operator" in (cursor.displayname or ""):
                return
            start_line = loc.line
            start_col = loc.column
            end_line = loc.line
            end_col = loc.column
            extent = cursor.extent
            if extent:
                end = extent.end
                if end and end.file and end.file.name:
                    end_line = end.line
                    end_col = end.column
            idfunc_counter[0] += 1
            idfunc = idfunc_counter[0]
            param_func = _get_param_func(cursor)
            result_type = (cursor.type.get_result().spelling or "").strip()
            modifier_and_return_type = result_type or ""
            line_detect = start_line
            line_text = _get_line_from_file(loc.file.name, start_line)
            is_tmpl = 1 if _is_template_function(cursor) else 0
            # IDfromAllList — как в funcToNormal, можно совпадает с idfunc
            results.append((
                idfunc, idfunc, file_id, name, param_func, line_detect,
                start_line, start_col, end_line, end_col,
                modifier_and_return_type, line_text, is_tmpl
            ))
            key = (path, start_line)
            key_to_id[key] = idfunc
        for child in _iter_children_safe(cursor):
            visit(child)

    visit(tu.cursor)
    return results, key_to_id


def _get_arg_types_from_call(cursor):
    """
    Получить типы аргументов из вызова для более точного сопоставления перегрузок.
    Старается быть совместимым с разными версиями libclang.
    """
    arg_types = []
    try:
        if hasattr(cursor, "get_arguments"):
            for arg in cursor.get_arguments():
                if hasattr(arg, "type") and arg.type is not None:
                    arg_types.append(arg.type.spelling)
        else:
            children = list(_iter_children_safe(cursor))
            for child in children[1:]:
                if hasattr(child, "type") and child.type is not None:
                    arg_types.append(child.type.spelling)
    except Exception:
        pass
    return arg_types


def _normalize_type(type_str):
    """Упрощённая нормализация строкового представления типа."""
    if not type_str:
        return ""
    return " ".join(type_str.split())


def _match_overload_by_types(candidates, call_arg_types, idfunc_to_signature):
    """
    Сопоставление перегрузок по типам аргументов.
    candidates: список idfunc
    call_arg_types: типы аргументов вызова
    idfunc_to_signature: idfunc -> [типы параметров]
    """
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates

    norm_call = [_normalize_type(t) for t in call_arg_types]

    exact = []
    for idf in candidates:
        sig = idfunc_to_signature.get(idf, [])
        norm_sig = [_normalize_type(t) for t in sig]
        if norm_sig == norm_call:
            exact.append(idf)

    if exact:
        return exact
    return candidates


def _parse_param_types(param_func):
    """
    Разбор типов параметров из строки param_func, например:
    "(int, float, const char*)" -> ["int", "float", "const char*"]
    """
    if not param_func or param_func.strip() == "()":
        return []
    s = param_func.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    types = []
    current = ""
    depth = 0
    for ch in s:
        if ch == "<":
            depth += 1
            current += ch
        elif ch == ">":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            types.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        types.append(current.strip())
    return types


def collect_calls(tu, path_to_id, path_norm, def_key_to_id, name_to_idfunc=None, idfunc_to_file_id=None, name_nargs_to_idfunc=None):
    """
    Обход AST и сбор вызовов функций (CALL_EXPR).
    Сначала привязка по (path, line) определения; если нет (вызов из другого TU) — по имени и числу аргументов,
    затем по имени. При нескольких кандидатах (перегрузки) добавляется по одной записи на каждого — все считаются используемыми.
    Возвращает список кортежей (ID, IDfunc, name, from_, useIn, lineID, line).
    """
    results = []
    id_counter = [0]
    name_to_idfunc = name_to_idfunc or {}
    idfunc_to_file_id = idfunc_to_file_id or {}
    name_nargs_to_idfunc = name_nargs_to_idfunc or {}

    _CXX_MEMBER_CALL_EXPR = getattr(clang.CursorKind, "CXX_MEMBER_CALL_EXPR", None)

    def visit(cursor):
        ref = None
        cur_kind = _cursor_kind_safe(cursor)
        if cur_kind == clang.CursorKind.CALL_EXPR:
            ref = cursor.referenced
        elif _CXX_MEMBER_CALL_EXPR and cur_kind == _CXX_MEMBER_CALL_EXPR:
            ref = getattr(cursor, "referenced", None)
            if ref is None:
                for child in _iter_children_safe(cursor):
                    if getattr(child, "referenced", None) is not None:
                        ref = child.referenced
                        break
        if ref is None:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        if cur_kind == getattr(clang.CursorKind, "CXX_MEMBER_CALL_EXPR", None):
            pass
        elif cur_kind != clang.CursorKind.CALL_EXPR:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        valid_ref = (clang.CursorKind.FUNCTION_DECL, clang.CursorKind.CXX_METHOD)
        if _cursor_kind_safe(ref) not in valid_ref:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        name = _cursor_full_name(ref) or ref.spelling or "?"
        if not name or name == "?":
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        loc = cursor.location
        if not loc or not loc.file:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        path = _path_norm(loc.file.name)
        use_in_file_id = path_to_id.get(path)
        if use_in_file_id is None:
            for child in _iter_children_safe(cursor):
                visit(child)
            return
        line_id = loc.line
        line_text = _get_line_from_file(loc.file.name, line_id)

        idfunc = None
        from_file_id = None
        def_cursor = ref.get_definition() if hasattr(ref, "get_definition") else ref
        if def_cursor is None:
            def_cursor = ref
        if getattr(def_cursor, "is_definition", lambda: False)():
            key = _cursor_location_key(def_cursor)
            if key is not None:
                idfunc = def_key_to_id.get(key)
                if idfunc is not None:
                    ref_path = _path_norm(def_cursor.location.file.name) if def_cursor.location and def_cursor.location.file else ""
                    from_file_id = path_to_id.get(ref_path)

        candidates = []
        if idfunc is None and (name_to_idfunc or name_nargs_to_idfunc):
            call_nargs = _call_get_num_arguments(cursor)
            candidates = name_nargs_to_idfunc.get((name, call_nargs), [])
            if not candidates:
                candidates = name_to_idfunc.get(name, [])
            if len(candidates) == 1:
                idfunc = candidates[0]
                from_file_id = idfunc_to_file_id.get(idfunc)
            elif len(candidates) > 1:
                idfunc = candidates[0]
                from_file_id = idfunc_to_file_id.get(idfunc)

        if idfunc is None and from_file_id is None:
            if not candidates:
                if folder.get("CLANG_LOG_UNRESOLVED", "").strip().lower() in ("1", "yes", "true"):
                    print("WARNING: Unresolved call '{}' at {}:{}".format(name, path, line_id))
                for child in _iter_children_safe(cursor):
                    visit(child)
                return
            idf = candidates[0]
            from_fid = idfunc_to_file_id.get(idf)
            if from_fid is not None:
                id_counter[0] += 1
                results.append((
                    id_counter[0], idf, name, from_fid, use_in_file_id, line_id, line_text
                ))
            for child in _iter_children_safe(cursor):
                visit(child)
            return

        if idfunc is not None and from_file_id is not None:
            id_counter[0] += 1
            results.append((
                id_counter[0], idfunc, name, from_file_id, use_in_file_id, line_id, line_text
            ))
        for child in _iter_children_safe(cursor):
            visit(child)

    visit(tu.cursor)
    return results


def collect_calls_v2(
    tu,
    path_to_id,
    path_norm,
    def_key_to_id,
    name_to_idfunc=None,
    idfunc_to_file_id=None,
    name_nargs_to_idfunc=None,
    idfunc_to_signature=None,
):
    """
    Расширенная версия collect_calls:
    - обрабатывает методы класса (CXX_MEMBER_CALL_EXPR)
    - учитывает перегрузки по типам аргументов через idfunc_to_signature
    """
    results = []
    id_counter = [0]
    name_to_idfunc = name_to_idfunc or {}
    idfunc_to_file_id = idfunc_to_file_id or {}
    name_nargs_to_idfunc = name_nargs_to_idfunc or {}
    idfunc_to_signature = idfunc_to_signature or {}

    if clang is None:
        return results

    def visit(cursor):
        kind = _cursor_kind_safe(cursor)
        if kind == clang.CursorKind.CALL_EXPR:
            _process_call_expr(cursor)
        elif kind == getattr(clang.CursorKind, "CXX_MEMBER_CALL_EXPR", None):
            _process_member_call_expr(cursor)
        for child in _iter_children_safe(cursor):
            visit(child)

    def _process_call_expr(cursor):
        ref = cursor.referenced
        if ref is None:
            return
        valid_kinds = (clang.CursorKind.FUNCTION_DECL, clang.CursorKind.CXX_METHOD)
        if hasattr(clang.CursorKind, "FUNCTION_TEMPLATE"):
            valid_kinds = valid_kinds + (clang.CursorKind.FUNCTION_TEMPLATE,)
        if _cursor_kind_safe(ref) not in valid_kinds:
            return
        _register_call(cursor, ref)

    def _process_member_call_expr(cursor):
        ref = getattr(cursor, "referenced", None)
        if ref and _cursor_kind_safe(ref) == clang.CursorKind.CXX_METHOD:
            _register_call(cursor, ref)
            return
        children = list(_iter_children_safe(cursor))
        if not children:
            return
        member_ref = children[0]
        ref = getattr(member_ref, "referenced", None)
        if ref and _cursor_kind_safe(ref) == clang.CursorKind.CXX_METHOD:
            _register_call(cursor, ref)

    def _register_call(call_cursor, ref_cursor):
        name = _cursor_full_name(ref_cursor) or ref_cursor.spelling or "?"
        if not name or name == "?":
            return

        loc = call_cursor.location
        if not loc or not loc.file:
            return

        path = _path_norm(loc.file.name)
        use_in_file_id = path_to_id.get(path)
        if use_in_file_id is None:
            return

        line_id = loc.line
        line_text = _get_line_from_file(loc.file.name, line_id)

        idfunc = None
        from_file_id = None

        def_cursor = ref_cursor.get_definition() if hasattr(ref_cursor, "get_definition") else ref_cursor
        if def_cursor is None:
            def_cursor = ref_cursor
        if def_cursor and getattr(def_cursor, "is_definition", lambda: False)():
            key = _cursor_location_key(def_cursor)
            if key:
                idfunc = def_key_to_id.get(key)
                if idfunc:
                    def_path = _path_norm(def_cursor.location.file.name)
                    from_file_id = path_to_id.get(def_path)

        if idfunc is None:
            call_arg_types = _get_arg_types_from_call(call_cursor)
            call_nargs = len(call_arg_types)

            candidates = name_nargs_to_idfunc.get((name, call_nargs), [])
            if not candidates:
                candidates = name_to_idfunc.get(name, [])

            if candidates:
                matched = _match_overload_by_types(candidates, call_arg_types, idfunc_to_signature)
            else:
                matched = []

            if len(matched) == 1:
                idfunc = matched[0]
                from_file_id = idfunc_to_file_id.get(idfunc)
            elif len(matched) > 1:
                # несколько подходящих — считаем все использованными
                for idf in matched:
                    from_fid = idfunc_to_file_id.get(idf)
                    if from_fid:
                        id_counter[0] += 1
                        results.append(
                            (id_counter[0], idf, name, from_fid, use_in_file_id, line_id, line_text)
                        )
                return

        if idfunc and from_file_id:
            id_counter[0] += 1
            results.append(
                (id_counter[0], idfunc, name, from_file_id, use_in_file_id, line_id, line_text)
            )

    visit(tu.cursor)
    return results


def ensure_tables(conn, drop_tbl):
    """Создать/очистить ccc_definition_function и ccc_use_function_list, пересоздать представления."""
    cur = conn.cursor()
    if drop_tbl:
        cur.execute("DROP TABLE IF EXISTS ccc_use_function_list CASCADE")
        cur.execute("DROP TABLE IF EXISTS ccc_definition_function CASCADE")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ccc_definition_function(
            IDfunc          INTEGER,
            IDfromAllList   INTEGER,
            file_id         INTEGER,
            name            TEXT,
            param_func      TEXT,
            line_detect     INTEGER,
            start_line      INTEGER,
            start_pos       INTEGER,
            end_line        INTEGER,
            end_pos         INTEGER,
            modifier_and_return_type TEXT,
            line            TEXT,
            is_template     INTEGER DEFAULT 0
        )
    """)
    try:
        cur.execute("SELECT is_template FROM ccc_definition_function LIMIT 0")
    except Exception:
        try:
            cur.execute("ALTER TABLE ccc_definition_function ADD COLUMN is_template INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ccc_use_function_list(
            ID      INTEGER NOT NULL PRIMARY KEY,
            IDfunc  INTEGER,
            name    TEXT,
            from_   INTEGER,
            useIn   INTEGER,
            lineID  INTEGER,
            line    TEXT
        )
    """)
    # При запуске AST-анализа всегда очищаем таблицы функций (заполняем только из Clang)
    cur.execute("TRUNCATE TABLE ccc_definition_function")
    cur.execute("TRUNCATE TABLE ccc_use_function_list")
    cur.execute("DROP VIEW IF EXISTS ccc_where_use_function_V2")
    cur.execute("""
        CREATE VIEW ccc_where_use_function_V2 AS
        SELECT ccc_use_function_list.idfunc, ccc_use_function_list.name,
               ccc_definition_function.file_id, ccc_definition_function.idfunc UseInFuncID
        FROM ccc_use_function_list, ccc_definition_function
        WHERE (ccc_use_function_list.useIn = ccc_definition_function.file_id)
          AND (ccc_definition_function.start_line <= ccc_use_function_list.lineID)
          AND (ccc_definition_function.end_line >= ccc_use_function_list.lineID)
    """)
    cur.execute("DROP VIEW IF EXISTS ccc_not_use_function")
    cur.execute("""
        CREATE VIEW ccc_not_use_function AS
        SELECT ccc_definition_function.idfunc, ccc_definition_function.name, ccc_definition_function.file_id,
               ccc_definition_function.line_detect, ccc_definition_function.line
        FROM ccc_definition_function
        WHERE ccc_definition_function.idfunc NOT IN (
            SELECT ccc_use_function_list.idfunc FROM ccc_use_function_list
        ) AND ccc_definition_function.name != 'main' AND (ccc_definition_function.name IS NULL OR strpos(ccc_definition_function.name, 'operator') = 0)
          AND (ccc_definition_function.is_template IS NULL OR ccc_definition_function.is_template = 0)
    """)
    conn.commit()

    # Журнал проблем парсинга AST (translation units), чтобы видеть качество разбора.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ccc_ast_parse_failures (
            event_id   BIGSERIAL PRIMARY KEY,
            ts         TIMESTAMP DEFAULT now(),
            stage      TEXT,
            file_path  TEXT,
            reason     TEXT,
            details    TEXT
        )
        """
    )
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ast_fail_ts ON ccc_ast_parse_failures(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ast_fail_file ON ccc_ast_parse_failures(file_path)")
    except Exception:
        pass
    conn.commit()


def _log_diagnostics(tu, file_path, log_func=None):
    """Вывести диагностики Clang (ошибки и фатальные) — чтобы видеть причину «не удалось разобрать» (Python 3.5-совместимо)."""
    if not tu or not tu.diagnostics:
        return
    err_level = 4
    out = log_func if log_func else print
    out("--- Диагностика Clang для файла: {} ---".format(file_path))
    for d in tu.diagnostics:
        if d.severity >= err_level:
            out("  ОШИБКА: {}".format(d.spelling or ""))
            if getattr(d, "location", None) and getattr(d.location, "file", None) and d.location.file:
                out("  В файле: {}, строка {}, столбец {}".format(
                    d.location.file.name, getattr(d.location, "line", 0), getattr(d.location, "column", 0)))
    out("---")


def parse_file_with_clang(file_path, build_dir, args, log_func=None):
    """Построить TranslationUnit для файла с заданными аргументами. При ошибке вернуть None.
    log_func(str) — при наличии выводит диагностики Clang при ошибках парсинга."""
    tu, _reason, _details = parse_file_with_clang_result(file_path, build_dir, args, log_func=log_func)
    return tu


def parse_file_with_clang_result(file_path, build_dir, args, log_func=None):
    """
    Как parse_file_with_clang, но возвращает (tu, reason, details).
    reason:
      - ok
      - libclang_missing
      - no_compile_command
      - clang_error
      - exception
    """
    if clang is None:
        return None, "libclang_missing", "clang module is None"
    entry = get_compile_command_for_file(build_dir, file_path) or get_compile_command_for_file_norm(build_dir, file_path)
    if not entry:
        return None, "no_compile_command", "file not found in compile_commands.json"
    cmd = entry.get("command") or entry.get("arguments")
    if isinstance(cmd, list):
        args = [a for a in cmd[1:] if a != file_path]
    else:
        args = get_extra_args_from_command(cmd or "")
    index = clang.Index.create()
    try:
        tu = index.parse(file_path, args=args, options=clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        if tu.diagnostics:
            for d in tu.diagnostics:
                if d.severity >= 4:  # Error
                    if log_func:
                        _log_diagnostics(tu, file_path, log_func)
                    return None, "clang_error", d.spelling or "clang error"
        return tu, "ok", ""
    except Exception as e:
        return None, "exception", str(e)


def parse_header_using_cpp_command(header_path, build_dir, cpp_path, log_func=None):
    """
    Разобрать заголовочный файл (.h и т.д.), используя флаги компиляции того .cpp,
    который его подключает (в compile_commands есть только .cpp/.c, для .h записи нет).
    log_func(str) — при наличии выводит диагностики Clang при ошибках.
    """
    if clang is None:
        return None
    entry = get_compile_command_for_file(build_dir, cpp_path) or get_compile_command_for_file_norm(build_dir, cpp_path)
    if not entry:
        return None
    cmd = entry.get("command") or entry.get("arguments")
    if isinstance(cmd, list):
        args = [a for a in cmd[1:] if a != cpp_path]
    else:
        args = get_extra_args_from_command(cmd or "")
    index = clang.Index.create()
    try:
        tu = index.parse(header_path, args=args, options=clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        if tu.diagnostics:
            for d in tu.diagnostics:
                if d.severity >= 4:
                    if log_func:
                        _log_diagnostics(tu, header_path, log_func)
                    return None
        return tu
    except Exception:
        return None


def main():
    if clang is None:
        print("clang_ast_runner: модуль libclang не найден.")
        print("  Установите: pip3 install libclang  (при запуске из исходников).")
        print("  При сборке exe/deb добавьте в spec hiddenimports: clang, clang.cindex и пересоберите.")
        return
    _init_libclang()
    # Проверка загрузки нативной библиотеки (libclang.so ставится из пакета ОС)
    try:
        clang.Index.create()
    except Exception as e:
        err = str(e).lower()
        print("clang_ast_runner: не удалось загрузить libclang.so.")
        if "undefined symbol" in err or "compatible with your libclang" in err:
            print("  Несовместимость версий: Python-обёртка (libclang из pip) новее, чем libclang.so на системе (например, LLVM 6 на Astra).")
            print("  Пересоберите exe/deb с более старой обёрткой: на машине сборки выполните:")
            print("    pip3 install libclang==9.0.1")
            print("  затем заново соберите пакет. На машине пользователя должен быть установлен libclang-6.0-dev (или аналог).")
        else:
            print("  Установите пакет ОС с libclang.so (Astra: libclang-6.0-dev уже даёт /usr/lib/llvm-6.0/lib/).")
            print("  Либо укажите в LOG_PATH.txt: CLANG_LIB=/usr/lib/llvm-6.0/lib/libclang.so.1")
        print("  Ошибка: {}".format(e))
        return
    compile_commands = get_compile_commands_path()
    if not compile_commands:
        print("clang_ast_runner: COMPILE_COMMANDS не задан — выход.")
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
        print("clang_ast_runner: ошибка подключения к БД: {}".format(e))
        return

    path_to_id = get_path_to_file_id(conn)
    if not path_to_id:
        print("clang_ast_runner: ccc_file_list пуст. Сначала выполните find_files.")
        conn.close()
        return

    drop_tbl = int(folder.get("DROP_TBL", "0"))
    ensure_tables(conn, drop_tbl)

    files_raw = get_source_files_from_compile_commands(compile_commands)
    if not files_raw:
        print("clang_ast_runner: нет исходных файлов в compile_commands.json.")
        conn.close()
        return

    # Один и тот же .cpp в compile_commands может быть в нескольких записях (разные цели сборки).
    # Обрабатываем каждый путь один раз — убираем дубликаты по нормализованному пути.
    seen_paths = set()
    files = []
    for fpath in files_raw:
        p = _path_norm(fpath)
        if p not in seen_paths:
            seen_paths.add(p)
            files.append(fpath)
    total_files = len(files)
    if len(files_raw) != total_files:
        print("clang_ast_runner: записей в compile_commands: {}, уникальных файлов: {} (дубликаты пропущены).".format(len(files_raw), total_files), flush=True)
    print("clang_ast_runner: файлов к разбору: {}, разбор может занять много минут.".format(total_files), flush=True)
    sys.stdout.flush()

    path_norm = _path_norm
    all_defs = []
    def_key_to_id = {}
    idfunc_global = [0]
    t0 = time.time()
    failed_stage1 = 0
    parsed_stage1 = 0

    # Проход 1: собрать определения, дедуплицируя по (path, line) — одна функция из заголовка
    # не должна попадать в БД по разу на каждый .cpp, иначе десятки тысяч "неиспользуемых"
    for idx, fpath in enumerate(files, 1):
        path = path_norm(fpath)
        if path not in path_to_id:
            continue
        print("clang_ast_runner: [1/2] [{}/{}] {}".format(idx, total_files, os.path.basename(fpath)), flush=True)
        sys.stdout.flush()
        tu, reason, details = parse_file_with_clang_result(fpath, build_dir, None, log_func=print)
        if tu is None:
            failed_stage1 += 1
            try:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO ccc_ast_parse_failures (stage, file_path, reason, details) VALUES (%s, %s, %s, %s)",
                    ("defs", fpath, reason, details),
                )
                conn.commit()
                c.close()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            continue
        parsed_stage1 += 1
        defs, key_to_id = collect_function_definitions(tu, path_to_id, path_norm)
        # Для каждого def ключ (path файла определения, line) — key_to_id: key -> local_id
        key_for_local = {local_id: k for (k, local_id) in key_to_id.items()}
        local_to_global = {}
        for d in defs:
            key = key_for_local.get(d[0])
            if key is None:
                continue
            if key in def_key_to_id:
                # Уже видели эту функцию (тот же файл и строка) — не дублируем запись, только маппинг для вызовов
                local_to_global[d[0]] = def_key_to_id[key]
            else:
                idfunc_global[0] += 1
                idfunc = idfunc_global[0]
                def_key_to_id[key] = idfunc
                local_to_global[d[0]] = idfunc
                # d[12] — is_template (если есть), иначе 0
                all_defs.append((idfunc, idfunc, d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11], d[12] if len(d) > 12 else 0))

    cur = conn.cursor()
    for r in all_defs:
        cur.execute("""
            INSERT INTO ccc_definition_function
            (IDfunc, IDfromAllList, file_id, name, param_func, line_detect, start_line, start_pos, end_line, end_pos, modifier_and_return_type, line, is_template)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, r)
    conn.commit()
    print("clang_ast_runner: определений функций: {}".format(len(all_defs)))

    # По имени ищем idfunc при вызовах из другого TU (get_definition() не переходит в другой файл).
    # Индексируем по полному имени и по короткому (после последнего "::"); по (name, nargs) — для различения перегрузок.
    name_to_idfunc = {}
    name_nargs_to_idfunc = {}
    idfunc_to_file_id = {}
    for r in all_defs:
        idf, _, file_id, name, param_func = r[0], r[1], r[2], r[3], r[4]
        idfunc_to_file_id[idf] = file_id
        if name:
            name_to_idfunc.setdefault(name, []).append(idf)
            nargs = _param_count_from_param_func(param_func)
            name_nargs_to_idfunc.setdefault((name, nargs), []).append(idf)
            short = name.split("::")[-1] if "::" in name else name
            if short != name:
                name_to_idfunc.setdefault(short, []).append(idf)
                name_nargs_to_idfunc.setdefault((short, nargs), []).append(idf)

    # Сигнатуры функций для точного разрешения перегрузок по типам
    idfunc_to_signature = {}
    for r in all_defs:
        idf = r[0]
        param_func = r[4]
        idfunc_to_signature[idf] = _parse_param_types(param_func)

    # Проход 2: вызовы
    print("clang_ast_runner: проход 2/2 — сбор вызовов (имя+число аргументов, перегрузки помечаются используемыми).", flush=True)
    sys.stdout.flush()
    use_id = [0]
    failed_stage2 = 0
    parsed_stage2 = 0
    for idx, fpath in enumerate(files, 1):
        path = path_norm(fpath)
        if path not in path_to_id:
            continue
        print("clang_ast_runner: [2/2] [{}/{}] {}".format(idx, total_files, os.path.basename(fpath)), flush=True)
        sys.stdout.flush()
        tu, reason, details = parse_file_with_clang_result(fpath, build_dir, None, log_func=print)
        if tu is None:
            failed_stage2 += 1
            try:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO ccc_ast_parse_failures (stage, file_path, reason, details) VALUES (%s, %s, %s, %s)",
                    ("calls", fpath, reason, details),
                )
                conn.commit()
                c.close()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            continue
        parsed_stage2 += 1
        calls = collect_calls_v2(
            tu,
            path_to_id,
            path_norm,
            def_key_to_id,
            name_to_idfunc,
            idfunc_to_file_id,
            name_nargs_to_idfunc,
            idfunc_to_signature,
        )
        for c in calls:
            use_id[0] += 1
            cur.execute(
                "INSERT INTO ccc_use_function_list (ID, IDfunc, name, from_, useIn, lineID, line) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (use_id[0], c[1], c[2], c[3], c[4], c[5], c[6])
            )
    conn.commit()
    print("clang_ast_runner: вызовов (в наших определениях): {}".format(use_id[0]))
    elapsed = time.time() - t0
    print(
        "clang_ast_runner: итоги: файлов={}, defs_ok={}, defs_fail={}, calls_ok={}, calls_fail={}, время={:.1f}s".format(
            total_files, parsed_stage1, failed_stage1, parsed_stage2, failed_stage2, elapsed
        ),
        flush=True,
    )
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
