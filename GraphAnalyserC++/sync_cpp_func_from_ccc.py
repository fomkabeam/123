# -*- coding: utf-8 -*-
"""
B1.1 (вариант 2): единый источник связей вызовов при наличии AST в БД.

Если таблица ccc_use_function_list заполнена (контур clang_ast_runner), пересобираем
cpp_func_calls_connections из тех же данных, что и отчёт НДВ, и обновляем рёбра
Call -> FunctionDef в графе NetworkX для PDF/Graphviz.

Несколько строк ccc на одну строку исходника (неоднозначные перегрузки) сопоставляются
одному узлу Call: для каждой строки (файл, lineid, имя) берётся один call_id, на каждый
IDfunc вставляется отдельная запись в cpp_func_calls_connections.

Если ccc пуста, graph_runner оставляет классический find_func_call_connection.
"""

import os


def _path_norm(p):
    if not p:
        return ""
    return os.path.normpath(os.path.abspath(p))


def _ccc_file_to_cpp_file(cur):
    """Соответствие id файла в ccc_file_list -> id в cpp_files по нормализованному пути."""
    try:
        cur.execute("SELECT id_file, path FROM ccc_file_list")
        ccc_rows = cur.fetchall()
        cur.execute("SELECT id, path FROM cpp_files ORDER BY id ASC")
        cpp_rows = cur.fetchall()
    except Exception:
        return {}
    cpp_map = {_path_norm(p): fid for (fid, p) in cpp_rows}
    out = {}
    for ccc_id, path in ccc_rows:
        key = _path_norm(path)
        if key in cpp_map:
            out[ccc_id] = cpp_map[key]
    return out


