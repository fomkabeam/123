# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import subprocess
import psycopg2

def Check_LOG_INFO():
    """Чтение LOG_PATH.txt рядом с исполняемым файлом (frozen) или модулем (dev)."""
    DB_INFO = {}
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "LOG_PATH.txt")
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            for line in file:
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key:
                        DB_INFO[key] = value
        return DB_INFO
    except FileNotFoundError:
        print("ОШИБКА: Файл {} не найден".format(config_path))
        sys.exit(1)
    except Exception as e:
        print("ОШИБКА при чтении конфигурации {}: {}".format(config_path, e))
        sys.exit(1)


def validate_config(folder):
    """Проверка обязательных параметров конфигурации."""
    required = ["DB_NAME", "DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "SEARH_METH"]
    missing = [key for key in required if not folder.get(key)]
    if missing:
        print("ОШИБКА: Отсутствуют обязательные параметры: {}".format(", ".join(missing)))
        return False
    method = folder.get("SEARH_METH", "").strip()
    if method in ("CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"):
        if not folder.get("COMPILE_COMMANDS", "").strip():
            print("ОШИБКА: Для метода {} требуется COMPILE_COMMANDS".format(method))
            return False
    return True


folder = Check_LOG_INFO()

_DB_CONN = None
_DB_CUR = None


def _get_db():
    """Ленивое подключение к БД для вспомогательных запросов."""
    global _DB_CONN, _DB_CUR
    if _DB_CONN is None or _DB_CUR is None:
        _DB_CONN = psycopg2.connect(
            database=folder["DB_NAME"],
            user=folder["DB_USER"],
            password=folder["DB_PASS"],
            host=folder["DB_HOST"],
            port=folder["DB_PORT"],
        )
        _DB_CUR = _DB_CONN.cursor()
    return _DB_CONN, _DB_CUR


def get_file_path():
    conn, cur = _get_db()
    cur.execute("select path from ccc_file_list where sourse_or_lib = 'sourse'")
    buff = cur.fetchall()
    return [row[0] for row in buff]


def len_files_for_type(typ="sourse"):
    conn, cur = _get_db()
    cur.execute("select count(*) from ccc_var_use")
    l = cur.fetchone()
    return l[0] if l else 0
STEP_ALIASES = {
    # Исторический шаг поиска классов заменён на AST-вариант.
    "findCppClass": "clang_ast_classes",
}


def _resolve_step_name(script_name):
    return STEP_ALIASES.get(script_name, script_name)


def _is_step_available(script_name):
    resolved = _resolve_step_name(script_name)
    # Для frozen/runner ориентируемся на модульную доступность.
    if importlib.util.find_spec(resolved) is not None:
        return True
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.isfile(os.path.join(base_dir, resolved + ".py"))


def _run_script(script_name, runner=None):
    """
    Запуск одного шага анализа.
    Возвращает код 0 при успехе, ненулевой при ошибке.
    """
    resolved = _resolve_step_name(script_name)
    if not _is_step_available(script_name):
        print("ОШИБКА: шаг '{}' недоступен (ожидался модуль '{}')".format(script_name, resolved))
        return 127
    if runner is not None:
        rc = runner(resolved)
        return 0 if rc is None else int(rc)
    python_path = folder.get('PATH_PYTHON', 'python3 ')
    if not python_path.endswith(' ') and not python_path.endswith(os.path.sep):
        python_path = python_path + ' '
    return os.system(python_path + resolved + ".py")


def _execute_pipeline(pipeline, runner=None):
    """Выполнить список шагов с fail-fast. Возвращает код завершения."""
    total = len(pipeline)
    for idx, script_name in enumerate(pipeline, 1):
        print("PIPELINE_STAGE {}/{}: {}".format(idx, total, script_name), flush=True)
        print("{}_Start".format(script_name), flush=True)
        rc = _run_script(script_name, runner)
        if rc != 0:
            print("{}_FAILED: код {}".format(script_name, rc), flush=True)
            return rc
        print("{}_End".format(script_name), flush=True)
    return 0


# Пайплайн для методов CLANG / CLANG_AST / CLANG_AST_NO_SENS (один и тот же порядок этапов)
_CLANG_PIPELINE = [
    "find_files", "clang_ast_connect", "clang_ast_classes", "clang_ast_runner",
    "clang_ast_variables", "NEW_3_F_Line_Seg", "clang_ast_var_view",
    "clang_runner", "createReport",
]


def get_pipeline_for(depth, method):
    """
    Возвращает список имён скриптов (этапов) пайплайна для данной пары (уровень, метод).
    Используется для универсального «Продолжить с этапа» и «Пропустить этапы» в GUI.
    Для LS фактический порядок (AST или legacy) задаётся в get_effective_pipeline по COMPILE_COMMANDS;
    здесь для совместимости возвращается AST-вариант уровня 2.
    """
    method = method.strip()
    if method in ("CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"):
        return list(_CLANG_PIPELINE)
    depth_i = int(depth) if isinstance(depth, str) else int(depth)
    key = (depth_i, method)
    pl = _PIPELINES_BY_DEPTH_METHOD.get(key)
    if pl is not None:
        return pl
    if method == "LS" and depth_i == 2:
        return [
            "find_files",
            "clang_ast_connect",
            "clang_ast_classes",
            "clang_ast_runner",
            "NEW_3_F_Line_Seg",
        ]
    return None


def get_effective_pipeline(depth, method, folder_override=None):
    """
    Возвращает фактически используемый пайплайн с учётом fallback-логики.
    folder_override: словарь как LOG_PATH.txt (используется из GUI для предварительной проверки).
    """
    cfg = folder_override if folder_override is not None else folder
    depth_i = int(depth) if isinstance(depth, str) else int(depth)
    method = (method or "").strip()
    cc = (cfg.get("COMPILE_COMMANDS") or "").strip()

    # Сегменты строк (LS): при наличии compile_commands не смешиваем AST с findFunction —
    # clang_ast_runner заполняет ccc_definition_function для NEW_3_F_Line_Seg.
    if method == "LS" and depth_i == 2:
        if cc:
            print(
                "LS: задан COMPILE_COMMANDS — контур сегментов: AST (connect/classes/runner) → NEW_3_F_Line_Seg."
            )
            return [
                "find_files",
                "clang_ast_connect",
                "clang_ast_classes",
                "clang_ast_runner",
                "NEW_3_F_Line_Seg",
            ]
        print(
            "LS: COMPILE_COMMANDS не задан — legacy: findFunction/funcToNormal → NEW_3_F_Line_Seg (пониженная точность)."
        )
        return [
            "find_files",
            "findConnectionBetweenFilesCpp",
            "findFunction",
            "funcToNormal",
            "NEW_3_F_Line_Seg",
        ]

    if depth_i in (2, 3) and method == "ALL" and not cc:
        print(
            "ВНИМАНИЕ: COMPILE_COMMANDS не задан — для уровня {} используется legacy ALL (эвристики, не AST).".format(
                depth_i
            )
        )
        return list(_LEGACY_ALL_PIPELINE[depth_i])
    return get_pipeline_for(depth_i, method)


def list_available_methods(depth, folder_override=None):
    """
    Возвращает методы, которые реально можно запустить (пайплайн существует, все шаги доступны).
    """
    depth_i = int(depth) if isinstance(depth, str) else int(depth)
    cfg = folder_override if folder_override is not None else folder

    # Кандидаты из таблицы (уровень 2/3/4) + Clang-режимы для 2/3; LS только для уровня 2 (см. get_effective_pipeline)
    candidates = {m for (d, m) in _PIPELINES_BY_DEPTH_METHOD.keys() if d == depth_i}
    if depth_i in (2, 3):
        candidates.update(["CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"])
    if depth_i == 2:
        candidates.add("LS")
    candidates = sorted(candidates)
    out = []
    for method in candidates:
        # Для CLANG/AST методов — конфиг должен содержать compile_commands
        if method in ("CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"):
            if not (cfg.get("COMPILE_COMMANDS") or "").strip():
                continue
        pipeline = get_effective_pipeline(depth_i, method, folder_override=cfg)
        if not pipeline:
            continue
        if all(_is_step_available(step) for step in pipeline):
            out.append(method)
    return out


# Пайплайны по (CHECK_DEPTH, SEARH_METH) для уровней 2, 3, 4 (без Clang-методов)
_PIPELINES_BY_DEPTH_METHOD = {
    (4, "ALL"): ["find_files", "findConnectionBetweenFilesCpp", "createReport"],
    (4, "FF_PFS"): ["find_files", "findConnectionBetweenFilesCpp"],
    (4, "FF"): ["find_files"],
    (4, "PFS"): ["findConnectionBetweenFilesCpp"],
    (4, "CO"): ["createReport"],
    (3, "CO"): ["createReport"],
    (3, "ND"): ["findUseFunction"],
    # Основной контур для 3/2 уровней — AST-first. Legacy-модули остаются как fallback.
    (3, "ALL"): ["find_files", "clang_runner", "clang_ast_classes", "clang_ast_runner", "clang_ast_variables", "createReport"],
    (3, "FF_PFS"): ["find_files", "findConnectionBetweenFilesCpp"],
    (3, "FF"): ["find_files"],
    (3, "PFS"): ["findConnectionBetweenFilesCpp"],
    (3, "C"): ["findCppClass"],
    (3, "F"): ["findFunction", "funcToNormal"],
    (3, "V"): ["NEW_4_Variabels_C"],
    (3, "CPI"): ["findConnectionBetweenFilesCpp"],
    (3, "ChI"): ["findUseFunction"],
    (2, "CO"): ["createReport"],
    (2, "ND"): ["findUseFunction"],
    (2, "ALL"): ["find_files", "clang_runner", "clang_ast_classes", "clang_ast_runner", "clang_ast_variables", "createReport"],
    (2, "FF_PFS"): ["find_files", "findConnectionBetweenFilesCpp"],
    (2, "FF"): ["find_files"],
    (2, "PFS"): ["findConnectionBetweenFilesCpp"],
    (2, "C"): ["findCppClass"],
    (2, "F"): ["findFunction", "funcToNormal"],
    (2, "V"): ["NEW_4_Variabels_C"],
    (2, "CPI"): ["findConnectionBetweenFilesCpp"],
    (2, "ChI"): ["findUseFunction", "usingVariables"],
    (2, "ADD_JSens"): ["NEW_5_JSensor_NEW_Variant", "sensor_registry_builder"],
    # LS обрабатывается в get_effective_pipeline (AST vs legacy в зависимости от COMPILE_COMMANDS)
}

_LEGACY_ALL_PIPELINE = {
    3: ["find_files", "findConnectionBetweenFilesCpp", "findFunction", "funcToNormal", "NEW_4_Variabels_C", "findUseFunction", "createReport"],
    2: ["find_files", "findConnectionBetweenFilesCpp", "findFunction", "funcToNormal", "NEW_3_F_Line_Seg", "NEW_4_Variabels_C", "findUseFunction", "usingVariables", "createReport"],
}


def _normalize_pipeline_from(value):
    """GUI мог сохранить «N/M: step»; для index() нужен только step."""
    s = (value or "").strip()
    if ": " in s:
        s = s.split(": ", 1)[1].strip()
    return s


def _apply_pipeline_options(pipeline, folder):
    """Применяет PIPELINE_FROM и PIPELINE_SKIP к списку этапов. Возвращает итоговый список."""
    if not pipeline:
        return pipeline
    start_from = _normalize_pipeline_from(
        folder.get("PIPELINE_FROM") or folder.get("CLANG_AST_FROM") or ""
    )
    skip_str = (folder.get("PIPELINE_SKIP") or "").strip()
    skip_set = {s.strip() for s in skip_str.split(",") if s.strip()}
    if start_from:
        try:
            idx = pipeline.index(start_from)
            pipeline = pipeline[idx:]
            print("Продолжение с этапа: {} (пропущено {} шагов)".format(start_from, idx))
        except ValueError:
            print("PIPELINE_FROM='{}' не найден в пайплайне, запуск с начала.".format(start_from))
    if skip_set:
        before = len(pipeline)
        pipeline = [s for s in pipeline if s not in skip_set]
        print("Пропуск этапов (PIPELINE_SKIP): {} — исключено {} из {}".format(skip_str, before - len(pipeline), before))
    return pipeline


def _apply_clang_fast_options(pipeline, cfg):
    """
    Доп. опции для CLANG/CLANG_AST:
    - AST_SKIP_TIDY=1: пропустить clang_runner (быстрый AST-прогон).
    """
    if not pipeline:
        return pipeline
    out = list(pipeline)
    skip_tidy = str(cfg.get("AST_SKIP_TIDY", "0")).strip() in ("1", "true", "True", "yes", "YES")
    if skip_tidy and "clang_runner" in out:
        out = [s for s in out if s != "clang_runner"]
        print("CLANG_FAST: clang_runner пропущен (AST_SKIP_TIDY=1).", flush=True)
    return out


def main(runner=None):
    """Главная функция запуска анализа. runner(script_name) — для frozen-режима (один исполняемый файл)."""
    try:
        print("_Starter: старт пайплайна (проверка конфигурации)...", flush=True)
    except Exception:
        pass
    if not validate_config(folder):
        return 2
    method = folder.get("SEARH_METH", "").strip()

    if method in ("CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"):
        if not folder.get("COMPILE_COMMANDS", "").strip():
            print("{}: задайте COMPILE_COMMANDS в LOG_PATH.txt".format(method))
            if method == "CLANG":
                return _execute_pipeline(["find_files", "clang_runner"], runner)
            return 2

        pipeline = get_pipeline_for(None, method)
        pipeline = _apply_clang_fast_options(pipeline, folder)
        pipeline = _apply_pipeline_options(list(pipeline), folder)
        return _execute_pipeline(pipeline, runner)

    DEPTH = int(folder.get('CHECK_DEPTH', 2))
    method = folder.get('SEARH_METH', '').strip()

    if DEPTH == 4:
        pipeline = get_pipeline_for(4, method)
        if pipeline is None:
            print("ОШИБКА: неизвестный метод '{}' для 4 уровня".format(method))
            return 2
        pipeline = _apply_pipeline_options(list(pipeline), folder)
        return _execute_pipeline(pipeline, runner)
    if DEPTH in (2, 3):
        pipeline = get_effective_pipeline(DEPTH, method, folder_override=folder)
        if pipeline is None:
            print("ОШИБКА: неизвестный метод '{}' для {} уровня".format(method, DEPTH))
            return 2
        pipeline = _apply_pipeline_options(list(pipeline), folder)
        return _execute_pipeline(pipeline, runner)

    print("ОШИБКА: неподдерживаемый уровень CHECK_DEPTH={}".format(DEPTH))
    return 2


if __name__ == '__main__':
    raise SystemExit(main(runner=None))
