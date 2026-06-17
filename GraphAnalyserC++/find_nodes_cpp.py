#!/usr/bin/env python3
import numbers

# Минимальный модуль для маппинга произвольного AST (dict/list)
# в таблицы cpp_type_nodes / cpp_parent_child.
# Regex-парсер C++ здесь намеренно отсутствует — дерево поставляет Clang-пайплайн.

type_id = 0
parent_id = 0


def clean_string(s):
    """Очистка строки от проблемных символов перед сохранением в БД."""
    if isinstance(s, str):
        try:
            s = s.replace("\x00", "")
            s = "".join(ch for ch in s if ord(ch) >= 32 or ch in "\t\n\r")
            return s.encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            return "INVALID_STRING"
    return str(s)


def create_tables(con, cur):
    """Создаёт таблицы для узлов и связей графа C++ AST."""
    cur.execute("DROP TABLE IF EXISTS cpp_type_nodes")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cpp_type_nodes(
            file_id        INT,
            type_id        INT,
            node           TEXT,
            block_id       INT,
            col_offset     INT,
            end_col_offset INT,
            end_lineno     INT,
            lineno         INT
        )
        """
    )
    cur.execute("DROP TABLE IF EXISTS cpp_parent_child")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cpp_parent_child(
            file_parent_id INT,
            parent_id      INT,
            file_child_id  INT,
            child_id       INT,
            field          TEXT
        )
        """
    )
    con.commit()


def get_node_type(file_id, node, cur, parent_id):
    """Рекурсивно записывает узел AST (dict/list/primitive) в БД."""
    global type_id

    if isinstance(node, list):
        list_node(file_id, node, cur, parent_id)
    else:
        standart_node(file_id, node, cur, parent_id)


def list_node(file_id, node, cur, parent_id):
    """Обработка узлов-списков."""
    global type_id
    parent_id = type_id
    for idx, value in enumerate(node):
        label = str(idx)
        type_id += 1
        cur.execute(
            "INSERT INTO cpp_parent_child (file_parent_id, parent_id, file_child_id, child_id, field) "
            "VALUES (%s, %s, %s, %s, %s)",
            (file_id, parent_id, file_id, type_id, label),
        )
        get_node_type(file_id, value, cur, parent_id)


def standart_node(file_id, node, cur, parent_id):
    """Обработка всех узлов, отличных от list."""
    global type_id

    if isinstance(node, (str, numbers.Number)):
        clean = clean_string(node)
        cur.execute(
            "INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)",
            (file_id, type_id, clean),
        )
    elif node is None:
        cur.execute(
            "INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)",
            (file_id, type_id, "NoneType"),
        )
    elif isinstance(node, dict):
        cur.execute(
            "INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)",
            (file_id, type_id, node.get("type", "Unknown")),
        )
        parent_id = type_id
        for field, value in node.items():
            if field == "type":
                continue
            type_id += 1
            cur.execute(
                "INSERT INTO cpp_parent_child (file_parent_id, parent_id, file_child_id, child_id, field) "
                "VALUES (%s, %s, %s, %s, %s)",
                (file_id, parent_id, file_id, type_id, field),
            )
            get_node_type(file_id, value, cur, parent_id)
    else:
        cur.execute(
            "INSERT INTO cpp_type_nodes (file_id, type_id, node) VALUES (%s, %s, %s)",
            (file_id, type_id, str(node)),
        )


def parse_cpp_file(file_path):
    """Заглушка: regex-парсер удалён; возвращает пустой модуль для совместимости с nodes_cpp."""
    return {"type": "Module", "body": []}


def find_nodes(con, cur):
    """Заполняет cpp_type_nodes и cpp_parent_child минимальным деревом (Module без body) по каждому файлу из cpp_files."""
    global type_id, parent_id
    cur.execute("SELECT id, path FROM cpp_files ORDER BY id ASC")
    rows = cur.fetchall()
    for (file_id, _path) in rows:
        type_id = 1
        parent_id = 1
        tree = parse_cpp_file(_path)
        get_node_type(file_id, tree, cur, parent_id)
        con.commit()

