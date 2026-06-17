#!/usr/bin/env python3
"""
Построение графа вызовов C++: дерево AST (cpp_type_nodes, cpp_parent_child) -> NetworkX граф
-> области видимости (block_id) -> связи Call->FunctionDef -> экспорт в PDF (Graphviz).

Структура графа в PDF:
- Узлы: все узлы AST (Module, FunctionDef, Call, Import, Namespace, ClassDef, body, name, func, ...).
- Рёбра: дерево (родитель–потомок) + связи вызовов (Call -> FunctionDef), синие — вызовы, серые — структура.
- Подписи: для FunctionDef/Call подставляется имя функции из дочернего узла (name/func).
"""
import os
import graphviz as gv
import networkx as nx
from structures import node


def _node_display_label(gr, n):
    """Читаемая подпись узла: для FunctionDef/Call — имя из дочернего узла (name/func)."""
    if n.name == "FunctionDef":
        for u, v, key in gr.edges(n, keys=True):
            if u == n and key == "name":
                return v.name if hasattr(v, "name") else "FunctionDef"
        return "FunctionDef"
    if n.name == "Call":
        for u, v, key in gr.edges(n, keys=True):
            if u == n and key == "func":
                return v.name if hasattr(v, "name") else "Call"
        return "Call"
    if n.name == "Module":
        return "Module (file {})".format(n.file_id)
    return n.name

def create_graph(con, cur, graph, count_files):
    """
    ТОЧНАЯ КОПИЯ create_graph.create_graph() из Python анализатора
    Создает дерево каждого файла в формате PDF
    """
    print('create_graph_cpp.create_graph is start')

    max_files = count_files
    print('Processing {} files (full analysis)'.format(max_files))

    for i in range(1, max_files + 1):
        print('Processing file {}/{}...'.format(i, max_files))

        graphattrs = {
            'labelloc': 't',
            'fontcolor': 'black',
            'bgcolor': 'white',
            'margin': '0.02',
            'rankdir': 'LR'
        }

        nodeattrs = {
            'color': 'black',
            'fontcolor': 'black',
            'style': 'filled',
            'fillcolor': 'white',
        }

        edgeattrs = {
            'color': 'red',
            'fontcolor': 'black',
        }

        graph = gv.Digraph(filename='trees/tree_of_' + str(i) + '_file.gv', 
                          graph_attr=graphattrs, node_attr=nodeattrs, edge_attr=edgeattrs)

        # ТОЧНО как в Python: получаем все данные для текущего файла
        cur.execute("""
            SELECT pc.file_parent_id, pc.parent_id, pc.file_child_id, pc.child_id, pc.field,
                   tn1.node as parent_node, tn2.node as child_node
            FROM cpp_parent_child pc
            LEFT JOIN cpp_type_nodes tn1 ON pc.file_parent_id = tn1.file_id AND pc.parent_id = tn1.type_id
            LEFT JOIN cpp_type_nodes tn2 ON pc.file_child_id = tn2.file_id AND pc.child_id = tn2.type_id
            WHERE pc.file_parent_id = %s
            ORDER BY pc.file_parent_id, pc.parent_id, pc.child_id ASC
        """, (i,))
        rows = cur.fetchall()
        
        for row in rows:
            file_parent_id, parent_id, file_child_id, child_id, field, parent_node, child_node = row
            if parent_node and child_node:
                graph.node(str(file_parent_id) + ' ' + str(parent_id), label=str(parent_node))
                graph.node(str(file_child_id) + ' ' + str(child_id), label=str(child_node))
                graph.edge(str(file_parent_id) + ' ' + str(parent_id), 
                          str(file_child_id) + ' ' + str(child_id), label=str(field))
        
        graph.format = "pdf"
        graph.view()


