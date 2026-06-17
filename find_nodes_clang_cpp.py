# -*- coding: utf-8 -*-
"""
Построение дерева узлов для графа вызовов по Clang AST (вариант A).
Заполняет cpp_type_nodes и cpp_parent_child в том же формате, что и find_nodes_cpp,
чтобы дальше работали fill_graph -> set_block_id -> find_func_cpp -> create_full_graph.

COMPILE_COMMANDS берётся из LOG_PATH (dbFolder). Если граф строится после основного
анализа — можно взять данные из уже построенных таблиц ccc_definition_function,
ccc_use_function_list, ccc_file_list (fill_nodes_from_ccc).
"""

import os
import sys

# GraphAnalyserC++ должен быть в sys.path (graph_runner добавляет перед вызовом)
import find_nodes_cpp

from dbFolder import folder
from clang_runner import (
    get_compile_commands_path,
    get_build_dir,
    get_source_files_from_compile_commands,
)


def _path_norm(p):
    if not p:
        return ""
    return os.path.normpath(os.path.abspath(p))


def _cursor_kind_safe(cursor):
    try:
        return cursor.kind
    except ValueError:
        return None
    except Exception:
        return None


def _iter_children_safe(cursor):
    try:
        for c in cursor.get_children():
            yield c
    except ValueError:
        return
    except Exception:
        return


def _get_call_name(cursor, clang):
    """Имя вызываемой функции по курсору CALL_EXPR (учёт методов классов)."""
    try:
        ref = cursor.referenced
        if not ref:
            return cursor.displayname or cursor.spelling or "?"
        kind = _cursor_kind_safe(ref)
        name = ref.spelling or ref.displayname or ""
        if kind == clang.CursorKind.CXX_METHOD:
            parent = getattr(ref, "semantic_parent", None)
            class_name = ""
            if parent and _cursor_kind_safe(parent) in (clang.CursorKind.CLASS_DECL, clang.CursorKind.STRUCT_DECL):
                class_name = parent.spelling or ""
            base = name or (ref.type.spelling or "").split("(")[0].strip()
            if class_name:
                name = "{}::{}".format(class_name, base)
            else:
                name = base
        return name or "?"
    except Exception:
        return cursor.displayname or cursor.spelling or "?"


def _cursor_in_file(cursor, file_path_norm):
    """Проверка: курсор из текущего файла (не из включённого заголовка)."""
    try:
        loc = cursor.location
        if not loc or not loc.file:
            return True
        return _path_norm(loc.file.name) == file_path_norm
    except Exception:
        return True


