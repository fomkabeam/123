# -*- coding: utf-8 -*-
"""
Вставка сенсора на вход в функцию (один SENSOR(id); после '{' тела).
Защиты (не удалять):
  - Вставка только после '{' после ')' (тело функции), не в brace-init {a,b}.
  - Не вставляем в комментарии (//, /* */) — _is_in_comment_block.
  - Не вставляем, если рядом уже есть SENSOR — _has_sensor_nearby.
  - Один сенсор на функцию — inserted_functions set.
  - Не вставляем в пустое тело '{}', не вставляем если следующая строка уже с SENSOR.
"""
import find_files
from dbFolder import *
import finderCommentAndQuoatsInCppLineCode as finder
from shutil import copytree
from sys import exit

global cursor

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

cursor.execute("SELECT id_file, path, encoding FROM ccc_file_list")
data = cursor.fetchall()

def findSensor(line, index):
    return finder.searching(finder.findComments(line), 'sensor(', index)

def getData(id_file, conn):
    cursor = conn.cursor()
    main_data = []
    cursor.execute('''SELECT idfunc, name, start_line, start_pos
                   FROM ccc_definition_function
                   WHERE file_id = {0}
                   GROUP BY start_line, idfunc, name, start_pos'''.format(id_file))
    for j in cursor.fetchall():
        main_data.append([j[0], j[1], j[2], j[3]])
    print(main_data)
    return main_data