def fill_graph(count_files, cur):
    """
    ТОЧНАЯ КОПИЯ create_graph.fill_graph() из Python анализатора
    Заполняет объект "Граф"
    """
    print('create_graph_cpp.fill_graph is start')

    print('Processing {} files...'.format(count_files))
    
    # ТОЧНО как в Python: получаем все данные одним запросом
    cur.execute("""
        SELECT pc.file_parent_id, pc.parent_id, pc.file_child_id, pc.child_id, pc.field,
               tn1.node as parent_node, tn1.block_id as parent_block,
               tn2.node as child_node, tn2.block_id as child_block
        FROM cpp_parent_child pc
        LEFT JOIN cpp_type_nodes tn1 ON pc.file_parent_id = tn1.file_id AND pc.parent_id = tn1.type_id
        LEFT JOIN cpp_type_nodes tn2 ON pc.file_child_id = tn2.file_id AND pc.child_id = tn2.type_id
        ORDER BY pc.file_parent_id, pc.parent_id, pc.child_id ASC
    """)
    rows = cur.fetchall()
    
    print('Found {} relationships'.format(len(rows)))
    
    G = nx.MultiDiGraph()
    
    # ТОЧНО как в Python: обрабатываем все строки
    for i, row in enumerate(rows):
        if i % 1000 == 0:
            print('Processing relationship {}/{}...'.format(i + 1, len(rows)))
            
        file_parent_id, parent_id, file_child_id, child_id, field, parent_node, parent_block, child_node, child_block = row
        
        # Создаем узлы ТОЧНО как в Python
        if parent_block is not None:
            parent_node_obj = node(file_parent_id, parent_id, parent_node, parent_block)
        else:
            parent_node_obj = node(file_parent_id, parent_id, parent_node)
            
        if child_block is not None:
            child_node_obj = node(file_child_id, child_id, child_node, child_block)
        else:
            child_node_obj = node(file_child_id, child_id, child_node)
        
        # Добавляем узлы в граф
        G.add_node(parent_node_obj)
        G.add_node(child_node_obj)
        
        # Добавляем связь
        G.add_edge(parent_node_obj, child_node_obj, field)
    
    print('Graph construction completed')
    return G


def find_module_by_import(gr, cur, con):
    """
    АДАПТАЦИЯ find_module_by_import() из Python анализатора для C++
    Ищет id файлов для #include, объединяет деревья файлов
    """
    print('create_graph_cpp.find_module_by_import is start')

    delet = []
    cur.execute("SELECT id, path from cpp_files ORDER BY id ASC")
    file = cur.fetchall()
    
    for row in file:
        for n, nbrs in gr.adj.items():
            if n.name == 'Import':
                for nbr, eattr in nbrs.items():
                    # Получаем имя включаемого файла
                    neighbors = list(gr.neighbors(nbr))
                    if len(neighbors) == 0:
                        continue
                    
                    first_neighbor = neighbors[0]
                    imp_neighbors = list(gr.neighbors(first_neighbor))
                    if len(imp_neighbors) == 0:
                        imp = node(0, 0, 'None', 0)
                    else:
                        imp = imp_neighbors[0]
                    
                    # Проверяем соответствие имени файла
                    file_basename = os.path.basename(row[1])
                    if imp.name in file_basename or file_basename in imp.name:
                        child_neighbors = list(gr.neighbors(node(row[0], 1, 'Module')))
                        if len(child_neighbors) > 1:
                            child_id = child_neighbors[1].node_id
                            
                            # Добавляем связи
                            cur.execute("INSERT INTO cpp_parent_child (file_parent_id, parent_id, file_child_id, child_id, field) VALUES (%s, %s, %s, %s, %s)", 
                                       (imp.file_id, imp.node_id, row[0], 2, 'body'))
                            cur.execute("INSERT INTO cpp_parent_child (file_parent_id, parent_id, file_child_id, child_id, field) VALUES (%s, %s, %s, %s, %s)", 
                                       (imp.file_id, imp.node_id, row[0], child_id, 'type_ignores'))
                            
                            gr.add_edge(node(imp.file_id, imp.node_id, imp.name), node(row[0], 2, 'list'), 'body')
                            gr.add_edge(node(imp.file_id, imp.node_id, imp.name), node(row[0], child_id, 'list'), 'type_ignores')
                            delet.append([row[0], child_id])
    
    # Удаляем дубликаты
    index = 0
    while index < len(delet):
        if delet[index] in delet[:index]:
            del delet[index]
        else:
            index += 1
    
    # Удаляем лишние связи
    for i in delet:
        try:
            gr.remove_edge(node(i[0], 1, 'Module'), node(i[0], 2, 'list'))
            gr.remove_edge(node(i[0], 1, 'Module'), node(i[0], i[1], 'list'))
            gr.remove_node(node(i[0], 1, 'Module'))
            cur.execute("DELETE FROM cpp_parent_child WHERE file_parent_id = %s and parent_id = %s and file_child_id = %s and child_id = %s", 
                       (i[0], 1, i[0], 2))
            cur.execute("DELETE FROM cpp_parent_child WHERE file_parent_id = %s and parent_id = %s and file_child_id = %s and child_id = %s", 
                       (i[0], 1, i[0], i[1]))
            cur.execute("DELETE FROM cpp_type_nodes WHERE file_id = %s and type_id = %s", (i[0], 1))
        except:
            pass
    
    con.commit()
    return gr