def build_tree_from_clang(tu, file_path, clang_module, max_depth=1000):
    """
    Строит дерево в формате find_nodes_cpp (как regex): Module.body — плоский список
    Import, Namespace, ClassDef, FunctionDef (у FunctionDef — body с Call).
    Только узлы из текущего файла (file_path). Namespace/ClassDef с body=[] и не вкладываем
    в них дочерние объявления — они идут в module_body (как в regex).
    """
    clang = clang_module
    file_path_norm = _path_norm(file_path)
    module_body = []
    body_stack = [module_body]

    def visit(cursor, depth=0):
        if depth > max_depth:
            return
        kind = _cursor_kind_safe(cursor)
        in_this_file = _cursor_in_file(cursor, file_path_norm)
        if kind == clang.CursorKind.INCLUSION_DIRECTIVE:
            if in_this_file:
                try:
                    included = cursor.get_included_file()
                    path = included.name if included else ""
                except Exception:
                    path = ""
                name = os.path.basename(path) if path else ""
                body_stack[-1].append({
                    "type": "Import",
                    "path": path,
                    "names": [name] if name else [],
                })
            for c in _iter_children_safe(cursor):
                visit(c)
            return
        if kind == clang.CursorKind.NAMESPACE and in_this_file:
            name = cursor.spelling or ""
            body_stack[-1].append({"type": "Namespace", "name": name, "body": []})
            for c in _iter_children_safe(cursor):
                visit(c)
            return
        if kind == clang.CursorKind.CXX_RECORD_DECL and in_this_file:
            name = cursor.spelling or ""
            if name:
                body_stack[-1].append({"type": "ClassDef", "name": name, "body": []})
            for c in _iter_children_safe(cursor):
                visit(c)
            return
        func_kinds = (
            clang.CursorKind.FUNCTION_DECL,
            clang.CursorKind.CXX_METHOD,
            getattr(clang.CursorKind, "CONSTRUCTOR", None),
            getattr(clang.CursorKind, "DESTRUCTOR", None),
        )
        if kind in func_kinds and getattr(cursor, "is_definition", lambda: False)() and in_this_file:
            # Имя функции/метода с учётом класса
            name = cursor.spelling or cursor.displayname or ""
            if kind in (clang.CursorKind.CXX_METHOD, getattr(clang.CursorKind, "CONSTRUCTOR", None), getattr(clang.CursorKind, "DESTRUCTOR", None)):
                parent = getattr(cursor, "semantic_parent", None)
                class_name = ""
                if parent and _cursor_kind_safe(parent) in (clang.CursorKind.CLASS_DECL, clang.CursorKind.STRUCT_DECL):
                    class_name = parent.spelling or ""
                if kind == getattr(clang.CursorKind, "CONSTRUCTOR", None):
                    base = class_name
                elif kind == getattr(clang.CursorKind, "DESTRUCTOR", None):
                    base = "~{}".format(class_name) if class_name else name
                else:
                    base = name or (cursor.type.spelling or "").split("(")[0].strip()
                if class_name:
                    name = "{}::{}".format(class_name, base)
                else:
                    name = base
            args_list = []
            for c in _iter_children_safe(cursor):
                if _cursor_kind_safe(c) == clang.CursorKind.PARM_DECL:
                    args_list.append(c.type.spelling or "?")
            node = {
                "type": "FunctionDef",
                "name": name or "?",
                "args": {"type": "arguments", "args": args_list},
                "body": [],
                "is_static": getattr(cursor, "storage_class", None) == getattr(clang.StorageClass, "STATIC", None),
                "is_inline": getattr(cursor, "is_inline_function", lambda: False)(),
            }
            body_stack[-1].append(node)
            body_stack.append(node["body"])
            for c in _iter_children_safe(cursor):
                visit(c, depth + 1)
            body_stack.pop()
            return
        if kind == clang.CursorKind.CALL_EXPR and in_this_file:
            name = _get_call_name(cursor, clang)
            if name and name != "?":
                body_stack[-1].append({"type": "Call", "func": name})
            for c in _iter_children_safe(cursor):
                visit(c, depth + 1)
            return
        for c in _iter_children_safe(cursor):
            visit(c, depth + 1)

    try:
        visit(tu.cursor, 0)
    except Exception:
        pass
    return {"type": "Module", "body": module_body}


def _header_to_cpp_map(cur):
    """Словарь normpath(заголовка) -> normpath(.cpp), который его подключает (из ccc_connect_list)."""
    try:
        cur.execute("""
            SELECT f1.path AS cpp_path, f2.path AS header_path
            FROM ccc_connect_list c
            JOIN ccc_file_list f1 ON f1.id_file = c.id_file
            JOIN ccc_file_list f2 ON f2.id_file = c.connectToID
        """)
        out = {}
        for (cpp_path, header_path) in cur.fetchall():
            if header_path and cpp_path:
                out[_path_norm(header_path)] = _path_norm(cpp_path)
        return out
    except Exception:
        return {}


def _same_dir_cpp(header_path_norm, cpp_paths_list):
    """Вернуть путь к .cpp из compile_commands в той же папке, что и header_path_norm, или None."""
    target_dir = os.path.dirname(header_path_norm)
    for p in cpp_paths_list:
        if target_dir == os.path.dirname(_path_norm(p)):
            return p
    return None


