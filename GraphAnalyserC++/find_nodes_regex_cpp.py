#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regex-парсер C++ как в MyGraphAnalyser: только высокоуровневые узлы (Module, Import,
Namespace, ClassDef, FunctionDef, Call). Используется в режиме «как старый анализатор»
для получения читаемого полного графа без полного Clang AST.
"""
import os
import re
import numbers

type_id = 0
parent_id = 0

RE_INCLUDE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]")
RE_NAMESPACE = re.compile(r"\bnamespace\s+([A-Za-z_]\w*)\s*\{")
RE_CLASS = re.compile(r"\b(class|struct)\s+([A-Za-z_]\w*)")
RE_FUNCTION = re.compile(r"^(?:[A-Za-z_][\w:<>&*\s]+\s+)?([A-Za-z_]\w*(?:::[A-Za-z_]\w*)?)\s*\(([^;{}]*)\)\s*\{?\s*$")
RE_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
RE_COMMENT_LINE = re.compile(r"//.*$")
RE_COMMENT_BLOCK_OPEN = re.compile(r"/\*")
RE_COMMENT_BLOCK_CLOSE = re.compile(r"\*/")

CONTROL_WORDS = {
    "if", "for", "while", "switch", "return", "sizeof", "catch",
    "static_cast", "dynamic_cast", "reinterpret_cast", "const_cast",
    "throw", "new", "delete",
}


def clean_string(s):
    if isinstance(s, str):
        try:
            s = s.replace("\x00", "")
            s = "".join(c for c in s if ord(c) >= 32 or c in "\t\n\r")
            return s.encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            return "INVALID_STRING"
    return str(s)


def get_node_type(file_id, node, cur, parent_id):
    if isinstance(node, list):
        list_node(file_id, node, cur, parent_id)
    else:
        standart_node(file_id, node, cur, parent_id)


def list_node(file_id, node, cur, parent_id):
    global type_id
    parent_id = type_id
    for idx, value in enumerate(node):
        label = str(idx)
        type_id += 1
        cur.execute(
            "INSERT INTO cpp_parent_child (file_parent_id, parent_id, file_child_id, child_id, field) VALUES (%s, %s, %s, %s, %s)",
            (file_id, parent_id, file_id, type_id, label),
        )
        get_node_type(file_id, value, cur, parent_id)


def standart_node(file_id, node, cur, parent_id):
    global type_id
    if isinstance(node, (str, numbers.Number)):
        clean_node = clean_string(node)
        cur.execute("INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)", (file_id, type_id, clean_node))
    elif node is None:
        cur.execute("INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)", (file_id, type_id, "NoneType"))
    elif isinstance(node, dict):
        cur.execute("INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)", (file_id, type_id, node.get("type", "Unknown")))
        parent_id = type_id
        for field, value in node.items():
            if field == "type":
                continue
            type_id += 1
            cur.execute(
                "INSERT INTO cpp_parent_child (file_parent_id, parent_id, file_child_id, child_id, field) VALUES (%s, %s, %s, %s, %s)",
                (file_id, parent_id, file_id, type_id, field),
            )
            get_node_type(file_id, value, cur, parent_id)
    else:
        cur.execute("INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)", (file_id, type_id, str(node)))


def parse_cpp_file(file_path):
    """Парсит C++ файл по regex (как в MyGraphAnalyser): Module, Import, Namespace, ClassDef, FunctionDef, Call."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return {"type": "Module", "body": []}

    clean_lines = []
    in_block_comment = False
    for line in lines:
        if in_block_comment:
            if RE_COMMENT_BLOCK_CLOSE.search(line):
                in_block_comment = False
            continue
        if RE_COMMENT_BLOCK_OPEN.search(line):
            in_block_comment = True
            line = line.split("/*", 1)[0]
        line = RE_COMMENT_LINE.sub("", line)
        clean_lines.append(line)

    module = {"type": "Module", "body": []}
    for idx, line in enumerate(clean_lines, 1):
        line = line.strip()
        if not line:
            continue
        inc = RE_INCLUDE.match(line)
        if inc:
            include_path = inc.group(1)
            import_node = {"type": "Import", "path": include_path, "names": [os.path.basename(include_path)]}
            module["body"].append(import_node)
            continue
        ns = RE_NAMESPACE.search(line)
        if ns:
            ns_name = ns.group(1)
            namespace_node = {"type": "Namespace", "name": ns_name, "body": []}
            module["body"].append(namespace_node)
            continue
        cl = RE_CLASS.search(line)
        if cl:
            cl_name = cl.group(2)
            class_node = {"type": "ClassDef", "name": cl_name, "body": []}
            module["body"].append(class_node)
            continue
        fn = RE_FUNCTION.match(line)
        if fn:
            fn_name = fn.group(1)
            fn_args = fn.group(2)
            func_node = {
                "type": "FunctionDef",
                "name": fn_name,
                "args": {"type": "arguments", "args": [arg.strip() for arg in fn_args.split(",") if arg.strip()]},
                "body": [],
            }
            module["body"].append(func_node)
            continue
        for call_match in RE_CALL.finditer(line):
            call_name = call_match.group(1)
            if call_name not in CONTROL_WORDS:
                call_node = {"type": "Call", "func": call_name}
                if module["body"] and isinstance(module["body"][-1], dict):
                    if "body" in module["body"][-1]:
                        module["body"][-1]["body"].append(call_node)
                    else:
                        module["body"].append(call_node)
                else:
                    module["body"].append(call_node)
    return module


def find_nodes(con, cur):
    """Заполняет cpp_type_nodes и cpp_parent_child деревом из regex-парсера (как в MyGraphAnalyser)."""
    global type_id, parent_id
    cur.execute("SELECT id, path FROM cpp_files ORDER BY id ASC")
    rows = cur.fetchall()
    for row in rows:
        path = os.path.abspath(row[1])
        file_id = row[0]
        try:
            tree = parse_cpp_file(path)
            type_id = 1
            parent_id = type_id
            get_node_type(file_id, tree, cur, parent_id)
            con.commit()
        except Exception as e:
            print("Error processing {}: {}".format(path, e))
            continue
