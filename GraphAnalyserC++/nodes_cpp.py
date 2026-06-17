#!/usr/bin/env python3
import os
import sys
import psycopg2

# Добавляем родительскую папку в sys.path для импорта structures
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import find_files_cpp
import find_nodes_cpp
import create_graph_cpp
import set_block_id_cpp
import find_func_cpp

def menu():
    """
    ТОЧНАЯ КОПИЯ menu() из nodes.py
    Меню для работы с C++ анализатором
    """
    while True:
        print('|-----------------------------------------Menu------------------------------------------|')
        print('| 1. Найти все файлы C++ в указанной директории                                         |')
        print('| 2. Найти все узлы и связи между ними во всех файлах                                   |')
        print('| 3. Создать деревья всех файлов и открыть их для просмотра                             |')
        print('| 4. Заполнить данными объект граф                                                       |')
        print('| 5. Определить области видимости всех узлов                                             |')
        print('| 6. Скрепить деревья на основании включенных файлов                                     |')
        print('|(не используйте данную функцию если добавляете связь между включенными файлами вручную)|')
        print('| 7. Заполнить новыми данными объект граф и определить вложенность областей видимости    |')
        print('| 8. Найти все определения и вызовы функций и связать их                                 |')
        print('| 9. Запустить файл добавления связей вручную                                            |')
        print('| 10. Создать граф                                                                       |')
        print('| 0. Выход                                                                               |')
        print('|---------------------------------------------------------------------------------------|')
        choose = int(input('Выберите функцию из списка: '))

        if choose == 1:
            find_files_cpp.create_tables(con, cur)
            count_files = find_files_cpp.find_file(os.listdir(path), path, con, cur)
            print('Найдено файлов: {}'.format(count_files))
            
        elif choose == 2:
            find_nodes_cpp.create_tables(con, cur)
            find_nodes_cpp.find_nodes(con, cur)
            
        elif choose == 3:
            # Получаем количество файлов из БД
            if 'count_files' not in locals():
                cur.execute("SELECT COUNT(*) FROM cpp_files")
                count_files = cur.fetchone()[0]
            create_graph_cpp.create_graph(con, cur, graph, count_files)
            
        elif choose == 4:
            # Получаем количество файлов из БД
            if 'count_files' not in locals():
                cur.execute("SELECT COUNT(*) FROM cpp_files")
                count_files = cur.fetchone()[0]
            gr = create_graph_cpp.fill_graph(count_files, cur)
            print('Граф создан!')
            
        elif choose == 5:
            # Получаем количество файлов из БД
            if 'count_files' not in locals():
                cur.execute("SELECT COUNT(*) FROM cpp_files")
                count_files = cur.fetchone()[0]
            # Инициализация графа если ещё не создан
            if 'gr' not in locals():
                print("Creating graph...")
                gr = create_graph_cpp.fill_graph(count_files, cur)
            set_block_id_cpp.create_tables(con, cur)
            set_block_id_cpp.set_block_id(gr, cur, con, count_files)
            print('Области видимости определены!')
            
        elif choose == 6:
            # Инициализация графа если ещё не создан
            if 'gr' not in locals():
                print("Creating graph...")
                if 'count_files' not in locals():
                    cur.execute("SELECT COUNT(*) FROM cpp_files")
                    count_files = cur.fetchone()[0]
                gr = create_graph_cpp.fill_graph(count_files, cur)
            gr = create_graph_cpp.find_module_by_import(gr, cur, con)
            print('Деревья скреплены!')
            
        elif choose == 7:
            # Получаем количество файлов из БД
            if 'count_files' not in locals():
                cur.execute("SELECT COUNT(*) FROM cpp_files")
                count_files = cur.fetchone()[0]
            gr = create_graph_cpp.fill_graph(count_files, cur)
            set_block_id_cpp.nesting_blocks(gr, con, cur)
            print('Вложенность областей видимости определена!')
            
        elif choose == 8:
            # Инициализация графа если ещё не создан
            if 'gr' not in locals():
                print("Creating graph...")
                if 'count_files' not in locals():
                    cur.execute("SELECT COUNT(*) FROM cpp_files")
                    count_files = cur.fetchone()[0]
                gr = create_graph_cpp.fill_graph(count_files, cur)
            find_func_cpp.create_tables(con, cur)
            find_func_cpp.find_functions(gr, cur, con)
            find_func_cpp.find_functions_calls(gr, cur, con)
            gr = find_func_cpp.find_func_call_connection(gr, cur, con)
            print('Вызовы функций связаны с определениями!')
            
        elif choose == 9:
            print('Функция пока не реализована для C++')
            # TODO: адаптировать add_edge_to_graph для C++
            
        elif choose == 10:
            # Инициализация графа если ещё не создан
            if 'gr' not in locals():
                print("Creating graph...")
                if 'count_files' not in locals():
                    cur.execute("SELECT COUNT(*) FROM cpp_files")
                    count_files = cur.fetchone()[0]
                gr = create_graph_cpp.fill_graph(count_files, cur)
            create_graph_cpp.create_full_graph(gr, graph)
            
        elif choose == 0:
            return
        else:
            return


# Настройка подключения к БД
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.txt')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    _proj = f.readline().rstrip()
    DB_NAME = f.readline().rstrip()
    DB_USER = f.readline().rstrip()
    DB_PASS = f.readline().rstrip()
    DB_HOST = f.readline().rstrip()
    DB_PORT = f.readline().rstrip()

# ПУТЬ К C++ ПРОЕКТУ (измените на свой путь)
PATH_DIR = r"C:\Users\Alexey\Desktop\CD2\crc16\crc16"

path = PATH_DIR
con = psycopg2.connect(
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)
graph = None
cur = con.cursor()

if __name__ == '__main__':
    menu()

