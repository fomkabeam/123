# -*- coding: utf-8 -*-
##define что <на что>
import finderCommentAndQuoatsInCppLineCode as finder
import find_files
from dbFolder import *

def pasteData(ID, id_file, defined, inted, line): #Занесение данных в таблицу
    global cursor
    cursor.execute('''
    INSERT INTO ccc_defind_list
    VALUES (%s, %s, %s, %s, %s)
    ''', (ID, id_file, defined, inted, line))
    conn.commit()

# find_files.create_table_files()
# find_files.run(folder['PATH_FILE'])

global cursor
conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

DT=int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS ccc_defind_list''') #Создание таблицы
    cursor.execute('''
        CREATE TABLE ccc_defind_list(
        ID INTEGER,
        id_file INTEGER,
        defined TEXT,
        inted TEXT,
        line TEXT);
    ''')
    conn.commit()

cursor.execute("SELECT id_file, path, name_rash, encoding FROM ccc_file_list")
data = cursor.fetchall()

ID =            1
define_flag =   False
inted_flag =    False
define =        ''
inted =         ''
temp_string =   '' #Для фрмирования строки с переносами
words = []
chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])
for i in data:
    if chek_search_File_ID !=0 and file_id < chek_search_File_ID:
            continue
    with open(i[1], encoding=i[3]) as f:
        for line in f:
            if define_flag or inted_flag: #Если был перенос
                comments = finder.findComments(line)
                string = finder.cleanerWithoutQuotes(comments, line)
                if define_flag: #Поиск имён и оставшихся переносов
                    if '\\' not in string:
                        define_flag = False
                        define += string.split()[0]
                        pasteData(ID, i[0], define, string[string.find(string.split()[0]) + len(string.split()[0]) + 1:], temp_string + line)
                        define =        ''
                        inted =         ''
                        ID += 1
                        temp_string = ''
                    else:
                        if len(string.split()) > 1:
                            define_flag = False
                            define += string.split()[0]
                            inted = string[string.find(string.split()[0]) + len(string.split()[0]) + 1: -1]
                            inted_flag = True
                        else:
                            define += string[:-1]
                        temp_string += line
                    continue
                if inted_flag:
                    if '\\' not in string:
                        inted += string
                        inted_flag = False
                        pasteData(ID, i[0], define, inted, temp_string + line)
                        define =        ''
                        inted =         ''
                        ID += 1
                        temp_string = ''
                    else:
                        inted += string[:-1]
                        temp_string += line
                    continue

            if line.find('define') != -1:
                comments = finder.findComments(line)
                string = finder.cleaner(comments, line)
                if ('define' in string) and ('#' in string):
                    if ('\\' not in string):
                        if (len(string.split()) < 3): #Предопределённые замены
                            continue
                        string = finder.cleanerWithoutQuotes(comments, line)
                        pasteData(ID, i[0], string.split()[1], string[string.find(string.split()[1]) + len(string.split()[1]) + 1:], line)
                        ID += 1
                        temp_string = ''
                    else:
                        temp_string = line
                        words = string.split()
                        if len(words) <= 2:
                            if words[0][-1] == '\\':
                                define_flag = True
                            elif len(words) > 1:
                                if words[1] == '\\':
                                    define_flag = True
                                else:
                                    define = words[1][:-1]
                                    define_flag = True
                            continue
                        else:
                            define = words[1]
                            inted = string[string.find(define) + len(define) + 1:-1]
                            inted_flag = True

conn.commit()
