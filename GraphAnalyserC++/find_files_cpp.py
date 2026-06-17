#!/usr/bin/env python3
import os

def create_tables(con, cur):
    """
    ТОЧНАЯ КОПИЯ find_files.create_tables() из Python анализатора
    Создает таблицу для хранения путей к файлам C++
    """
    print('find_files_cpp.create_tables is start')
    
    cur.execute('''DROP TABLE IF EXISTS cpp_files''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cpp_files
        (id SERIAL,
        path TEXT,
        size INT);''')
    con.commit()


def find_file(files, path, con, cur, progress_callback=None, _total=None):
    """
    Находит все C++ файлы в указанной директории (рекурсивно).
    progress_callback(count, file_path) вызывается каждые 500 файлов для отображения прогресса.
    """
    if _total is None:
        _total = [0]
    count = 0
    for file in files:
        file_path = os.path.join(path, file)
        if os.path.isfile(file_path):
            if file.endswith(('.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx')):
                count += 1
                _total[0] += 1
                size = os.path.getsize(file_path)
                cur.execute("INSERT INTO cpp_files (path, size) VALUES (%s, %s)", (file_path, size))
                if progress_callback and _total[0] % 500 == 0:
                    try:
                        progress_callback(_total[0], file_path)
                    except Exception:
                        pass
        elif os.path.isdir(file_path):
            count += find_file(
                os.listdir(file_path), file_path, con, cur,
                progress_callback=progress_callback, _total=_total,
            )
    con.commit()
    return count

