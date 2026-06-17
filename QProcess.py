# -*- coding: utf-8 -*-
import finderCommentAndQuoatsInCppLineCode as finder
from dbFolder import *
import re

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

global id
id = 0

def pasteData(id_file, name, level, num_line, line): #Добавление данных в таблицу
    global cursor
    global id
    id += 1
    cursor.execute('''
    INSERT INTO ccc_qprocess
    VALUES (%s, %s, %s, %s, %s, %s)
    ''', (id, id_file, name, level, num_line, line))
    conn.commit()

DT = int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS ccc_qprocess''')
    cursor.execute('''
        CREATE TABLE ccc_qprocess(
        	ID	            INTEGER NOT NULL PRIMARY KEY,
        	id_file	        INTEGER,
            name            TEXT,
            level           INTEGER,
            num_line        INTEGER,
            line            TEXT);
    ''')
    conn.commit()

cursor.execute('SELECT id_file, path, name_rash, encoding FROM ccc_file_list ORDER BY id_file ASC')
data = cursor.fetchall()

flag_m_comment = False
flag = False
ignoge = False
line_obj = 0
cut = re.compile('[^\s;]+')

save_index = -1

chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])
if chek_search_File_ID != 0 and DT != 1:
    cursor.execute('''
        DELETE FROM ccc_qprocess
        WHERE id_file >= {0}
    '''.format(chek_search_File_ID))
    conn.commit()

for file in data:
    code_line = 0
    if chek_search_File_ID != 0 and file_id < chek_search_File_ID:
            continue
    with open(file[1], encoding=file[3]) as f:
        # print('Open\t{0}:\t{1}'.format(file[0], file[1]))
        level = 0
        flag = False
        for line in f:
            # #print('\nLine {0}:\t{1}'.format(code_line, line), end='')
            save_index = 0
            code_line += 1
            if flag_m_comment:
                if '*/' in line:
                    flag_m_comment = False
                    end_m_comment = line.find('*/')
                    string = line[end_m_comment + 2:]
                    comments = finder.findComments(string)
            else:
                end_m_comment = 0
                comments = finder.findComments(line)
                string = line

            if '/*' in string:
                comments = finder.findComments(string)
                if comments['many_line_comments']:
                    if comments['many_line_comments'][-1][1] == -1:
                        flag_m_comment = True

            string = finder.cleaner(comments, string)
            comments = finder.findComments(line)
            words = cut.findall(string)

            for word in words:
                if flag:
                    flag = False
                    if word in ['const', '*const', '*', 'const*']:
                        flag = True
                        continue
                    pasteData(file[0], word.strip('*'), level, code_line, line)
                elif word == '{':
                    level += 1
                elif word == '}':
                    level -= 1
                elif word == 'QProcess':
                    print(line)
                    flag = True

conn.commit()
conn.close()