def pasteSensFunc(path, data): #Вместо поиска ключевых слов в случае отсутсвия блока
                           #можно искать команду которая относится к этому блоку
    print(path, data)
    maybe = 1
    with open(path[1][0], encoding=path[1][1]) as f:
        file = f.read()
    if 'УЦП-ОА' in path[1][0] or 'самотестирование' in path[1][0]:
        pastedSens = 'SendMSG({0});'
    elif 'УЦП-П' in path[1][0]:
        pastedSens = 'Time_a({0});'
    else:
        file = '#include "' + folder['PID_SEARCH_PATH'] +'"\n' + file
        maybe = 0
        pastedSens = 'SENSOR({0});'


    file = file.split('\n')
    print(data)

    def _prev_nonspace_char(s, idx):
        j = idx
        while j >= 0 and s[j].isspace():
            j -= 1
        return s[j] if j >= 0 else ''

    def _is_in_comment_block(lines, line_idx):
        """Проверка, находится ли строка внутри блока комментариев /* ... */ или закомментирована //."""
        if line_idx >= len(lines):
            return False
        
        # Проверяем текущую строку
        s = lines[line_idx]
        stripped = s.strip()
        # Строка полностью закомментирована
        if stripped.startswith('//') or stripped.startswith('/*') or (stripped.startswith('*') and not stripped.startswith('*(')):
            return True
        
        # Проверяем, не находимся ли мы внутри блока /* ... */
        in_block_comment = False
        for check_idx in range(max(0, line_idx - 10), line_idx + 1):
            if check_idx >= len(lines):
                continue
            check_line = lines[check_idx]
            # Ищем начало блока комментария
            if '/*' in check_line:
                comment_start = check_line.find('/*')
                comment_end = check_line.find('*/', comment_start)
                if comment_end == -1:
                    # Блок начался и не закрыт в этой строке
                    in_block_comment = True
                elif comment_end > comment_start:
                    # Блок закрыт в этой строке
                    in_block_comment = False
            # Проверяем закрытие блока в текущей строке
            if in_block_comment and '*/' in check_line:
                in_block_comment = False
        
        return in_block_comment

    def _has_sensor_nearby(lines, line_idx, max_distance=3):
        """Проверка, есть ли SENSOR в ближайших строках (чтобы не вставлять дважды)."""
        for check_idx in range(max(0, line_idx - max_distance), min(len(lines), line_idx + max_distance + 1)):
            if 'SENSOR(' in lines[check_idx]:
                return True
        return False

    def _try_insert_after_function_brace(lines, start_line_1based, start_pos_1based, sensor_stmt):
        """
        Вставка сенсора как отдельного statement сразу после '{' тела функции.
        Важно: игнорируем '{' у brace-init (например new T({a,b})) — там перед '{' обычно не ')'.
        """
        if start_line_1based is None:
            return False
        i = int(start_line_1based) - 1
        if i < 0 or i >= len(lines):
            return False

        # Проверка: не вставляем в закомментированный код
        if _is_in_comment_block(lines, i):
            return False

        # Проверка: не вставляем, если рядом уже есть SENSOR
        if _has_sensor_nearby(lines, i):
            return False

        # начинаем поиск с указанной позиции в строке start_line
        pos0 = max(int(start_pos_1based) - 1, 0) if start_pos_1based is not None else 0

        # ограничим поиск, чтобы не блуждать по файлу
        max_lines_to_scan = 30
        scanned = 0
        while i < len(lines) and scanned < max_lines_to_scan:
            s = lines[i]
            # Пропускаем закомментированные строки
            stripped = s.strip()
            if stripped.startswith('//') or stripped.startswith('/*') or (stripped.startswith('*') and not stripped.startswith('*(')):
                i += 1
                scanned += 1
                continue
                
            start_at = pos0 if scanned == 0 else 0
            idx = s.find('{', start_at)
            while idx != -1:
                # Проверка: '{' не должен быть внутри комментария
                before_brace = s[:idx]
                if '//' in before_brace:
                    comment_pos = before_brace.rfind('//')
                    if comment_pos > before_brace.rfind('"') or before_brace.rfind('"') == -1:
                        idx = s.find('{', idx + 1)
                        continue
                
                # эвристика: '{' функции обычно идет после ')'
                prev_ch = _prev_nonspace_char(s, idx - 1)
                if prev_ch == ')':
                    # Дополнительная проверка: после '{' не должно быть сразу '}' (пустое тело)
                    after_brace = s[idx + 1:].strip()
                    if after_brace.startswith('}'):
                        idx = s.find('{', idx + 1)
                        continue
                    
                    # Проверка: не вставляем в строку, которая содержит только '{' и пробелы/комментарии
                    if stripped == '{' or (stripped.startswith('{') and '//' in stripped):
                        idx = s.find('{', idx + 1)
                        continue
                    
                    # Проверка: следующая строка не должна уже содержать SENSOR
                    if i + 1 < len(lines) and 'SENSOR(' in lines[i + 1]:
                        idx = s.find('{', idx + 1)
                        continue
                    
                    # вставим после '{' с переносом строки и отступом
                    indent = ''
                    # отступ берём как отступ следующей строки, если она есть, иначе текущей
                    if i + 1 < len(lines):
                        nxt = lines[i + 1]
                        indent = nxt[:len(nxt) - len(nxt.lstrip())]
                    else:
                        indent = s[:len(s) - len(s.lstrip())] + '    '

                    insertion = '\n' + indent + sensor_stmt
                    lines[i] = s[:idx + 1] + insertion + s[idx + 1:]
                    return True

                # ищем следующий '{' в этой же строке
                idx = s.find('{', idx + 1)

            i += 1
            scanned += 1
        return False

    # Вставляем сенсоры безопасно: только как statement после '{' тела функции
    inserted_functions = set()  # чтобы не вставлять дважды в одну функцию
    for i in data:
        func_key = (i[2], i[3])  # (start_line, start_pos) как ключ функции
        if func_key in inserted_functions:
            continue
        insert = i[0] + 500000
        sensor_stmt = pastedSens.format(insert)
        if _try_insert_after_function_brace(file, i[2], i[3], sensor_stmt):
            inserted_functions.add(func_key)


    with open(path[1][0], 'w') as f:
        for i in file:
            f.write(i + '\n')

if __name__ == '__main__':
    for i in data:
        main_data = []
        cur.execute('''SELECT idfunc, name, start_line, start_pos
                       FROM ccc_definition_function
                       WHERE file_id = {0}
                       GROUP BY idfunc, name, start_line, start_pos'''.format(id_file))
        for j in cur.fetchall():
            main_data.append([j[0], j[1], j[2], j[3]])
        pasteSensFunc(i, main_data)
        main_data = []

    conn.commit()
    conn.close()
