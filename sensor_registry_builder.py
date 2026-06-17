# -*- coding: utf-8 -*-
"""
Построение реестра сенсоров (ccc_sensor_registry) по исходникам.

Идея: реестр фиксирует «ожидаемые» сенсоры (где вставлены/присутствуют SENSOR(id);),
а ccc_sensoragramma — фактические срабатывания.
"""

import os
import re

from dbFolder import Check_LOG_INFO


SENSOR_RE = re.compile(r"\bSENSOR\s*\(\s*(\d+)\s*\)\s*;")


def build_registry(truncate=True):
    import psycopg2

    cfg = Check_LOG_INFO()
    conn = psycopg2.connect(
        database=cfg["DB_NAME"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASS"],
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Таблица должна существовать (создаётся create_sensoragramma_table.py), но на всякий случай.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ccc_sensor_registry (
            sensor_id    INTEGER PRIMARY KEY,
            file_path    TEXT,
            line_no      INTEGER,
            kind         TEXT,
            object_type  TEXT,
            object_name  TEXT,
            object_id    INTEGER
        )
        """
    )
    if truncate:
        try:
            cur.execute("TRUNCATE TABLE ccc_sensor_registry")
        except Exception:
            pass

    cur.execute("SELECT path, encoding FROM ccc_file_list WHERE sourse_or_lib = 'sourse'")
    rows = cur.fetchall()

    inserted = 0
    for file_path, enc in rows:
        if not file_path or not os.path.isfile(file_path):
            continue
        encoding = enc or "utf-8"
        try:
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    m = SENSOR_RE.search(line)
                    if not m:
                        continue
                    sensor_id = int(m.group(1))
                    # id уникален; если встречается повторно — оставляем первую запись.
                    cur.execute(
                        """
                        INSERT INTO ccc_sensor_registry (sensor_id, file_path, line_no, kind, object_type, object_name, object_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (sensor_id) DO NOTHING
                        """,
                        (sensor_id, file_path, line_no, "function_entry", "SENSOR_MACRO", None, None),
                    )
                    inserted += 1
        except Exception:
            continue

    cur.close()
    conn.close()
    print("sensor_registry_builder: готово, добавлено записей: {}".format(inserted))


if __name__ == "__main__":
    build_registry(truncate=True)

