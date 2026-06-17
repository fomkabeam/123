# -*- coding: utf-8 -*-
"""
Запуск clang-tidy для анализа проекта по compile_commands.json.
Результаты пишутся в таблицу clang_diagnostics в PostgreSQL.

Что ищет (проверки -checks):
  - clang-diagnostic-unused-function   — неиспользуемые функции
  - clang-diagnostic-unused-variable   — неиспользуемые переменные
  - clang-analyzer-deadcode.DeadStores  — мёртвые присваивания
  - clang-analyzer-deadcode.UnreachableCode — недостижимый код

Важно: если clang не находит include (Qt, protobuf и т.д.), он не разбирает файл
до конца и эти проверки не срабатывают — будут только ошибки «file not found».
Пути к файлам должны точно совпадать с полем "file" в compile_commands.json.

LOG_PATH.txt:
  CLANG_FILES_FROM=compile_commands  — брать список файлов из compile_commands.json (по умолчанию, рекомендуется).
  CLANG_FILES_FROM=ccc_file_list     — брать из БД (пути могут не совпадать с JSON).
  CLANG_DEBUG=1                      — для первых 2 файлов вывести stdout/stderr clang-tidy.
  CLANG_TIDY_CHECKS=check1,check2    — дополнительные проверки clang-tidy (добавляются к базовому набору).

Почему проверяется меньше файлов, чем в ccc_file_list:
  В compile_commands.json только единицы компиляции — .c/.cc/.cpp/.cxx, которые реально
  компилируются (429 штук). Заголовки .h не компилируются отдельно, они подключаются из .cpp.
  В ccc_file_list ~1100 записей — это все файлы дерева (включая .h). clang-tidy запускается
  только по тем файлам, для которых есть запись в compile_commands.json.

Откуда в таблице пути к .h:
  Когда в .cpp подключается заголовок и в нём не находится include — ошибка выдаётся в том
  .h файле (строка с #include). Поэтому file_path в диагностике часто указывает на .h.
"""

import json
import os
import re
import shlex
import shutil
import sys
import subprocess

import psycopg2

from dbFolder import folder


def get_compile_commands_path(config=None):
    """Путь к compile_commands.json. config — словарь из GUI; если не передан — из dbFolder.folder."""
    cfg = config if config is not None else folder
    path = (cfg.get('COMPILE_COMMANDS') or '').strip()
    if not path:
        print("COMPILE_COMMANDS не задан – clang-анализ пропущен.")
        return None
    if not os.path.isfile(path):
        print("Файл compile_commands.json не найден: {}".format(path))
        return None
    return path


def get_build_dir(compile_commands_path):
    """Каталог сборки = директория, где лежит compile_commands.json."""
    return os.path.dirname(os.path.abspath(compile_commands_path))


def _norm_path(p):
    if not p:
        return ""
    return os.path.normpath(os.path.abspath(p))


