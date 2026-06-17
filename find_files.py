import os
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import psycopg2

from dbFolder import folder

DEFAULT_DB = 'result.db'
#создание таблицы в БД
def searchEncoding(path):
    encoding = [# сюда можно впихнуть все известные кодировки.
    'utf-8',
    'koi8-r',
    'cp500',
    'utf-16',
    'GBK',
    'windows-1251',
    'ASCII',
    'US-ASCII',
    'Big5']

    correct_encoding = ''

    for enc in encoding:
        try:
            open(path, encoding=enc).read()
        except (UnicodeDecodeError, LookupError):
            pass
        else:
            correct_encoding = enc
            #print('Done!')
            break


    return correct_encoding
def _get_extensions_from_config(cfg) -> Set[str]:
    exts = (cfg.get("FILE_EXTENSION") or "").split()
    if not exts:
        exts = ["c", "cc", "cpp", "h", "hpp", "inl", "H", "C", "CPP", "HPP"]
    out = set()
    for e in exts:
        e = e.strip().lstrip(".")
        if e:
            out.add(e.lower())
    return out


def _looks_like_qt_stub(path: Path) -> bool:
    """Qt иногда генерирует C-файлы без расширения с 1 строкой #include."""
    try:
        with path.open("r", encoding=searchEncoding(str(path)) or "utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i > 1:
                    return False
                if "#include" in line:
                    return True
    except Exception:
        return False
    return False


def collect_source_files(root_dir: str, extensions: Set[str]) -> List[Tuple[str, str, str]]:
    """
    Сбор файлов исходников без записи в БД.
    Возвращает список: (abs_path, stem_name, name_rash).
    """
    root = Path(root_dir)
    if not root.exists() or not root.is_dir():
        return []

    files = []
    scanned = 0
    for p in root.rglob("*"):
        scanned += 1
        if scanned % 8000 == 0:
            try:
                print(
                    "find_files: обход каталога… проверено путей: {}, отобрано исходников: {}".format(
                        scanned, len(files)
                    ),
                    flush=True,
                )
            except Exception:
                pass
        try:
            if not p.is_file():
                continue
            # Пропускаем симлинки
            if p.is_symlink():
                continue
            suffix = p.suffix.lstrip(".")
            if suffix:
                if suffix.lower() not in extensions:
                    continue
                name_rash = p.name
                stem = p.stem
                files.append((str(p.resolve()), stem, name_rash))
            else:
                # Файл без расширения: принимаем только Qt-stub с #include
                if _looks_like_qt_stub(p):
                    files.append((str(p.resolve()), p.name, p.name))
        except Exception:
            continue
    return files


def create_table_files(conn, drop_tbl: bool = True):
    cur = conn.cursor()
    if drop_tbl:
        cur.execute("DROP TABLE IF EXISTS ccc_file_list CASCADE")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ccc_file_list (
            id_file int PRIMARY KEY NOT NULL,
            name text,
            name_rash text,
            path text,
            sourse_or_lib text,
            encoding TEXT
        )
        """
    )
    if not drop_tbl:
        try:
            cur.execute("TRUNCATE TABLE ccc_file_list")
        except Exception:
            pass
    conn.commit()

def save_files(conn, files: Iterable[Tuple[str, str, str]], typef: str = "sourse", start_id: int = 1) -> int:
    """
    Сохраняет файлы в ccc_file_list. Возвращает количество вставленных записей.
    files: (abs_path, stem_name, name_rash)
    """
    cur = conn.cursor()
    inserted = 0
    file_id = start_id
    try:
        total_files = len(files)
    except Exception:
        total_files = 0
    for idx, (abs_path, stem, name_rash) in enumerate(files, start=1):
        if idx == 1 or idx % 25 == 0 or idx == total_files:
            try:
                print(
                    "find_files: запись в БД… {}/{} (id_file≈{})".format(idx, total_files or "?", file_id),
                    flush=True,
                )
            except Exception:
                pass
        enc = searchEncoding(abs_path)
        cur.execute(
            """
            INSERT INTO ccc_file_list (id_file, name, path, name_rash, sourse_or_lib, encoding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (file_id, stem, abs_path, name_rash, typef, enc),
        )
        inserted += 1
        file_id += 1
    conn.commit()
    return inserted


def run(project_root: Optional[str] = None):
    project_root = project_root or (folder.get("PATH_FILE") or "").strip()
    print("find_files: run()", flush=True)
    print("find_files: PATH_FILE = {}".format(project_root), flush=True)
    exts = _get_extensions_from_config(folder)
    print("find_files: сбор списка файлов (обход дерева, может занять время)…", flush=True)
    files = collect_source_files(project_root, exts)
    print("find_files: найдено файлов: {}".format(len(files)), flush=True)
    max_files_raw = (folder.get("MAX_FILES") or "").strip()
    if max_files_raw:
        try:
            max_files = int(max_files_raw)
            if max_files > 0 and len(files) > max_files:
                print(
                    "find_files: smoke-режим MAX_FILES={} — будет обработано только первых {} из {}.".format(
                        max_files, max_files, len(files)
                    ),
                    flush=True,
                )
                files = files[:max_files]
        except Exception:
            print("find_files: MAX_FILES='{}' не число, ограничение игнорировано.".format(max_files_raw), flush=True)

    conn = psycopg2.connect(
        database=folder["DB_NAME"],
        user=folder["DB_USER"],
        password=folder["DB_PASS"],
        host=folder["DB_HOST"],
        port=folder["DB_PORT"],
        connect_timeout=30,
    )
    drop_tbl = int(folder.get("DROP_TBL", "0") or "0") == 1
    create_table_files(conn, drop_tbl=drop_tbl)
    print("find_files: определение кодировок и INSERT в ccc_file_list (долго на больших проектах)…", flush=True)
    save_files(conn, files, typef="sourse", start_id=1)
    conn.close()
    print("find_files: запись в БД завершена.", flush=True)
    return len(files)

def insert_in_db(Flist, typef="sourse", db_name = DEFAULT_DB):
    #conn = sqlite3.connect(db_name)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    for i in Flist:
        cur.execute('INSERT INTO ccc_file_list VALUES (%s, %s, %s, %s)', (i[0],i[1],i[2], typef))
    conn.commit()
    conn.close()
def len_files_for_type(typ = 'sourse', db=DEFAULT_DB):
    #conn = sqlite3.connect(db)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select count(*) from ccc_file_list where sourse_or_lib = '{}'".format(typ))
    l = cur.fetchone()
    return l[0]
def get_file_path(db_name = DEFAULT_DB):
    #conn = sqlite3.connect(db_name)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select path, encoding, id_file from ccc_file_list order by id_file asc")
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append([i[0], i[1], i[2]])
    return list

def get_file_name_path(db_name = DEFAULT_DB):
    #conn = sqlite3.connect(db_name)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select name , path from ccc_file_list where sourse_or_lib = 'sourse'")
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i)
    return list

def get_file_name_rash(db_name = DEFAULT_DB): # функция для скрипта по поиску связуй "файл-файл"
   # conn = sqlite3.connect(db_name)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select name_rash , path from ccc_file_list where sourse_or_lib = 'sourse'")
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i)
    return list

def get_file_fath_for_func(identificatio, db_name = DEFAULT_DB):
    #conn = sqlite3.connect(db_name)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select path from ccc_file_list where id_file = '{}'".format(identificatio))
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i[0])
    #print(identificatio)
    return list

def search_f(path):
    if not os.path.isdir(path):
        return 0
    return run(path)
if __name__=='__main__':
    print("find_files: __main__ старт", flush=True)
    run(folder.get('PATH_FILE'))
##    list_f=get_file_path()
##    for path in enumerate(list_f, start=1):
##        print(path)
    #list = get_file_name_path()
    #print(list[0][1])
    #print(list[1])
    #insert_in_db(run(folder=r'D:\Work_anal_java'))
    #IDD = 3
    #print(get_file_fath_for_func(IDD))
