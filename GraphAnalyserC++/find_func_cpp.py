#!/usr/bin/env python3
from structures import node

def create_tables(con, cur):
    """
    ТОЧНАЯ КОПИЯ find_func.create_tables() из Python анализатора
    Создает таблицы для объявлений функций и вызовов функций
    """
    print('find_func_cpp.create_tables is start')

    cur.execute('''DROP TABLE IF EXISTS cpp_func_def''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cpp_func_def
        (file_id INT,
        func_def_id INT,
        func_name_id INT,
        block_id INT);''')
    cur.execute('''DROP TABLE IF EXISTS cpp_func_calls''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cpp_func_calls
        (file_id INT,
        call_id INT,
        call_name_id INT,
        attr_name TEXT,
        block_id INT);''')
    cur.execute('''DROP TABLE IF EXISTS cpp_func_calls_connections''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cpp_func_calls_connections
        (file_id_of_call INT,
        call_id INT,
        file_id_of_func_def INT,
        func_def_id TEXT);''')
    con.commit()


def find_functions(gr, cur, con):
    """
    ТОЧНАЯ КОПИЯ find_func.find_functions() из Python анализатора
    Ищет все объявления функций в указанном графе
    """
    print('find_func_cpp.find_functions is start')

    for n, nbrs in gr.adj.items():
        if n.name == 'FunctionDef':
            for nbr, eattr in nbrs.items():
                if eattr == {'name': {}}:
                    cur.execute("INSERT INTO cpp_func_def (file_id, func_def_id, func_name_id, block_id) VALUES (%s, %s, %s, %s)", 
                               (n.file_id, n.node_id, nbr[1], n.block_id))
    con.commit()


def find_functions_calls(gr, cur, con):
    """
    Ищет все вызовы функций в графе. Учитывает и AST (Name/Attribute), и regex-дерево (Call → лист с именем функции).
    """
    print('find_func_cpp.find_functions_calls is start')

    for n, nbrs in gr.adj.items():
        if n.name != 'Call':
            continue
        for nbr, eattr in nbrs.items():
            nbr_neighbors = list(gr.neighbors(nbr))
            if nbr.name == 'Attribute':
                if len(nbr_neighbors) < 2:
                    continue
                if nbr_neighbors[0].name == 'Name':
                    name_neighbors = list(gr.neighbors(nbr_neighbors[0]))
                    attr_name = name_neighbors[0].name if name_neighbors else None
                    cur.execute("INSERT INTO cpp_func_calls (file_id, call_id, call_name_id, attr_name, block_id) VALUES (%s, %s, %s, %s, %s)",
                               (n.file_id, n.node_id, nbr_neighbors[1].node_id, attr_name, n.block_id))
                else:
                    cur.execute("INSERT INTO cpp_func_calls (file_id, call_id, call_name_id, block_id) VALUES (%s, %s, %s, %s)",
                               (n.file_id, n.node_id, nbr_neighbors[1].node_id, n.block_id))
            elif nbr.name == 'Name':
                if nbr_neighbors:
                    call_name_id = nbr_neighbors[0].node_id
                else:
                    call_name_id = nbr.node_id
                cur.execute("INSERT INTO cpp_func_calls (file_id, call_id, call_name_id, block_id) VALUES (%s, %s, %s, %s)",
                           (n.file_id, n.node_id, call_name_id, n.block_id))
            else:
                if not nbr_neighbors:
                    cur.execute("INSERT INTO cpp_func_calls (file_id, call_id, call_name_id, block_id) VALUES (%s, %s, %s, %s)",
                               (n.file_id, n.node_id, nbr.node_id, n.block_id))
    con.commit()