def get_compile_command_for_file(build_dir, file_path):
    """Возвращает запись {directory, command, file} для файла из compile_commands.json или None (точное совпадение пути)."""
    path = os.path.join(build_dir, "compile_commands.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            if entry.get("file") == file_path:
                return entry
        return None
    except Exception:
        return None


def get_compile_command_for_file_norm(build_dir, file_path):
    """Как get_compile_command_for_file, но совпадение по нормированному пути (для заголовков и путей из БД)."""
    path = os.path.join(build_dir, "compile_commands.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        target = _norm_path(file_path)
        for entry in data:
            if _norm_path(entry.get("file") or "") == target:
                return entry
        return None
    except Exception:
        return None


def get_extra_args_from_command(cmd_str):
    """
    Из command строки компиляции извлекаем флаги для -extra-arg-before:
    -I, -isystem, -fPIC, -fPIE, -std=..., -D... (чтобы Qt и код разбирались корректно).
    """
    out = []
    # -I path
    for m in re.finditer(r"-I(\S+)", cmd_str):
        out.append("-I" + m.group(1))
    # -isystem path
    for m in re.finditer(r"-isystem\s+(\S+)", cmd_str):
        out.append("-isystem")
        out.append(m.group(1))
    # -fPIC / -fPIE (иначе Qt даёт #error "Compile your code with -fPIC")
    if "-fPIC" in cmd_str:
        out.append("-fPIC")
    if "-fPIE" in cmd_str:
        out.append("-fPIE")
    # -std=...
    m_std = re.search(r"-std=(\S+)", cmd_str)
    if m_std:
        out.append("-std=" + m_std.group(1))
    # -D макросы (-DMACRO или -D MACRO=value)
    for m in re.finditer(r"-D\s*(\S+)", cmd_str):
        out.append("-D" + m.group(1))
    return out


def get_source_files_from_compile_commands(compile_commands_path):
    """
    Список исходников из compile_commands.json — пути и команды совпадают на 100%,
    clang-tidy всегда найдёт запись и подставит правильные -I.
    """
    exts = ('.c', '.cc', '.cpp', '.cxx')
    files = []
    try:
        with open(compile_commands_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for entry in data:
            path = entry.get('file')
            if not path or not isinstance(path, str):
                continue
            if path.endswith(exts) or path.endswith(tuple(e.upper() for e in exts)):
                files.append(path)
    except Exception as e:
        print("clang_runner: не удалось прочитать compile_commands.json: {}".format(e))
    return files


def get_source_files_from_db(conn):
    """
    Список исходников из ccc_file_list (расширения .c, .cc, .cpp, .cxx).
    Пути могут не совпадать с ключами в compile_commands.json.
    """
    exts = ('.c', '.cc', '.cpp', '.cxx', '.C', '.CPP')
    cur = conn.cursor()
    cur.execute("SELECT path FROM ccc_file_list")
    rows = cur.fetchall()
    files = []
    for (p,) in rows:
        if not p:
            continue
        lower = p.lower()
        for e in exts:
            if lower.endswith(e):
                files.append(p)
                break
    return files


def ensure_table(conn):
    """Создаём таблицу clang_diagnostics при необходимости. Очищаем при DROP_TBL=1."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clang_diagnostics (
            id SERIAL PRIMARY KEY,
            file_path TEXT,
            line INT,
            col INT,
            severity TEXT,
            check_name TEXT,
            message TEXT
        );
    """)
    try:
        dt = int(folder.get('DROP_TBL', '0'))
    except Exception:
        dt = 0
    if dt == 1:
        cur.execute("TRUNCATE TABLE clang_diagnostics;")
    conn.commit()


DIAG_RE = re.compile(
    r'^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+):\s+'
    r'(?P<severity>warning|error|note):\s+'
    r'(?P<msg>.*?)(?:\s+\[(?P<check>[^\]]+)\])?\s*$'
)


def run_clang_tidy_for_file(build_dir, file_path, clang_tidy_bin, debug=False):
    """
    Запуск clang-tidy для одного файла.
    Пути -I/-isystem из compile_commands.json передаём явно через -extra-arg-before,
    т.к. при запуске из Python clang-tidy иногда не подхватывает их из JSON.
    """
    diagnostics = []

    base_checks = (
        "-*,"
        "clang-diagnostic-unused-function,"
        "clang-diagnostic-unused-variable,"
        "clang-analyzer-deadcode.DeadStores,"
        "clang-analyzer-deadcode.UnreachableCode,"
        "clang-analyzer-core.CallAndMessage"
    )
    extra_checks = (folder.get("CLANG_TIDY_CHECKS", "") or "").strip()
    if extra_checks:
        checks_str = "".join(base_checks) + "," + extra_checks
    else:
        checks_str = "".join(base_checks)

    extra_args = []
    entry = get_compile_command_for_file(build_dir, file_path)
    if entry:
        cmd = entry.get("command", "")
        incl = get_extra_args_from_command(cmd)
        for a in incl:
            # Каждый аргумент отдельно, чтобы пути с пробелами не ломали команду
            extra_args.append("-extra-arg-before=" + a)

    extra_str = " ".join(shlex.quote(x) for x in extra_args)
    inner = (
        "cd " + shlex.quote(build_dir) +
        " && " + shlex.quote(clang_tidy_bin) + " -p . " + (extra_str + " " if extra_str else "") +
        "-checks=" + shlex.quote(checks_str) +
        " -quiet " + shlex.quote(file_path) + " --"
    )
    cmd_str = "bash -lc " + shlex.quote(inner)

    try:
        proc = subprocess.Popen(
            cmd_str,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except OSError as e:
        print("Ошибка запуска clang-tidy: {}".format(e))
        return diagnostics

    stdout_lines = [line.rstrip("\n") for line in proc.stdout]
    stderr_text = proc.stderr.read()
    proc.wait()

    if debug:
        print("  [CLANG_DEBUG] path = {}".format(file_path))
        entry = get_compile_command_for_file(build_dir, file_path)
        if entry:
            print("  [CLANG_DEBUG] запись в compile_commands.json: directory = {}".format(entry.get("directory", "")))
            cmd = entry.get("command", "")
            # Извлекаем все -I и -isystem пути (именно они задают, откуда искать #include <...>)
            incl = re.findall(r"-I(\S+)|-isystem\s+(\S+)", cmd)
            print("  [CLANG_DEBUG] пути поиска include (-I и -isystem) из JSON:")
            for m in incl:
                p = (m[0] or m[1]).strip()
                if p:
                    print("    {}".format(p))
        else:
            print("  [CLANG_DEBUG] для этого файла НЕТ записи в compile_commands.json — clang-tidy не подставит -I!")
        print("  [CLANG_DEBUG] stdout (первые 15 строк):")
        for ln in stdout_lines[:15]:
            print("    | {}".format(ln))
        if not stdout_lines:
            print("    (пусто)")
        err_lines = stderr_text.strip().split("\n") if stderr_text else []
        print("  [CLANG_DEBUG] stderr (первые 10 строк):")
        for ln in err_lines[:10]:
            print("    | {}".format(ln))
        if not err_lines:
            print("    (пусто)")

    for line in stdout_lines:
        m = DIAG_RE.match(line)
        if not m:
            continue
        d = m.groupdict()
        diagnostics.append((
            d.get('file') or file_path,
            int(d.get('line') or 0),
            int(d.get('col') or 0),
            d.get('severity') or '',
            d.get('check') or '',
            d.get('msg') or '',
        ))

    return diagnostics


def save_diagnostics(conn, diags):
    """Сохраняем все диагностики в БД. В GUI можно отфильтровать «file not found»."""
    if not diags:
        return 0
    cur = conn.cursor()
    for file_path, line, col, severity, check_name, message in diags:
        cur.execute(
            """
            INSERT INTO clang_diagnostics
                (file_path, line, col, severity, check_name, message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (file_path, line, col, severity, check_name, message)
        )
    conn.commit()
    return len(diags)


def main():
    compile_commands = get_compile_commands_path()
    if not compile_commands:
        return
    build_dir = get_build_dir(compile_commands)

    try:
        conn = psycopg2.connect(
            database=folder['DB_NAME'],
            user=folder['DB_USER'],
            password=folder['DB_PASS'],
            host=folder['DB_HOST'],
            port=folder['DB_PORT'],
        )
    except Exception as e:
        print("Ошибка подключения к БД: {}".format(e))
        return

    ensure_table(conn)

    clang_tidy_bin = shutil.which("clang-tidy") or "clang-tidy"
    print("clang_runner: build_dir (cwd для clang-tidy) = {}".format(build_dir))
    print("clang_runner: clang-tidy = {}".format(clang_tidy_bin))

    # Откуда брать список файлов: compile_commands (рекомендуется) или ccc_file_list
    source = folder.get('CLANG_FILES_FROM', 'compile_commands').strip().lower()
    if source == 'compile_commands' or source == 'compile_commands.json':
        files = get_source_files_from_compile_commands(compile_commands)
        print("clang_runner: список файлов из compile_commands.json (пути совпадают с JSON).")
    else:
        files = get_source_files_from_db(conn)
        print("clang_runner: список файлов из ccc_file_list (задайте CLANG_FILES_FROM=compile_commands для совпадения с JSON).")

    if not files:
        print("clang_runner: нет исходных файлов.")
        conn.close()
        return

    print("clang_runner: файлов для анализа: {}".format(len(files)))

    debug_mode = folder.get('CLANG_DEBUG', '0').strip() == '1'
    if debug_mode:
        print("clang_runner: CLANG_DEBUG=1 — отладочный вывод для первых 2 файлов.")

    total_diags = 0
    for idx, fpath in enumerate(files, start=1):
        print("clang_runner: [{}/{}] {}".format(idx, len(files), fpath))
        do_debug = debug_mode and idx <= 2
        diags = run_clang_tidy_for_file(build_dir, fpath, clang_tidy_bin, debug=do_debug)
        saved = save_diagnostics(conn, diags)
        total_diags += saved

    print("clang_runner: всего диагностик сохранено: {}".format(total_diags))
    conn.close()


if __name__ == '__main__':
    main()

