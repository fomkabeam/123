# -*- coding: utf-8 -*-
"""
Отчёт покрытия сенсоров: сравнивает реестр (ccc_sensor_registry) и фактические события (ccc_sensoragramma).
"""

from dbFolder import Check_LOG_INFO


def main():
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
    try:
        cur.execute("SELECT COUNT(*) FROM ccc_sensor_registry")
        total = int(cur.fetchone()[0] or 0)
    except Exception:
        total = 0
    try:
        cur.execute(
            """
            SELECT COUNT(DISTINCT r.sensor_id)
            FROM ccc_sensor_registry r
            INNER JOIN ccc_sensoragramma s ON s.sensor_id = r.sensor_id
            """
        )
        covered = int(cur.fetchone()[0] or 0)
    except Exception:
        covered = 0
    uncovered = max(total - covered, 0)
    pct = (float(covered) / float(total) * 100.0) if total else 0.0

    print("sensor_coverage_report:")
    print("  registry_total: {}".format(total))
    print("  covered:        {}".format(covered))
    print("  uncovered:      {}".format(uncovered))
    print("  coverage_pct:   {:.2f}%".format(pct))

    # Топ не сработавших (для проверки)
    try:
        cur.execute(
            """
            SELECT r.sensor_id, r.file_path, r.line_no
            FROM ccc_sensor_registry r
            LEFT JOIN (SELECT DISTINCT sensor_id FROM ccc_sensoragramma) s ON s.sensor_id = r.sensor_id
            WHERE s.sensor_id IS NULL
            ORDER BY r.sensor_id
            LIMIT 50
            """
        )
        rows = cur.fetchall()
        if rows:
            print("\nНе сработали (первые 50):")
            for sid, path, line_no in rows:
                print("  {}  {}:{}".format(sid, path or "", line_no or ""))
    except Exception:
        pass

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