def _resolve_cpp_func_def_id(cur, cpp_file_id, ccc_idfunc, ccc_file_id, name):
    """Один func_def_id в cpp_func_def для заданного idfunc в ccc."""
    cur.execute(
        """
        SELECT fd.func_def_id
        FROM cpp_func_def fd
        JOIN cpp_type_nodes tn ON tn.file_id = fd.file_id AND tn.type_id = fd.func_name_id
        JOIN ccc_definition_function c
          ON c.idfunc = %s AND c.file_id = %s AND (c.name = tn.node OR c.name IS NOT DISTINCT FROM tn.node)
        WHERE fd.file_id = %s AND tn.node = %s
        """,
        (ccc_idfunc, ccc_file_id, cpp_file_id, name),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    cur.execute(
        """
        SELECT fd.func_def_id
        FROM cpp_func_def fd
        JOIN cpp_type_nodes tn ON tn.file_id = fd.file_id AND tn.type_id = fd.func_name_id
        WHERE fd.file_id = %s AND tn.node = %s
        """,
        (cpp_file_id, name),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    return None


def _remove_call_to_funcdef_edges(gr):
    """Удалить рёбра Call -> FunctionDef (синие в PDF), остальное не трогать."""
    to_remove = []
    for u, v, k in list(gr.edges(keys=True)):
        if getattr(u, "name", None) == "Call" and getattr(v, "name", None) == "FunctionDef":
            to_remove.append((u, v, k))
    for u, v, k in to_remove:
        try:
            gr.remove_edge(u, v, key=k)
        except Exception:
            pass


def _split_by_line(events):
    """events: sorted list of (lineid, idfunc, from_) -> список непустых чанков по одинаковой lineid."""
    chunks = []
    i = 0
    while i < len(events):
        line = events[i][0]
        chunk = []
        while i < len(events) and events[i][0] == line:
            chunk.append(events[i])
            i += 1
        chunks.append(chunk)
    return chunks


def sync_cpp_func_connections_from_ccc(conn, cur, gr, log=None):
    """
    Пересобрать cpp_func_calls_connections и рёбра вызовов в gr из ccc_use_function_list.

    :return: None — таблица ccc пуста или нет сопоставления файлов, нужен find_func_call_connection;
             int — число вставленных строк в cpp_func_calls_connections.
    """
    def out(msg):
        if log:
            try:
                log(msg)
            except Exception:
                pass
        else:
            print(msg)

    try:
        cur.execute("SELECT COUNT(*) FROM ccc_use_function_list")
        n_ccc = cur.fetchone()[0] or 0
    except Exception:
        return None
    if n_ccc == 0:
        return None

    ccc_to_cpp = _ccc_file_to_cpp_file(cur)
    if not ccc_to_cpp:
        out("sync_cpp_func_from_ccc: нет сопоставления ccc_file_list ↔ cpp_files, оставляем legacy-связи.")
        return None

    try:
        cur.execute(
            """
            SELECT id, idfunc, name, from_, usein, lineid
            FROM ccc_use_function_list
            ORDER BY usein, lineid, id
            """
        )
        uses = cur.fetchall()
    except Exception:
        try:
            cur.execute(
                """
                SELECT "ID", "IDfunc", name, from_, "useIn", "lineID"
                FROM ccc_use_function_list
                ORDER BY "useIn", "lineID", "ID"
                """
            )
            uses = cur.fetchall()
        except Exception as e:
            out("sync_cpp_func_from_ccc: чтение ccc_use_function_list: {} — legacy.".format(e))
            return None

    if not uses:
        return None

    from structures import node

    groups = {}
    for _uid, idfunc, name, from_, use_in, line_id in uses:
        callee_name = (name or "").strip()
        cpp_call = ccc_to_cpp.get(use_in)
        if cpp_call is None:
            continue
        key = (cpp_call, callee_name)
        if key not in groups:
            groups[key] = []
        groups[key].append((line_id or 0, idfunc, from_))

    cur.execute("DELETE FROM cpp_func_calls_connections")
    conn.commit()
    _remove_call_to_funcdef_edges(gr)

    inserted = 0
    skipped_groups = 0
    for (cpp_call_file, callee_name), events in groups.items():
        if not callee_name:
            continue
        events = sorted(events, key=lambda t: (t[0], t[1]))
        line_chunks = _split_by_line(events)
        cur.execute(
            """
            SELECT call_id FROM cpp_func_calls fc
            JOIN cpp_type_nodes tn ON tn.file_id = fc.file_id AND tn.type_id = fc.call_name_id
            WHERE fc.file_id = %s AND tn.node = %s
            ORDER BY fc.call_id
            """,
            (cpp_call_file, callee_name),
        )
        call_ids = [r[0] for r in cur.fetchall()]
        if len(line_chunks) != len(call_ids):
            skipped_groups += 1
            out(
                "sync_cpp_func_from_ccc: файл {} имя «{}»: уникальных строк (ccc)={}, узлов Call={} — пропуск.".format(
                    cpp_call_file, callee_name, len(line_chunks), len(call_ids)
                )
            )
            continue
        for chunk, call_id in zip(line_chunks, call_ids):
            for (_line, idfunc, _from_) in chunk:
                cur.execute(
                    "SELECT file_id, name FROM ccc_definition_function WHERE idfunc = %s",
                    (idfunc,),
                )
                def_row = cur.fetchone()
                if not def_row:
                    continue
                ccc_def_file, def_name = def_row[0], (def_row[1] or "").strip()
                cpp_def_file = ccc_to_cpp.get(ccc_def_file)
                if cpp_def_file is None:
                    continue
                func_def_id = _resolve_cpp_func_def_id(
                    cur, cpp_def_file, idfunc, ccc_def_file, def_name or callee_name
                )
                if func_def_id is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO cpp_func_calls_connections (file_id_of_call, call_id, file_id_of_func_def, func_def_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (cpp_call_file, call_id, cpp_def_file, str(func_def_id)),
                )
                inserted += 1
                cur.execute(
                    """
                    SELECT file_id, type_id, node, block_id FROM cpp_type_nodes
                    WHERE file_id = %s AND type_id = %s
                    """,
                    (cpp_call_file, call_id),
                )
                p = cur.fetchone()
                cur.execute(
                    """
                    SELECT file_id, type_id, node, block_id FROM cpp_type_nodes
                    WHERE file_id = %s AND type_id = %s
                    """,
                    (cpp_def_file, func_def_id),
                )
                c = cur.fetchone()
                if p and c:
                    pu = node(p[0], p[1], p[2], p[3])
                    cv = node(c[0], c[1], c[2], c[3])
                    gr.add_edge(pu, cv, "call")

    conn.commit()
    out(
        "sync_cpp_func_from_ccc: связей из ccc_use_function_list: {}, пропущено групп (имя/файл): {}.".format(
            inserted, skipped_groups
        )
    )
    return inserted
