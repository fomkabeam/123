# -*- coding: utf-8 -*-
from dbFolder import *
import finderCommentAndQuoatsInCppLineCode as finder
import find_files

def pasteData(ID, IDfunc, name, from_, useIn, lineID, line):#Добавление данных в таблицу
    global cursor
    try:
        cursor.execute('''
        INSERT INTO ccc_use_function_list
        VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (ID, IDfunc, name, from_, useIn, lineID, line))
        conn.commit()
    except sql.IntegrityError:
        print(ID, IDfunc, name, from_, useIn, lineID, line)

def searchConnectTree(id_file):
    global cursor
    global connected_files

    cursor.execute('SELECT id_file FROM ccc_connect_list WHERE connectToID = {0}'.format(id_file))

    for i in cursor.fetchall():
        if i[0] not in connected_files:
            connected_files.append(i[0])
            searchConnectTree(i[0])


# find_files.create_table_files()
# find_files.run(folder['PATH_FILE'])

global cursor
conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

DT=int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS ccc_use_function_list CASCADE''')
    cursor.execute('''
    CREATE TABLE ccc_use_function_list(
    	ID	    INTEGER NOT NULL PRIMARY KEY,
        IDfunc    INTEGER,
        name      TEXT,
        from_	    INTEGER,
        useIn     INTEGER,
        lineID    INTEGER,
    	line	    TEXT);
    ''')

    cursor.execute('''DROP VIEW IF EXISTS ccc_where_use_function''')
    cursor.execute('''
    CREATE VIEW ccc_where_use_function AS
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

global connected_files

func_data =         []
connected_files =   []
flag_m_comment =    False
ID =                1
code_line =         0


for i in data:
    cursor.execute('SELECT idfunc, name, start_line FROM ccc_definition_function WHERE file_id = {0} AND idfunc NOT IN (SELECT idfunc FROM ccc_declaration_function)'.format(i[0]))
    func_data = cursor.fetchall()
    cursor.execute('SELECT idfunc, name, line_detect FROM ccc_declaration_function WHERE file_id = {0} AND idfunc IN (SELECT idfunc FROM ccc_definition_function)'.format(i[0]))

    connected_files = []
    connected_files.append(i[0])
    searchConnectTree(i[0])

    for j in connected_files:
        with open(data[j - 1][1], encoding=data[j - 1][2]) as f:
            print('Open {0}:\t{1}'.format(data[j - 1][0], data[j - 1][1]))
            code_line = 0
            for line in f:
                code_line += 1

                if not flag_m_comment:
                    comments = finder.findComments(line)
                    string = finder.cleaner(comments, line)

                    if comments['many_line_comments']:
                        if comments['many_line_comments'][-1][1] == -1:
                            flag_m_comment = True

                    for func in func_data:
                        if '::' in func[1]:
                            name = func[1][func[1].find('::') + 2:]
                        else:
                            name = func[1]
                        if ((name + '(') in string) or ((name + ' (') in string):
                            for sbl in ' =-+*&/\\\'"?%.,<>[]{};:^$#@!`~()|':
                                if (sbl + name) in string:
                                    if j == i[0]:
                                        if code_line <= func[2]:
                                            continue
                                        pasteData(ID, func[0], func[1], i[0], j, code_line, line)
                                        ID += 1
                                    else:
                                        pasteData(ID, func[0], func[1], i[0], j, code_line, line)
                                        ID += 1

                elif '*/' in line:
                    flag_m_comment = False

                    string = line[line.find('*/') + 2:]
                    comments = finder.findComments(string)
                    string = finder.cleaner(comments, string)

                    if comments['many_line_comments']:
                        if comments['many_line_comments'][-1][1] == -1:
                            flag_m_comment = True

                    for func in func_data:
                        if '::' in func[1]:
                            name = func[1][func[1].find('::') + 2:]
                        else:
                            name = func[1]
                        if ((name + '(') in string) or ((name + ' (') in string):
                            for sbl in ' =-+*&/\\\'"?%.,<>[]{};:^$#@!`~()|':
                                if (sbl + name) in string:
                                    if j == i[0]:
                                        if code_line <= func[2]:
                                            continue
                                        pasteData(ID, func[0], func[1], i[0], j, code_line, line)
                                        ID += 1
                                    else:
                                        pasteData(ID, func[0], func[1], i[0], j, code_line, line)
                                        ID += 1

conn.commit()
