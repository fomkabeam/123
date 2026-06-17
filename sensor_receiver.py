# -*- coding: utf-8 -*-
"""
Приёмник сенсоров: слушает TCP порт 17176, принимает СТРУКТУРИРОВАННЫЕ события и пишет
их в PostgreSQL (таблица ccc_sensoragramma).

Поддерживаемые форматы входа:
1) JSON в одной строке:
   {"sensor_id":500123,"pid":1234,"parent_pid":1,"ts":"2026-01-01 10:00:00","run_id":1}
2) key=value;key=value
   sensor_id=500123;pid=1234;parent_pid=1;ts=2026-01-01 10:00:00;run_id=1

Raw SQL из сети НЕ выполняется.
"""
import os
import sys
import socket
import re
import argparse
import json
from datetime import datetime

def load_db_config():
    """Чтение LOG_PATH.txt: сначала из текущей папки, затем из папки скрипта."""
    cfg = {}
    for base_dir in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        config_path = os.path.join(base_dir, 'LOG_PATH.txt')
        if os.path.isfile(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        k, v = line.split('=', 1)
                        cfg[k.strip()] = v.strip()
            break
    cfg.setdefault('DB_HOST', os.environ.get('DB_HOST', 'localhost'))
    cfg.setdefault('DB_PORT', os.environ.get('DB_PORT', '5432'))
    cfg.setdefault('DB_NAME', os.environ.get('DB_NAME', 'analyse_db'))
    cfg.setdefault('DB_USER', os.environ.get('DB_USER', 'postgres'))
    cfg.setdefault('DB_PASS', os.environ.get('DB_PASS', ''))
    return cfg

def _parse_event(line):
    line = (line or "").strip()
    if not line:
        return None

    # Явно запрещаем legacy-режим с SQL.
    if re.match(r"^\s*INSERT\s+INTO\s+", line, flags=re.I):
        return {"_error": "raw SQL protocol is disabled"}

    if line.startswith("{") and line.endswith("}"):
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                return {"_error": "json payload must be object"}
            return obj
        except Exception as e:
            return {"_error": "invalid json: {}".format(e)}

    # key=value;key=value
    obj = {}
    for part in line.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        obj[k.strip()] = v.strip()
    if not obj:
        return {"_error": "unsupported payload format"}
    return obj


def _to_int(value):
    if value is None or value == "":
        return None
    return int(value)


def _to_ts(value):
    if value is None or value == "":
        return None
    # Допускаем ISO и "YYYY-MM-DD HH:MM:SS".
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def run_receiver(host='0.0.0.0', port=17176):
    try:
        import psycopg2
    except ImportError:
        print("Требуется psycopg2: pip install psycopg2-binary")
        sys.exit(1)

    cfg = load_db_config()
    if not cfg.get('DB_PASS'):
        print("Пароль БД не задан. Создайте в этой папке файл LOG_PATH.txt с строками:")
        print("  DB_HOST=localhost")
        print("  DB_PORT=5432")
        print("  DB_NAME=analyse_db")
        print("  DB_USER=postgres")
        print("  DB_PASS=ваш_пароль")
        print("либо задайте переменную окружения: export DB_PASS=ваш_пароль")
        sys.exit(1)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print("Приёмник сенсоров: слушаю {}:{}".format(host, port))

    def get_conn():
        c = psycopg2.connect(
            database=cfg['DB_NAME'],
            user=cfg['DB_USER'],
            password=cfg['DB_PASS'],
            host=cfg['DB_HOST'],
            port=cfg['DB_PORT']
        )
        c.autocommit = True
        return c

    conn_db = None
    while True:
        if conn_db is None:
            try:
                conn_db = get_conn()
            except Exception as e:
                print("Ошибка подключения к БД: {}".format(e))
                sys.exit(1)

        client, addr = server.accept()
        buf = b''
        try:
            while True:
                data = client.recv(4096)
                if not data:
                    break
                buf += data
                while b'\n' in buf or b';' in buf:
                    line, sep, rest = buf.partition(b'\n')
                    if sep:
                        buf = rest
                    else:
                        line, sep, rest = buf.partition(b';')
                        buf = rest + sep
                    line = line.decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    event = _parse_event(line)
                    if not event:
                        continue
                    if "_error" in event:
                        print("Событие отклонено: {} | payload='{}'".format(event["_error"], line[:200]))
                        continue

                    try:
                        sensor_id = _to_int(event.get("sensor_id") or event.get("id"))
                        pid = _to_int(event.get("pid"))
                        parent_pid = _to_int(event.get("parent_pid") or event.get("parent_id"))
                        run_id = _to_int(event.get("run_id"))
                        ts = _to_ts(event.get("ts") or event.get("time"))
                        host_name = event.get("host")
                        payload = json.dumps(event, ensure_ascii=False)

                        if sensor_id is None:
                            print("Событие отклонено: отсутствует sensor_id")
                            continue

                        cur = conn_db.cursor()
                        cur.execute(
                            """
                            INSERT INTO ccc_sensoragramma
                            (run_id, sensor_id, pid, parent_pid, ts, host, payload)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (run_id, sensor_id, pid, parent_pid, ts, host_name, payload),
                        )
                        cur.close()
                    except Exception as e:
                        print("Ошибка записи события: {}".format(e))
                        conn_db.close()
                        conn_db = None
                        break
        except Exception as e:
            print("Ошибка приёма: {}".format(e))
        finally:
            client.close()

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Приёмник сенсоров в БД')
    ap.add_argument('--port', type=int, default=17176)
    ap.add_argument('--bind', default='0.0.0.0')
    args = ap.parse_args()
    run_receiver(host=args.bind, port=args.port)