def fill_nodes_from_clang(conn, cur, log=None, config=None):
    """
    Заполняет cpp_type_nodes и cpp_parent_child по Clang AST.
    config — словарь из GUI (COMPILE_COMMANDS и т.д.); если не передан — из dbFolder.
    log: опционально функция(str) для вывода.
    Возвращает (success: bool, message: str).
    """
    def out(msg):
        if log:
            log(msg)
        else:
            print(msg)

    try:
        from clang_ast_runner import parse_file_with_clang, parse_header_using_cpp_command
        import clang.cindex as clang
    except ImportError as e:
        return (False, "Clang/libclang недоступен: {}".format(e))

    compile_commands_path = get_compile_commands_path(config)
    if not compile_commands_path:
        return (False, "COMPILE_COMMANDS не задан (укажите в настройках путь к compile_commands.json)")
    build_dir = get_build_dir(compile_commands_path)

    cpp_paths_list = get_source_files_from_compile_commands(compile_commands_path)
    cpp_paths_set = {_path_norm(p) for p in cpp_paths_list}
    norm_to_original = {_path_norm(p): p for p in cpp_paths_list}
    header_to_cpp = _header_to_cpp_map(cur)

    cur.execute("SELECT id, path FROM cpp_files ORDER BY id ASC")
    rows = cur.fetchall()
    if not rows:
        return (False, "Нет записей в cpp_files")

    filled = 0
    for (file_id, path) in rows:
        path_abs = _path_norm(path)
        if not os.path.isfile(path_abs):
            continue
        tu = None
        if path_abs in cpp_paths_set:
            tu = parse_file_with_clang(path_abs, build_dir, None, log_func=out)
        else:
            ref_cpp_norm = header_to_cpp.get(path_abs)
            ref_cpp = (norm_to_original.get(ref_cpp_norm) or ref_cpp_norm) if ref_cpp_norm else None
            if not ref_cpp:
                ref_cpp = _same_dir_cpp(path_abs, cpp_paths_list)
            if ref_cpp:
                tu = parse_header_using_cpp_command(path_abs, build_dir, ref_cpp, log_func=out)
        if tu is None:
            out("ОШИБКА: не удалось разобрать файл с помощью Clang ({}). Файл пропущен.".format(os.path.basename(path_abs)))
            continue
        tree = build_tree_from_clang(tu, path_abs, clang)
        if not tree.get("body"):
            out("ОШИБКА: пустой AST для файла {}.".format(os.path.basename(path_abs)))
            if tu.diagnostics:
                out("--- Диагностика Clang для файла: {} ---".format(path_abs))
                for diag in tu.diagnostics:
                    if getattr(diag, "severity", 0) >= 4:
                        out("  ОШИБКА: {}".format(getattr(diag, "spelling", "")))
                        if getattr(diag, "location", None) and getattr(diag.location, "file", None):
                            out("  В файле: {}, строка {}".format(diag.location.file.name, getattr(diag.location, "line", 0)))
                out("---")
            out("Файл пропущен.")
            continue
        find_nodes_cpp.type_id = 1
        find_nodes_cpp.parent_id = 1
        find_nodes_cpp.get_node_type(file_id, tree, cur, find_nodes_cpp.parent_id)
        conn.commit()
        filled += 1
    out("Узлы построены для {} файлов.".format(filled))
    return (True, "Узлы по Clang: {} файлов".format(filled))