def _safe_label(s):
    """Короткая подпись для Graphviz (без переносов и кавычек в кавычках)."""
    if s is None:
        return "?"
    s = str(s).replace("\\", "\\\\").replace('"', "'").replace("\n", " ").strip()
    return s[:64] + "..." if len(s) > 64 else s


def create_full_graph(gr, graph, output_directory=None, view=True, out=None,
                      save_full_gv=True, render_full_pdf=False, build_calls_pdf=True,
                      exclude_std_lib=False, hide_utility_threshold=0):
    """
    Создаёт граф в едином читаемом виде: LR, margin 0.02, белый фон, красные/синие рёбра.
    Подписи узлов — читаемые (для FunctionDef/Call берётся имя из AST). Данные из Clang дают точный анализ.
    save_full_gv: сохранить полный граф в graph_full_original.gv.
    render_full_pdf: рендерить полный граф в PDF.
    build_calls_pdf: построить граф только вызовов (graph_calls.gv / graph_calls.pdf).
    """
    def log(msg):
        if out:
            out(msg)
        print(msg)
    log('create_graph_cpp.create_full_graph is start')
    num_nodes = gr.number_of_nodes()
    num_edges = gr.number_of_edges()
    log("Узлов в графе: {}, рёбер: {}.".format(num_nodes, num_edges))

    out_dir = output_directory if output_directory else 'graphs'
    full_gv_base = os.path.join(out_dir, 'graph_full_original')
    full_gv_path = full_gv_base + '.gv'

    # Единый стиль: LR, margin 0.02, белый фон, читаемые подписи (из AST при Clang), red/blue рёбра
    graphattrs = {
        'labelloc': 't',
        'fontcolor': 'black',
        'bgcolor': 'white',
        'margin': '0.02',
        'rankdir': 'LR',
    }
    nodeattrs = {'color': 'black', 'fontcolor': 'black', 'style': 'filled', 'fillcolor': 'white'}
    edgeattrs = {'color': 'red', 'fontcolor': 'black'}
    g = gv.Digraph(filename=full_gv_base, graph_attr=graphattrs, node_attr=nodeattrs, edge_attr=edgeattrs)
    for n in list(gr.nodes):
        label = _safe_label(_node_display_label(gr, n))
        g.node("{} {}".format(n.file_id, n.node_id), label=label)
    for j in list(gr.edges(keys=True)):
        u, v, key = j[0], j[1], j[2]
        if u.name == 'Call' and v.name == 'FunctionDef':
            g.attr('edge', color='blue')
            g.edge("{} {}".format(u.file_id, u.node_id), "{} {}".format(v.file_id, v.node_id), label=_safe_label(str(key)))
        else:
            g.attr('edge', color='red')
            g.edge("{} {}".format(u.file_id, u.node_id), "{} {}".format(v.file_id, v.node_id), label=_safe_label(str(key)))

    g.format = "pdf"
    if save_full_gv:
        try:
            with open(full_gv_path, "w", encoding="utf-8") as f:
                f.write(g.source)
            log("Полный исходный граф сохранён: {} (все узлы и рёбра).".format(full_gv_path))
        except Exception as e:
            log("Ошибка записи {}: {}.".format(full_gv_path, e))
    if render_full_pdf:
        log("Рендер полного графа в PDF (dot)... при большом графе может занять часы.")
        if view:
            g.view()
        else:
            g.render(cleanup=True)
        log("Полный граф сохранён в PDF.")
    if build_calls_pdf:
        log("Построение графа только вызовов (graph_calls.gv / graph_calls.pdf)...")
        _create_call_graph_only(
            gr, out_dir, view,
            exclude_std_lib=exclude_std_lib,
            hide_utility_threshold=hide_utility_threshold,
        )
    return g