def find_func_call_connection(gr, cur, con):
    """
    ТОЧНАЯ КОПИЯ find_func.find_func_call_connection() из Python анализатора
    Ищет связи FunctionDef и Call
    """
    print('find_func_cpp.find_func_call_connection is start')

    cur.execute("SELECT file_id, func_def_id, func_name_id, block_id from cpp_func_def ")
    func_def = cur.fetchall()
    cur.execute("SELECT file_id, call_id, call_name_id, attr_name, block_id from cpp_func_calls ")
    func_call = cur.fetchall()
    cur.execute("SELECT id, path from cpp_files")
    file = cur.fetchall()
    f = []
    end_block = []
    
    for n, nbrs in gr.adj.items():
        if n.name == 'Module' and n.node_id == 1:
            end_block.append([(n.file_id, n.block_id)])
    
    # Адаптация для C++ файлов
    import os
    for row in file:
        basename = os.path.basename(row[1])
        # Убираем расширение для C++ файлов (.cpp, .h, .hpp и т.д.)
        if '.' in basename:
            name_without_ext = basename[:basename.rfind('.')]
        else:
            name_without_ext = basename
        f.append([row[0], name_without_ext])
    
    for n, nbrs in gr.adj.items():
        if n.name == 'Import':
            for nbr, eattr in nbrs.items():
                neighbors = list(gr.neighbors(nbr))
                if len(neighbors) == 0:
                    continue
                
                first_neighbor_neighbors = list(gr.neighbors(neighbors[0]))
                if len(first_neighbor_neighbors) == 0:
                    imp = node(0, 0, 'None', 0)
                else:
                    imp = first_neighbor_neighbors

                    for i in f:
                        if imp[0].name == i[1]:
                            if len(imp) > 1 and imp[1].name != 'NoneType':
                                i.append(imp[1].name)
                            else:
                                i.append(imp[0].name)
                            break

        elif n.name == 'ImportFrom':
            neighbors = list(gr.neighbors(n))
            if len(neighbors) == 0:
                imp = node(0, 0, 'None', 0)
            else:
                imp = neighbors[0]
                for i in f:
                    if imp.name == i[1]:
                        for nbr, eattr in nbrs.items():
                            if eattr == {'names': {}}:
                                nbr_neighbors = list(gr.neighbors(nbr))
                                if len(nbr_neighbors) == 0:
                                    continue
                                
                                first_nbr_neighbor_neighbors = list(gr.neighbors(nbr_neighbors[0]))
                                if len(first_nbr_neighbor_neighbors) < 2:
                                    imp = node(0, 0, 'None', 0)
                                else:
                                    imp = first_nbr_neighbor_neighbors[1]
                                    i.append(imp.name)
                        break
    
    for row in func_def:
        for rowc in func_call:
            cur.execute("SELECT node, block_id from cpp_type_nodes where file_id = {0} and type_id = {1}".format(row[0], row[2]))
            func_name_result = cur.fetchall()
            if len(func_name_result) == 0:
                continue
            func_name = func_name_result[0]
            
            cur.execute("SELECT node, block_id from cpp_type_nodes where file_id = {0} and type_id = {1}".format(rowc[0], rowc[2]))
            call_name_result = cur.fetchall()
            if len(call_name_result) == 0:
                continue
            call_name = call_name_result[0]
            
            cur.execute("SELECT file_id_of_parent_block, parent_block_id FROM cpp_nesting_blocks WHERE file_id_of_child_block = {0} and child_block_id = {1}".format(rowc[0], call_name[1]))
            block_id_of_func_call = cur.fetchall()
            
            if len(block_id_of_func_call) != 0:
                if call_name[0] == func_name[0] and row[0] == rowc[0] and (row[3] == block_id_of_func_call[0][1] or row[3] == rowc[4]):
                    cur.execute("INSERT INTO cpp_func_calls_connections (file_id_of_call, call_id, file_id_of_func_def, func_def_id) VALUES (%s, %s, %s, %s)", 
                               (rowc[0], rowc[1], row[0], row[1]))
                    cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(rowc[0], rowc[1]))
                    parent_node = cur.fetchall()[0]
                    cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(row[0], row[1]))
                    child_node = cur.fetchall()[0]
                    gr.add_edge(node(parent_node[0], parent_node[1], parent_node[2], parent_node[3]), 
                               node(child_node[0], child_node[1], child_node[2], child_node[3]))
                else:
                    while (row[3] != block_id_of_func_call[0][1] or block_id_of_func_call[0][1] != 1) and block_id_of_func_call not in end_block:
                        cur.execute("SELECT file_id_of_parent_block, parent_block_id FROM cpp_nesting_blocks WHERE file_id_of_child_block = {0} and child_block_id = {1}".format(rowc[0], block_id_of_func_call[0][1]))
                        block_id_of_func_call = cur.fetchall()
                        if len(block_id_of_func_call) != 0:
                            if call_name[0] == func_name[0] and row[0] == rowc[0] and row[3] == block_id_of_func_call[0][1]:
                                cur.execute("INSERT INTO cpp_func_calls_connections (file_id_of_call, call_id, file_id_of_func_def, func_def_id) VALUES (%s, %s, %s, %s)", 
                                           (rowc[0], rowc[1], row[0], row[1]))
                                cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(rowc[0], rowc[1]))
                                parent_node = cur.fetchall()[0]
                                cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(row[0], row[1]))
                                child_node = cur.fetchall()[0]
                                gr.add_edge(node(parent_node[0], parent_node[1], parent_node[2], parent_node[3]), 
                                           node(child_node[0], child_node[1], child_node[2], child_node[3]))
                        else:
                            break
            
            if len(f[row[0]-1]) > 2:
                if call_name[0] == func_name[0] and (rowc[3] == f[row[0]-1][1] or rowc[3] == f[row[0]-1][2]):
                    cur.execute("INSERT INTO cpp_func_calls_connections (file_id_of_call, call_id, file_id_of_func_def, func_def_id) VALUES (%s, %s, %s, %s)", 
                               (rowc[0], rowc[1], row[0], row[1]))
                    cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(rowc[0], rowc[1]))
                    parent_node = cur.fetchall()[0]
                    cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(row[0], row[1]))
                    child_node = cur.fetchall()[0]
                    gr.add_edge(node(parent_node[0], parent_node[1], parent_node[2], parent_node[3]), 
                               node(child_node[0], child_node[1], child_node[2], child_node[3]))
            elif call_name[0] == func_name[0] and rowc[3] == f[row[0]-1][1]:
                cur.execute("INSERT INTO cpp_func_calls_connections (file_id_of_call, call_id, file_id_of_func_def, func_def_id) VALUES (%s, %s, %s, %s)", 
                           (rowc[0], rowc[1], row[0], row[1]))
                cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(rowc[0], rowc[1]))
                parent_node = cur.fetchall()[0]
                cur.execute("SELECT file_id, type_id, node, block_id FROM cpp_type_nodes WHERE file_id = {0} and type_id = {1}".format(row[0], row[1]))
                child_node = cur.fetchall()[0]
                gr.add_edge(node(parent_node[0], parent_node[1], parent_node[2], parent_node[3]), 
                           node(child_node[0], child_node[1], child_node[2], child_node[3]))
    
    con.commit()
    return gr

