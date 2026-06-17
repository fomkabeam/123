# -*- coding: utf-8 -*-
"""
Запуск пайплайна построения графа вызовов C++ для GUI (окно «Построение графа»).
Использует find_files_cpp -> заполнение узлов (Clang / ccc / минимальный fallback) ->
set_block_id -> find_func_cpp -> create_full_graph -> сохранение PDF.
"""

import os
import sys

# Конфиг и БД — из того же LOG_PATH.txt, что и _Starter
try:
    from _Starter import folder
except Exception:
    from dbFolder import folder

import psycopg2


def _log(msg, callback=None):
    if callback:
        try:
            callback(msg)
        except Exception:
            pass
    else:
        print(msg)


def run_graph_pipeline(project_path, output_dir=None, progress_callback=None, stop_event=None, config=None,
                      ask_before_full_graph=None, filter_std_lib=False, filter_utility_threshold=0,
                      use_regex_nodes=False):
    """
    Строит граф вызовов по каталогу project_path и сохраняет в output_dir.

    :param ask_before_full_graph: при большом графе вызывается ask_before_full_graph(num_nodes, num_edges, out_dir);
          должен вернуть dict: save_full_gv, render_full_pdf, build_calls_pdf, exclude_std_lib, hide_utility_threshold.
    :param filter_std_lib: исключить вызовы std::, boost::, Qt:: в графе вызовов (если диалог не показывается).
    :param filter_utility_threshold: скрыть функции с входящих вызовов > этого порога (0 = не скрывать).
    :param use_regex_nodes: True — узлы строить упрощённым regex-парсером (меньше узлов, без Clang). False — узлы из Clang/ccc (точный анализ).
    :return: (success: bool, message: str)
    """
    def out(msg):
        _log(msg, progress_callback)

    def stopped():
        return stop_event is not None and stop_event.is_set()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    graph_dir = os.path.join(base_dir, "GraphAnalyserC++")
    if graph_dir not in sys.path:
        sys.path.insert(0, graph_dir)

    # Подключение к БД: приоритет у переданного config (из GUI), иначе LOG_PATH.txt
    db_config = config if config else folder
    out("Конфигурация:")
    out("  БД: {}@{}:{}/{}".format(
        db_config.get("DB_USER", ""),
        db_config.get("DB_HOST", ""),
        db_config.get("DB_PORT", ""),
        db_config.get("DB_NAME", ""),
    ))
    cc = (db_config.get("COMPILE_COMMANDS") or "").strip()
    if cc:
        out("  COMPILE_COMMANDS: {}".format(cc))
    else:
        out("  COMPILE_COMMANDS: не задан (для Clang-узлов укажите в настройках)")

    try:
        conn = psycopg2.connect(
            database=db_config.get("DB_NAME", folder.get("DB_NAME")),
            user=db_config.get("DB_USER", folder.get("DB_USER")),
            password=db_config.get("DB_PASS", folder.get("DB_PASS")),
            host=db_config.get("DB_HOST", folder.get("DB_HOST")),
            port=db_config.get("DB_PORT", folder.get("DB_PORT")),
        )
        cur = conn.cursor()
        conn.rollback()
        out("Подключение к БД установлено.")
    except Exception as e:
        return (False, "Ошибка подключения к БД: {}".format(e))

    try:
        # 1) Таблица cpp_files по выбранному каталогу
        out("Сканирование файлов: {} ...".format(project_path))
        import find_files_cpp
        find_files_cpp.create_tables(conn, cur)
        # Прогресс каждые 500 файлов, чтобы не зависало без вывода при больших проектах
        def progress_cb(n, path):
            if n and n % 500 == 0:
                out("  найдено файлов: {} ...".format(n))
        count_files = find_files_cpp.find_file(
            os.listdir(project_path), project_path, conn, cur,
            progress_callback=progress_cb,
        )
        if count_files == 0:
            return (False, "В каталоге не найдено C++ файлов (.cpp, .cc, .cxx, .c, .h, .hpp, .hxx).")
        out("Найдено файлов: {}.".format(count_files))
        if stopped():
            return (False, "Остановлено пользователем.")

        # 2) Узлы: при use_regex_nodes — regex-парсер (как MyGraphAnalyser); иначе ccc -> Clang -> ccc -> fallback
        import find_nodes_cpp
        find_nodes_cpp.create_tables(conn, cur)

        nodes_ok = False
        if use_regex_nodes:
            out("Упрощённый анализ (regex): заполнение узлов по regex (без Clang)...")
            try:
                import find_nodes_regex_cpp
                find_nodes_regex_cpp.find_nodes(conn, cur)
                nodes_ok = True
                out("Узлы заполнены из regex-парсера.")
            except Exception as e:
                out("Ошибка regex-парсера: {}.".format(e))
                try:
                    conn.rollback()
                except Exception:
                    pass
                return (False, "Не удалось создать узлы (regex): {}".format(e))

        if not nodes_ok:
            use_ccc_first = False
            try:
                cur.execute("SELECT COUNT(*) FROM ccc_definition_function")
                use_ccc_first = (cur.fetchone()[0] or 0) > 0
            except Exception:
                pass
            if use_ccc_first:
                out("Найдены данные анализа (ccc_definition_function). Используем узлы из ccc_* (без повторного парсинга Clang).")
                try:
                    import find_nodes_clang_cpp
                    ok, msg = find_nodes_clang_cpp.fill_nodes_from_ccc(conn, cur, out, config=config)
                    if ok:
                        nodes_ok = True
                        out(msg)
                except Exception as e:
                    out("Узлы из ccc недоступны: {}.".format(e))
                    try:
                        conn.rollback()
                    except Exception:
                        pass

            if not nodes_ok and not stopped():
                try:
                    import find_nodes_clang_cpp
                    ok, msg = find_nodes_clang_cpp.fill_nodes_from_clang(conn, cur, out, config=config)
                    if ok:
                        nodes_ok = True
                        out(msg)
                except Exception as e:
                    out("Clang-узлы недоступны: {}.".format(e))
                    try:
                        conn.rollback()
                    except Exception:
                        pass

            if not nodes_ok and not stopped():
                try:
                    import find_nodes_clang_cpp
                    ok, msg = find_nodes_clang_cpp.fill_nodes_from_ccc(conn, cur, out, config=config)
                    if ok:
                        nodes_ok = True
                        out(msg)
                except Exception as e:
                    out("Узлы из ccc недоступны: {}.".format(e))
                    try:
                        conn.rollback()
                    except Exception:
                        pass

            if not nodes_ok:
                out("Заполнение минимальными узлами (Module) по каждому файлу...")
                try:
                    find_nodes_cpp.find_nodes(conn, cur)
                    nodes_ok = True
                except Exception as e:
                    out("Ошибка минимальных узлов: {}.".format(e))
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    return (False, "Не удалось создать узлы: {}".format(e))
        if stopped():
            return (False, "Остановлено пользователем.")

        # 3) Граф в памяти, block_id, функции, вызовы, PDF
        out("Построение графа...")
        import create_graph_cpp
        import set_block_id_cpp
        import find_func_cpp

        gr = create_graph_cpp.fill_graph(count_files, cur)
        out("set_block_id_cpp: создание таблиц...")
        set_block_id_cpp.create_tables(conn, cur)
        out("set_block_id_cpp: определение block_id (может занять несколько минут)...")
        set_block_id_cpp.set_block_id(gr, cur, conn, count_files)
        if stopped():
            return (False, "Остановлено пользователем.")
        out("set_block_id_cpp: вложенность блоков...")
        set_block_id_cpp.nesting_blocks(gr, conn, cur)

        out("find_func_cpp: создание таблиц и поиск функций...")
        find_func_cpp.create_tables(conn, cur)
        find_func_cpp.find_functions(gr, cur, conn)
        out("find_func_cpp: поиск вызовов функций...")
        find_func_cpp.find_functions_calls(gr, cur, conn)
        out("find_func_cpp: связи вызовов (при наличии ccc_use_function_list — из AST, иначе эвристика по графу)...")
        import sync_cpp_func_from_ccc
        n_ccc = sync_cpp_func_from_ccc.sync_cpp_func_connections_from_ccc(conn, cur, gr, out)
        if n_ccc is None:
            gr = find_func_cpp.find_func_call_connection(gr, cur, conn)
        elif n_ccc == 0:
            out("find_func_cpp: связи из ccc не сопоставлены — эвристика find_func_call_connection.")
            gr = find_func_cpp.find_func_call_connection(gr, cur, conn)
        if stopped():
            return (False, "Остановлено пользователем.")

        out_dir = output_dir or os.path.join(graph_dir, "graphs")
        os.makedirs(out_dir, exist_ok=True)
        num_nodes = gr.number_of_nodes()
        num_edges = gr.number_of_edges()
        LARGE_NODES = 80000
        LARGE_EDGES = 250000
        is_large = num_nodes > LARGE_NODES or num_edges > LARGE_EDGES
        save_full_gv = True
        render_full_pdf = False
        build_calls_pdf = True
        exclude_std_lib = filter_std_lib
        hide_utility_threshold = filter_utility_threshold
        if is_large and ask_before_full_graph:
            try:
                choices = ask_before_full_graph(num_nodes, num_edges, out_dir)
                if choices:
                    save_full_gv = choices.get("save_full_gv", True)
                    render_full_pdf = choices.get("render_full_pdf", False)
                    build_calls_pdf = choices.get("build_calls_pdf", True)
                    exclude_std_lib = choices.get("exclude_std_lib", False)
                    hide_utility_threshold = choices.get("hide_utility_threshold", 0)
            except Exception as e:
                out("Ошибка выбора пользователя: {}. Используются значения по умолчанию.".format(e))
        out("Сохранение графа (по выбору: полный .gv, PDF)...")
        create_graph_cpp.create_full_graph(
            gr, None, output_directory=out_dir, view=False, out=out,
            save_full_gv=save_full_gv, render_full_pdf=render_full_pdf, build_calls_pdf=build_calls_pdf,
            exclude_std_lib=exclude_std_lib, hide_utility_threshold=hide_utility_threshold,
        )
        out("Граф сохранён: {}".format(out_dir))
        msg = "Граф сохранён в каталог:\n{}".format(os.path.abspath(out_dir))
        return (True, msg)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (False, str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