# Префиксы имён для исключения из графа вызовов (стандартные/внешние библиотеки)
CALL_GRAPH_EXCLUDE_PREFIXES = ("std::", "boost::", "__gnu_cxx::", "Qt::", "QMetaObject::")


def _create_call_graph_only(gr, output_directory, view=False, exclude_std_lib=False, hide_utility_threshold=0):
    """
    Строит граф только вызовов (FunctionDef и Call): rankdir LR, белый фон, синие рёбра.
    exclude_std_lib: не включать рёбра вызовов в std::, boost::, Qt:: и т.д.
    hide_utility_threshold: скрыть функции с числом входящих вызовов > этого порога (0 = не скрывать).
    """
    call_edges_raw = [(u, v, k) for u, v, k in gr.edges(keys=True) if u.name == "Call" and v.name == "FunctionDef"]
    if not call_edges_raw:
        return

    # Фильтр: исключить вызовы в стандартные/внешние библиотеки
    if exclude_std_lib:
        def _callee_name(v):
            return (_node_display_label(gr, v) or "").strip()
        call_edges_raw = [(u, v, k) for u, v, k in call_edges_raw
                          if not any(_callee_name(v).startswith(prefix) for prefix in CALL_GRAPH_EXCLUDE_PREFIXES)]
    if not call_edges_raw:
        return

    # Фильтр: скрыть «служебные» функции (много входящих вызовов)
    if hide_utility_threshold > 0:
        from collections import Counter
        callee_counts = Counter(v for u, v, k in call_edges_raw)
        utility_defs = {v for v, cnt in callee_counts.items() if cnt > hide_utility_threshold}
        call_edges_raw = [(u, v, k) for u, v, k in call_edges_raw if v not in utility_defs]
    if not call_edges_raw:
        return

    call_nodes_set = set()
    for u, v, k in call_edges_raw:
        call_nodes_set.add(u)
        call_nodes_set.add(v)
    call_nodes = list(call_nodes_set)

    # Тот же стиль, что и полный граф: LR, белый фон, читаемые подписи
    graphattrs = {
        "labelloc": "t",
        "fontcolor": "black",
        "bgcolor": "white",
        "margin": "0.02",
        "rankdir": "LR",
        "nodesep": "0.4",
        "ranksep": "0.5",
    }
    nodeattrs = {"color": "black", "fontcolor": "black", "style": "filled", "fillcolor": "white"}
    g = gv.Digraph(
        filename=os.path.join(output_directory, "graph_calls.gv"),
        graph_attr=graphattrs,
        node_attr=nodeattrs,
    )
    for n in call_nodes:
        nid = "{} {}".format(n.file_id, n.node_id)
        label = _safe_label(_node_display_label(gr, n))
        g.node(nid, label=label)
    for u, v, k in call_edges_raw:
        uid = "{} {}".format(u.file_id, u.node_id)
        vid = "{} {}".format(v.file_id, v.node_id)
        g.edge(uid, vid, label=_safe_label(k), color="blue", fontcolor="black")
    g.format = "pdf"
    if view:
        g.view()
    else:
        g.render(cleanup=True)

