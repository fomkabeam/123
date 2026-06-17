# -*- coding: utf-8 -*-
import psycopg2
from dbFolder import Check_LOG_INFO


def create_sensoragramma_table():
    """
    Создаёт/обновляет таблицы динамического анализа:
    - ccc_sensor_registry   : реестр сенсоров (ожидаемые точки контроля)
    - ccc_sensoragramma     : фактические события срабатывания
    """
    folder = Check_LOG_INFO()

    conn = psycopg2.connect(
        database=folder["DB_NAME"],
        user=folder["DB_USER"],
        password=folder["DB_PASS"],
        host=folder["DB_HOST"],
        port=folder["DB_PORT"],
    )
    cur = conn.cursor()

    # Реестр сенсоров
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

    # События сенсоров (новая схема)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ccc_sensoragramma (
            event_id     BIGSERIAL PRIMARY KEY,
            run_id       BIGINT,
            sensor_id    INTEGER NOT NULL,
            pid          INTEGER,
            parent_pid   INTEGER,
            ts           TIMESTAMP,
            host         TEXT,
            payload      TEXT
        )
        """
    )

    # Совместимость с ранее созданными схемами (добавляем недостающие поля без drop).
    compatibility_columns = [
        ("run_id", "BIGINT"),
        ("sensor_id", "INTEGER"),
        ("parent_pid", "INTEGER"),
        ("ts", "TIMESTAMP"),
        ("host", "TEXT"),
        ("payload", "TEXT"),
    ]
    for col_name, col_type in compatibility_columns:
        cur.execute(
            """
            DO $$ BEGIN
                ALTER TABLE ccc_sensoragramma ADD COLUMN %s %s;
            EXCEPTION WHEN duplicate_column THEN
                NULL;
            END $$;
            """
            % (col_name, col_type)
        )

    # Индексы для отчётов покрытия и фильтрации по запуску.
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensoragramma_sensor_id ON ccc_sensoragramma(sensor_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensoragramma_run_id ON ccc_sensoragramma(run_id)")
    conn.commit()
    conn.close()
    print("Таблицы ccc_sensoragramma и ccc_sensor_registry готовы.")


if __name__ == "__main__":
    create_sensoragramma_table()