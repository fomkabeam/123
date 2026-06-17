# -*- coding: utf-8 -*-
"""
Анализ критических маршрутов выполнения функциональных объектов (РД НДВ, п. 3.4.3).
Для заданных экспертом списков информационных объектов (переменные, при необходимости — функции)
находит сегменты (ветви) ccc_line_seg, в которых эти объекты участвуют.
Таблица ccc_line_seg формируется только при 2-м уровне контроля (скрипт NEW_3_F_Line_Seg).
"""
import sys
import os

try:
    from dbFolder import Check_LOG_INFO
except ImportError:
    Check_LOG_INFO = None

def get_connection():
    if not Check_LOG_INFO:
        raise RuntimeError("Модуль dbFolder не найден")
    folder = Check_LOG_INFO()
    import psycopg2
    return psycopg2.connect(
        database=folder['DB_NAME'],
        user=folder['DB_USER'],
        password=folder['DB_PASS'],
        host=folder['DB_HOST'],
        port=folder['DB_PORT']
    )


def run_analysis(conn, list_variable_names, list_function_names=None):
    """
    Для списка имён переменных находит сегменты (ccc_line_seg), в диапазоне строк которых
    встречаются эти переменные (по ccc_variables_v.num_line).
    В ccc_line_seg попадают только блоки управления: IF, FOR, WHILE, SWITCH, ELSE_IF.
    Переменные вне таких блоков (объявление в начале функции, «плоский» код) не попадут
    ни в один сегмент — это ожидаемо.
    Возвращает: (list of result tuples, stats_dict).
    stats_dict: total_vars_checked, vars_with_segments, vars_without_segments, total_segment_hits.
    """
    if not list_variable_names and not list_function_names:
        return [], {}
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND LOWER(table_name) = 'ccc_line_seg');
    """)
    if not cur.fetchone()[0]:
        cur.close()
        return [], {"table_missing": True}
    cur.execute("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND LOWER(table_name) = 'ccc_variables_v');
    """)
    if not cur.fetchone()[0]:
        cur.close()
        return [], {"table_missing": True}
    results = []
    vars_with_hits = set()  # имена переменных, для которых нашли хотя бы один сегмент
    for var_name in list_variable_names:
        var_name = (var_name or "").strip()
        if not var_name:
            continue
        cur.execute("""
            SELECT v.var_id, v.file_id, v.num_line, fl.path
            FROM ccc_variables_v v
            LEFT JOIN ccc_file_list fl ON fl.id_file = v.file_id
            WHERE LOWER(TRIM(v.var_name)) = LOWER(%s)
        """, (var_name,))
        vars_rows = cur.fetchall()
        for (var_id, file_id, num_line, path) in vars_rows:
            if num_line is None or file_id is None:
                continue
            cur.execute("""
                SELECT ls.line_seg_id, ls.name, ls.start_line, ls.end_line, ls.parent_func_id
                FROM ccc_line_seg ls
                WHERE ls.file_id = %s AND ls.start_line <= %s AND ls.end_line >= %s
                ORDER BY ls.line_seg_id
            """, (file_id, num_line, num_line))
            for (line_seg_id, seg_name, start_line, end_line, parent_func_id) in cur.fetchall():
                results.append((
                    var_name,
                    path or "",
                    parent_func_id or 0,
                    line_seg_id,
                    seg_name or "",
                    start_line or 0,
                    end_line or 0,
                ))
                vars_with_hits.add(var_name)
    cur.close()
    unique_vars = [v for v in list_variable_names if (v or "").strip()]
    stats = {
        "total_vars_checked": len(unique_vars),
        "vars_with_segments": len(vars_with_hits),
        "vars_without_segments": len(unique_vars) - len(vars_with_hits),
        "total_segment_hits": len(results),
        "table_missing": False,
    }
    return results, stats


def run_analysis_and_print(list_variable_names, list_function_names=None):
    """Запуск анализа и вывод в stdout (для вызова из CLI или из GUI с захватом вывода)."""
    conn = get_connection()
    try:
        rows, stats = run_analysis(conn, list_variable_names, list_function_names)
        if stats.get("table_missing"):
            print("Таблица ccc_line_seg или ccc_variables_v отсутствует. Выполните анализ с 2-м уровнем контроля (метод ALL или LS).")
            return
        if stats["total_vars_checked"] == 0:
            print("Список переменных пуст.")
            return
        print("Из {} переменных сегменты найдены для {} (без сегментов: {}). Всего записей сегментов: {}.".format(
            stats["total_vars_checked"], stats["vars_with_segments"], stats["vars_without_segments"], stats["total_segment_hits"]))
        print("(Сегменты строятся только для блоков IF, FOR, WHILE, SWITCH, ELSE; переменные вне этих блоков не попадают в отчёт.)")
        if not rows:
            return
        print("Маршруты (сегменты), затрагивающие выбранные переменные:")
        print("-" * 80)
        for r in rows:
            print("  Переменная: {}  |  Файл: {}  |  Функция ID: {}  |  Сегмент: {} (id={})  строки {}-{}".format(
                r[0], r[1], r[2], r[4], r[3], r[5], r[6]))
    finally:
        conn.close()


if __name__ == "__main__":
    # Из файла: путь к файлу списка переменных в первом аргументе (по одной на строку)
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                names = [line.strip() for line in f if line.strip()]
        else:
            names = []
    else:
        names = []
    run_analysis_and_print(names)
