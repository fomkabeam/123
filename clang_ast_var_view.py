# -*- coding: utf-8 -*-
"""
clang_ast_var_view.py - Создание представления ccc_variables_v
на основе ccc_definition_variable (из clang_ast_variables.py).

Заменяет NEW_4_Variabels_C + usingVariables для CLANG_AST пайплайна.
Совместимо с GUI и critical_routes.py.

Безопасное создание: если ccc_variables_v уже существует как ТАБЛИЦА
(из старого анализа NEW_4_Variabels_C), сначала удаляется DROP TABLE,
затем создаётся VIEW.
"""

import sys
import psycopg2
from dbFolder import folder


def ensure_view(conn):
    """Создать представление ccc_variables_v из таблиц AST."""
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ccc_definition_variable'
        )
    """)
    if not cur.fetchone()[0]:
        print("clang_ast_var_view: таблица ccc_definition_variable не существует. Сначала выполните clang_ast_variables.")
        cur.close()
        return False

    # Безопасное удаление: проверяем тип объекта (TABLE или VIEW) и удаляем правильной командой
    try:
        cur.execute("""
            SELECT table_type FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ccc_variables_v'
        """)
        row = cur.fetchone()
        if row:
            obj_type = row[0]
            print("clang_ast_var_view: найден объект ccc_variables_v, тип: {}".format(obj_type))
            if obj_type == 'BASE TABLE':
                print("clang_ast_var_view: удаление ТАБЛИЦЫ ccc_variables_v...")
                cur.execute("DROP TABLE ccc_variables_v CASCADE")
                conn.commit()
            elif obj_type == 'VIEW':
                print("clang_ast_var_view: удаление ПРЕДСТАВЛЕНИЯ ccc_variables_v...")
                cur.execute("DROP VIEW ccc_variables_v CASCADE")
                conn.commit()
        else:
            print("clang_ast_var_view: объект ccc_variables_v не существует, создаём представление")
    except Exception as e:
        print("clang_ast_var_view: ошибка при проверке/удалении: {}".format(e))
        try:
            conn.rollback()
        except Exception:
            pass
        # Принудительно удалить оба варианта
        try:
            cur.execute("DROP VIEW IF EXISTS ccc_variables_v CASCADE")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("DROP TABLE IF EXISTS ccc_variables_v CASCADE")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    try:
        cur.execute("""
            CREATE VIEW ccc_variables_v AS
            SELECT
                idvar AS var_id,
                file_id,
                name AS var_name,
                var_type,
                line_detect AS num_line,
                scope,
                is_static,
                COALESCE(has_init, 0) AS has_init,
                COALESCE(is_security_critical, 0) AS is_security_critical,
                CASE
                    WHEN is_security_critical = 1 THEN 'CRITICAL'
                    WHEN (has_init = 0 OR has_init IS NULL) AND scope IN ('local', 'global') THEN 'HIGH'
                    WHEN scope = 'parameter' THEN 'MEDIUM'
                    ELSE 'LOW'
                END AS severity
            FROM ccc_definition_variable
            ORDER BY file_id, line_detect
        """)
        conn.commit()
    except Exception as e:
        print("clang_ast_var_view: ошибка создания представления: {}".format(e))
        try:
            conn.rollback()
        except Exception:
            pass
        cur.close()
        return False

    cur.execute("SELECT COUNT(*) FROM ccc_variables_v")
    total = cur.fetchone()[0]
    print("clang_ast_var_view: представление ccc_variables_v создано, записей: {}".format(total))
    cur.close()
    return True


def main():
    try:
        conn = psycopg2.connect(
            database=folder["DB_NAME"],
            user=folder["DB_USER"],
            password=folder["DB_PASS"],
            host=folder["DB_HOST"],
            port=folder["DB_PORT"],
        )
    except Exception as e:
        print("clang_ast_var_view: ошибка подключения к БД: {}".format(e))
        return
    success = ensure_view(conn)
    conn.close()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