def fill_nodes_from_ccc(conn, cur, log=None, config=None):
    """
    Заполняет cpp_type_nodes и cpp_parent_child из уже построенных таблиц
    ccc_definition_function, ccc_use_function_list, ccc_file_list (после основного анализа).
    config — для единообразия API (подключение уже к нужной БД через conn).
    log: опционально функция(str).
    Возвращает (success: bool, message: str).
    """
    def out(msg):
        if log:
            log(msg)
        else:
            print(msg)

    cur.execute("SELECT id_file, path FROM ccc_file_list")
    ccc_files = cur.fetchall()
    cur.execute("SELECT id, path FROM cpp_files ORDER BY id ASC")
    cpp_files = cur.fetchall()
    if not cpp_files:
        return (False, "Нет записей в cpp_files")
    path_to_cpp_id = {_path_norm(p): fid for (fid, p) in cpp_files}
    ccc_id_to_path = {fid: p for (fid, p) in ccc_files}
    ccc_path_to_id = {_path_norm(p): fid for (fid, p) in ccc_files}

    cur.execute("SELECT COUNT(*) FROM ccc_definition_function")
    if cur.fetchone()[0] == 0:
        return (False, "Таблица ccc_definition_function пуста — сначала выполните анализ (CLANG/CLANG_AST)")

    cur.execute("""
        SELECT idfunc, file_id, name, start_line, end_line
        FROM ccc_definition_function
        ORDER BY file_id, start_line
    """)
    defs = cur.fetchall()
    cur.execute("""
        SELECT IDfunc, name, from_, lineID
        FROM ccc_use_function_list
        ORDER BY from_, lineID
    """)
    uses = cur.fetchall()

    # По файлу cpp: список (start_line, end_line, name) определений
    defs_by_ccc_file = {}
    for (idfunc, file_id, name, start_line, end_line) in defs:
        if file_id not in defs_by_ccc_file:
            defs_by_ccc_file[file_id] = []
        defs_by_ccc_file[file_id].append((start_line, end_line, name or "?"))

    # По (from_=ccc_file_id, lineID): вызов name
    uses_by_ccc_file = {}
    for (idfunc, name, from_, line_id) in uses:
        if from_ not in uses_by_ccc_file:
            uses_by_ccc_file[from_] = []
        uses_by_ccc_file[from_].append((line_id, name or "?"))

    # Для каждого cpp_file_id построить дерево и вызвать get_node_type
    filled = 0
    for (cpp_id, path) in cpp_files:
        path_n = _path_norm(path)
        ccc_file_id = ccc_path_to_id.get(path_n)
        if ccc_file_id is None:
            continue
        def_list = defs_by_ccc_file.get(ccc_file_id, [])
        use_list = uses_by_ccc_file.get(ccc_file_id, [])
        use_list.sort(key=lambda x: x[0])
        body = []
        for (start_line, end_line, fn_name) in sorted(def_list, key=lambda x: x[0]):
            calls_in_range = [(line_id, name) for (line_id, name) in use_list if start_line <= line_id <= end_line]
            call_nodes = [{"type": "Call", "func": name} for (_, name) in calls_in_range]
            body.append({
                "type": "FunctionDef",
                "name": fn_name,
                "args": {"type": "arguments", "args": []},
                "body": call_nodes,
            })
        tree = {"type": "Module", "body": body}
        find_nodes_cpp.type_id = 1
        find_nodes_cpp.parent_id = 1
        find_nodes_cpp.get_node_type(cpp_id, tree, cur, find_nodes_cpp.parent_id)
        conn.commit()
        filled += 1
    out("Узлы из ccc_* построены для {} файлов.".format(filled))
    return (True, "Узлы из ccc_*: {} файлов".format(filled))


def can_use_clang():
    """Проверка: задан ли COMPILE_COMMANDS и доступен ли Clang."""
    if not get_compile_commands_path():
        return False
    try:
        from clang_ast_runner import parse_file_with_clang
        import clang.cindex
        return True
    except Exception:
        return False


def can_use_ccc(conn):
    """Проверка: есть ли заполненные таблицы ccc_definition_function (и ccc_file_list)."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ccc_definition_function")
        n = cur.fetchone()[0]
        cur.close()
        return n > 0
    except Exception:
        return False
