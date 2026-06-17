#!/usr/bin/env python3
from structures import node
import networkx as nx

def create_tables(con, cur):
    """
    ТОЧНАЯ КОПИЯ set_block_id.create_tables() из Python анализатора
    Создает таблицы для идентификации областей видимости
    """
    print('set_block_id_cpp.create_tables is start')

    cur.execute('''DROP TABLE IF EXISTS cpp_blocks''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cpp_blocks
        (file_id INT,
        block_id INT,
        file_node_id INT,
        node_id INT);''')
    cur.execute('''DROP TABLE IF EXISTS cpp_nesting_blocks''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cpp_nesting_blocks
        (file_id_of_parent_block INT,
        parent_block_id INT,
        file_id_of_child_block INT,
        child_block_id INT);''')
    con.commit()


def find_all_body(gr, node, block_id, cur):
    """
    Ищет связь с названием body, заполняет таблицу областей видимости.
    Без вывода в консоль на каждый вызов (иначе при большом графе — часы и захламление лога).
    """
    for n, nbrs in gr.adj[node].items():
        if nbrs == {'body': {}}:
            block_id[n.file_id-1][0] += 1
            cur.execute("UPDATE cpp_type_nodes SET block_id = %s WHERE file_id = %s AND type_id = %s", (block_id[n.file_id-1][0], n.file_id, n.node_id))
            cur.execute("INSERT INTO cpp_blocks (file_id, block_id, file_node_id, node_id) VALUES (%s, %s, %s, %s)", (n.file_id, block_id[n.file_id-1][0], node.file_id, node.node_id))
            for na, nbrsa in gr.adj[n].items():
                find_all_childs(gr, na, block_id, cur)
        find_all_body(gr, n, block_id, cur)


def find_all_childs(gr, node, block_id, cur):
    """
    Присваивает всем детям корневого узла id области видимости.
    Без вывода в консоль на каждый вызов (при ~100k узлах давало часы работы и захламление лога).
    """
    cur.execute("UPDATE cpp_type_nodes SET block_id = %s WHERE file_id = %s AND type_id = %s", (block_id[node.file_id-1][0], node.file_id, node.node_id))
    for n, nbrs in gr.adj[node].items():
        cur.execute("UPDATE cpp_type_nodes SET block_id = %s WHERE file_id = %s AND type_id = %s", (block_id[n.file_id-1][0], n.file_id, n.node_id))
        for na, nbrsa in gr.adj[n].items():
            find_all_childs(gr, na, block_id, cur)


def set_block_id(gr, cur, con, count_files):
    """
    Определение областей видимости. Один проход по графу для поиска Module-узлов (вместо count_files проходов).
    """
    print('set_block_id_cpp.set_block_id is start')

    block_id = []
    cur.execute("SELECT id from cpp_files")
    for row in cur.fetchall():
        block_id.append([0])

    module_nodes = [n for n in gr.nodes() if n.name == 'Module' and n.node_id == 1]
    for mod in module_nodes:
        find_all_body(gr, mod, block_id, cur)

    cur.execute("UPDATE cpp_type_nodes SET block_id = 1 WHERE block_id = 0 OR block_id IS NULL")
    con.commit()
    print('set_block_id_cpp.set_block_id is end')


def nesting_blocks(gr, con, cur):
    """
    Заполняет таблицу вложенности областей видимости.
    Один проход по графу для Import (вместо файлы × граф).
    """
    print('set_block_id_cpp.nesting_blocks is start')
    import os

    b = [0, 0]
    source_t = None
    for n in gr.nodes():
        if n.name == 'Module' and n.node_id == 1:
            source_t = node(n.file_id, n.node_id, n.name, n.block_id)
            b = [n.file_id, n.block_id if n.block_id is not None else 0]
            break
    if source_t is None:
        con.commit()
        return

    G = nx.dfs_tree(gr, source=source_t)
    for n in G.nodes():
        n_bid = n.block_id if n.block_id is not None else 0
        b1 = b[1] if b[1] is not None else 0
        if n.file_id != b[0] and n_bid == b1:
            b = [n.file_id, n_bid]
        if n.file_id == b[0] and n_bid > b1:
            cur.execute("INSERT INTO cpp_nesting_blocks (file_id_of_parent_block, parent_block_id, file_id_of_child_block, child_block_id) VALUES (%s, %s, %s, %s)",
                        (b[0], b[1], n.file_id, n_bid))
            b = [n.file_id, n_bid]
        if n.file_id == b[0] and n_bid < b1:
            b = [n.file_id, n_bid]

    # Импорты: один проход по графу — собираем (file_id, block_id, imp_name) для каждого Import
    import_infos = []
    for n in gr.nodes():
        if n.name != 'Import':
            continue
        for nbr in gr.neighbors(n):
            neighbors = list(gr.neighbors(nbr))
            if not neighbors:
                continue
            first_neighbor = neighbors[0]
            imp_neighbors = list(gr.neighbors(first_neighbor))
            imp = imp_neighbors[0] if imp_neighbors else None
            if imp is None:
                continue
            imp_bid = imp.block_id if getattr(imp, 'block_id', None) is not None else 0
            imp_name = getattr(imp, 'name', '') or ''
            import_infos.append((imp.file_id, imp_bid, imp_name))

    cur.execute("SELECT id, path FROM cpp_files ORDER BY id ASC")
    files = cur.fetchall()
    for (file_id, path) in files:
        file_basename = os.path.basename(path)
        for (imp_fid, imp_bid, imp_name) in import_infos:
            if imp_name and (imp_name in file_basename or file_basename in imp_name):
                cur.execute("INSERT INTO cpp_nesting_blocks (file_id_of_parent_block, parent_block_id, file_id_of_child_block, child_block_id) VALUES (%s, %s, %s, %s)",
                            (imp_fid, imp_bid, file_id, 1))
                break

    con.commit()
    print('set_block_id_cpp.nesting_blocks is end')

