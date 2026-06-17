# -*- coding: utf-8 -*-
from dbFolder import *
import finderCommentAndQuoatsInCppLineCode as finder
import find_files
import re

def pasteData(ID, IDfunc, name, from_, useIn, lineID, line):#Добавление данных в таблицу
    global cursor
    flag = True
    ID_ = ID
    while flag:
        try:
            cursor.execute('''
            INSERT INTO ccc_use_function_list
            VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (ID_, IDfunc, name, from_, useIn, lineID, line))
            conn.commit()
            print(ID_, IDfunc, name, from_, useIn, lineID, line)
        except Exception:
            ID_ += 1
            print("Error")
            continue
        finally:
            flag = False

global cursor
conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

DT=int(folder['DROP_TBL'])
if DT == 1:
    # cursor.execute('''DROP TABLE IF EXISTS ccc_use_function_list CASCADE''')
    # cursor.execute('''
    # CREATE TABLE ccc_use_function_list(
    # 	ID	    INTEGER NOT NULL PRIMARY KEY,
    #     IDfunc    INTEGER,
    #     name      TEXT,
    #     from_	    INTEGER,
    #     useIn     INTEGER,
    #     lineID    INTEGER,
    # 	line	    TEXT);
    # ''')

    cursor.execute('''DROP VIEW IF EXISTS ccc_where_use_function_V2''')
    cursor.execute('''
    CREATE VIEW ccc_where_use_function_V2 AS
    SELECT ccc_use_function_list.idfunc, ccc_use_function_list.name, ccc_definition_function.file_id, ccc_definition_function.idfunc UseInFuncID
    FROM ccc_use_function_list, ccc_definition_function
    WHERE (ccc_use_function_list.useIn = ccc_definition_function.file_id)
        AND (ccc_definition_function.start_line <= ccc_use_function_list.lineID)
        AND (ccc_definition_function.end_line >= ccc_use_function_list.lineID)
    ''')

   # conn.commit()

    cursor.execute('''DROP VIEW IF EXISTS ccc_not_use_function''')
    cursor.execute('''
    CREATE VIEW ccc_not_use_function AS
    SELECT ccc_definition_function.idfunc, ccc_definition_function.name, ccc_definition_function.file_id
    FROM ccc_definition_function
    WHERE ccc_definition_function.idfunc NOT IN (
    SELECT ccc_use_function_list.idfunc FROM ccc_use_function_list
    ) AND ccc_definition_function.name != 'main' AND strpos(ccc_definition_function.name, 'operator') = 0
    ''')

    conn.commit()

cursor.execute("SELECT id_file, path, encoding FROM ccc_file_list")
data = cursor.fetchall()


func_data =         []
connected_files =   []
flag_m_comment =    False
ID =                328
code_line =         0
words = re.compile('[A-Za-z_0-9]+|[\(&=]')
cursor.execute('''SELECT idfunc, name, line_detect, file_id FROM ccc_definition_function''')
func_data = cursor.fetchall()

for file in data:
    with open(file[1], encoding=file[2]) as f:
        print('Open {0}: {1}'.format(file[0], file[1]))
        code_line = 0
        # if file[0] != 7:
        #     continue
        for line in f:
            code_line += 1

            if flag_m_comment:
                if '*/' in line:
                    flag_m_comment = False
                    end_m_comment = line.find('*/')
                    string = line[end_m_comment + 2:]
                    comments = finder.findComments(string)
                else:
                    continue
            else:
                if line.split():
                    if line.split()[0][0] == '#':
                        continue
                end_m_comment = 0
                comments = finder.findComments(line)
                string = line

            if '/*' in string:
                comments = finder.findComments(string)
                if comments['many_line_comments']:
                    if comments['many_line_comments'][-1][1] == -1:
                        flag_m_comment = True

            words_ = words.findall(finder.cleaner(comments, string))
            # if file[0] == 7:
            #     print('Line\t', code_line, ': ', words_)
            for func in func_data:
                try:
                    if '::' in func[1]:
                        if func[3] != file[0]:
                            if func[1][func[1].rfind('::'):] in words_:
                                if words_[words_.index(func[1][func[1].rfind('::') + 2:]) + 1] == '(':
                                    ID += 1
                                    pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)

                        elif func[2] != code_line:
                            if func[1][func[1].rfind('::'):] in words_:
                                if words_[words_.index(func[1][func[1].rfind('::') + 2:]) + 1] == '(':
                                    ID += 1
                                    pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                    else:
                        if func[3] != file[0]:
                            if func[1] in words_:
                                if (words_[words_.index(func[1]) + 1] == '('):
                                    ID += 1
                                    pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                        elif func[2] != code_line:
                            #if func[1] == 'DynamicGetRuleData':
                            #print(func[1], func[1] in words_)
                            # print(func[1], len(words_[3]), len(func[1]))
                            if (func[1] in words_):
                                # print('+++++++++++++++++++++')
                                # print(words_[words_.index(func[1]) - 1] == '&')
                                if (words_[words_.index(func[1]) + 1] == '('):
                                    # print('-----------------------------------')
                                    ID += 1
                                    pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                except Exception as s:
                    if str(s) != 'list index out of range':
                        print(s)
                    continue
            for i in '&=':
                for func in func_data:
                    try:
                        if '::' in func[1]:
                            if func[3] != file[0]:
                                if func[1][func[1].rfind('::'):] in words_:
                                    if words_[words_.index(func[1][func[1].rfind('::') + 2:]) - 1] == i:
                                        ID += 1
                                        pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                            elif func[2] != code_line:
                                if func[1][func[1].rfind('::'):] in words_:
                                    if words_[words_.index(func[1][func[1].rfind('::') + 2:]) - 1] == i:
                                        ID += 1
                                        pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                        else:
                            if func[3] != file[0]:
                                if func[1] in words_:
                                    if (words_[words_.index(func[1]) - 1] == i):
                                        ID += 1
                                        pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                            elif func[2] != code_line:
                                #if func[1] == 'DynamicGetRuleData':
                                #print(func[1], func[1] in words_)
                                # print(func[1], len(words_[3]), len(func[1]))
                                if (func[1] in words_):
                                    # print('+++++++++++++++++++++')
                                    # print(words_[words_.index(func[1]) - 1] == '&')
                                    if (words_[words_.index(func[1]) - 1] == i):
                                        # print('-----------------------------------')
                                        ID += 1
                                        pasteData(ID, func[0], func[1], func[3], file[0], code_line, line)
                    except Exception as s:
                        if str(s) != 'list index out of range':
                            print(s)
                        continue

conn.commit()
