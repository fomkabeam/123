import finderCommentAndQuoatsInCppLineCode as finder
from dbFolder import *
import re

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

def pasteData(id, id_file, qoutes, num_line, line): #Добавление данных в таблицу
    global cursor
    cursor.execute('''
    INSERT INTO ccc_start_qprocess
    VALUES (%s, %s, %s, %s, %s)
    ''', (id, id_file, qoutes, num_line, line))
    conn.commit()

DT = int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS ccc_start_qprocess''')
    cursor.execute('''
        CREATE TABLE ccc_start_qprocess(
        	ID_var	            INTEGER,
        	id_file	        INTEGER,
            qoutes          TEXT,
            num_line        INTEGER,
            line            TEXT);
    ''')
    conn.commit()

cursor.execute('SELECT id_file, path, name_rash, encoding FROM ccc_file_list ORDER BY id_file ASC')
data = cursor.fetchall()

flag_m_comment = False
flag = False
cut = re.compile('[^\s;\.]+')

save_index = -1

chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])
if chek_search_File_ID != 0 and DT != 1:
    cursor.execute('''
        DELETE FROM ccc_start_qprocess
        WHERE id_file >= {0}
    '''.format(chek_search_File_ID))
    conn.commit()

for file in data:
    code_line = 0
    if chek_search_File_ID != 0 and file_id < chek_search_File_ID:
            continue
    with open(file[1], encoding=file[3]) as f:
        print('Open\t{0}:\t{1}'.format(file[0], file[1]))
        level = 0
        flag = False
        vars = []
        cursor.execute('''
            SELECT name, level, num_line, id FROM ccc_qprocess
            WHERE id_file = {0}
        '''.format(file[0]))
        for var in cursor.fetchall():
            if var[1] != 0:
                vars.append({
                    'id'       : var[3],
                    'name'     : var[0],
                    'level'    : var[1],
                    'num_line' : var[2],
                    'active'   : 0
                })
            else:
                vars.append({
                    'id'       : var[3],
                    'name'     : var[0],
                    'level'    : var[1],
                    'num_line' : var[2],
                    'active'   : 1
                })
        if vars == []:
            continue
        for line in f:
            print('\nLine {0}:\t{1}'.format(code_line, line), end='')
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

            for var in vars:
                if code_line >= var['num_line'] and var['active'] == 0:
                    var['active'] = 1

            for word in words:
                if word == '{':
                    level += 1
                elif word == '}':
                    level -= 1
                    for var in vars:
                        if var['active'] == 1 and var['level'] < level:
                            var['active'] = 2
                            print(vars)

            for var in vars:
                if var['active'] == 1 and (var['name'] + '.start') in string:
                    print(line)
                    index = finder.searching(comments, var['name'] + '.start', line, end_m_comment) + len(var['name'] + '.start')
                    if comments['quotes']:
                        for quotes in comments['quotes']:
                            if quotes[0] > index:
                                pasteData(var['id'], file[0], line[quotes[0] + 1:quotes[1]], code_line, line)
                                break
