#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
findConnectionBetweenFilesCpp

Заглушка для пайплайна уровня 4 (PFS/FF_PFS/ALL):
- обеспечивает наличие и очистку таблицы ccc_connect_list;
- не использует Clang и не требует COMPILE_COMMANDS.

Связи между файлами на основе #include для более высоких уровней
строятся через clang_ast_connect.py (при наличии compile_commands.json).
"""

import psycopg2

from dbFolder import folder


def main():
    print("findConnectionBetweenFilesCpp: подготовка таблицы ccc_connect_list (без Clang).")
    try:
        conn = psycopg2.connect(
            database=folder["DB_NAME"],
            user=folder["DB_USER"],
            password=folder["DB_PASS"],
            host=folder["DB_HOST"],
            port=folder["DB_PORT"],
        )
    except Exception as e:
        print("findConnectionBetweenFilesCpp: ошибка подключения к БД: {}".format(e))
        return

    try:
        cur = conn.cursor()
        # Минимальная структура: id_file, connectToID, lineID
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ccc_connect_list (
                id_file     INTEGER,
                connectToID INTEGER,
                lineID      INTEGER
            )
            """
        )
        # Для 4-го уровня достаточно очистить старые данные, чтобы отчёт был консистентен.
        cur.execute("TRUNCATE TABLE ccc_connect_list")
        conn.commit()
    except Exception as e:
        print("findConnectionBetweenFilesCpp: ошибка подготовки таблицы: {}".format(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

