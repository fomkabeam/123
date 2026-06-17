# -*- coding: utf-8 -*-
import finderCommentAndQuoatsInCppLineCode as finder
from findBrk import findBrk
import sqlite3
import psycopg2 #PostgreSQL
import find_files
from dbFolder import *

global conn
conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
# conn = sqlite3.connect('../result.db')
global cursor
cursor = conn.cursor()

def searchConnectTree(id_file):
    global cursor
    global connected_files

    cursor.execute('SELECT id_file FROM ccc_connect_list WHERE connectToID = {0}'.format(id_file))

    for i in cursor.fetchall():
        if i[0] not in connected_files:
            connected_files.append(i[0])
            searchConnectTree(i[0])

def mainSearchVar(id_file, path, enc):
    global arrVar
    global cursor
    global connected_files
    cursor.execute('SELECT var_id, var_name, num_line, class_id FROM ccc_variables_v WHERE file_id = {0}'.format(id_file))
    buff = cursor.fetchall()
    name = ''
    for i in buff:
        if '[' in i[1]:
            name = i[1][:i[1].find('[')]
            # # print(name)
            arrVar.append(var(i[0], name, i[2]))
        else:
            arrVar.append(var(i[0], i[1], i[2]))
        if i[3] != 0:
            arrVar[-1].globaly = True
    del buff
    last_sum_of_brace = 0
    sum_of_brace = 0
    code_line = 0
    unuse_list = []
    with open(path, encoding=enc) as f:
        for line in f:
            code_line += 1
            # print('Line\t{0}: {1}'.format(code_line, line))
            comments = finder.findComments(line)
            last_sum_of_brace = sum_of_brace
            sum_of_brace = findBrk(comments, line, '{}', sum_of_brace)[0]


            for i in range(len(arrVar)):
                if arrVar[i].line == code_line:
                    arrVar[i].level = sum_of_brace
                    if sum_of_brace == 0:
                        arrVar[i].globaly = True
                    if arrVar[i].globaly:
                        arrVar[i].level = 0
                if arrVar[i].level > -1:
                    if (arrVar[i].level > sum_of_brace) and (not arrVar[i].use):
                        unuse_list.append(i)
                        arrVar[i].pasteData(id_file)
                    elif (arrVar[i].line < code_line) and (not arrVar[i].use):
                        arrVar[i].searchInLine(line, comments)
            for i in range(len(unuse_list)-1):
                for j in range(len(unuse_list)-i-1):
                    if unuse_list[j] < unuse_list[j+1]:
                        unuse_list[j], unuse_list[j+1] = unuse_list[j+1], unuse_list[j]
            # # print(unuse_list)
            if unuse_list:
                for i in unuse_list:
                    del arrVar[i]
            unuse_list = []

            index = 0
            while index < len(arrVar):
                if arrVar[index].use:
                    del arrVar[index]
                else:
                    index += 1

    if len(arrVar) > 0:
        unuse_list = []
        for i in range(len(arrVar)):
            if not arrVar[i].globaly:
                unuse_list.append(i)
                arrVar[i].pasteData(id_file)

        for i in range(len(unuse_list)-1):
            for j in range(len(unuse_list)-i-1):
                if unuse_list[j] < unuse_list[j+1]:
                    unuse_list[j], unuse_list[j+1] = unuse_list[j+1], unuse_list[j]

        for i in unuse_list:
            del arrVar[i]

        if len(arrVar) > 0:
            cursor.execute('SELECT connectToID FROM ccc_connect_list WHERE id_file = {0}'.format(id_file))
            buff = cursor.fetchall()
            if buff:
                del buff
                connected_files = []
                searchConnectTree(id_file)
                main_id_file = id_file
                arrFiles = []
                for i in connected_files:
                    cursor.execute('SELECT path, encoding FROM ccc_file_list WHERE id_file = {0}'.format(i))
                    temp_data = cursor.fetchall()[0]
                    arrFiles.append([i, temp_data[0], temp_data[1]])
                for i in arrFiles:
                    if arrVar:
                        id_file = i[0]
                        path = i[1]
                        with open(path,  encoding=i[2]) as f:
                            for line in f:
                                comments = finder.findComments(line)
                                for i in range(len(arrVar)):
                                    if not arrVar[i].use:
                                        arrVar[i].searchInLine(line, comments)

                                while index < len(arrVar):
                                    if arrVar[index].use:
                                        del arrVar[index]
                                    else:
                                        index += 1
                    else:
                        break
                while arrVar:
                    arrVar[0].pasteData(main_id_file)
                    del arrVar[0]
            else:
                while arrVar:
                    arrVar[0].pasteData(id_file)
                    del arrVar[0]


class var:
    def __init__(self, id, name, line, level = -1, globaly = False):
        self.id = id
        self.name = name
        self.line = line
        self.level = level
        self.globaly = globaly
        self.use = False
    def searchInLine(self, line, comments):
        string = finder.cleaner(comments, line)

        simbols = (' ', '\t', '\n', '=', '+', '-', '%', ';', '*', '/', '&', '|', '(', ')', '{', '}', '^', ':', '.', '[', ']', '?', '>', '<')

        for s in simbols:
            if (s + self.name) in string:
                for s2 in simbols:
                    if (self.name + s2) in string:
                        self.use = True
                        return 0
    def pasteData(self, id_file):
        global cursor
        cursor.execute('INSERT INTO ccc_unuseVar VALUES (%s, %s, %s)', (self.id, self.name, id_file))
        conn.commit()



# find_files.create_table_files()
# find_files.run('/home/fokriz/Рабочий стол/Work/Parsing Task/C++/Test')

DT=int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS ccc_unuseVar''')
    cursor.execute('''
    CREATE TABLE ccc_unuseVar (
    	VarID      	INT NOT NULL PRIMARY KEY,
        name        TEXT,
    	id_file	    INTEGER);
    ''')
    conn.commit()

cursor.execute("SELECT id_file, path, encoding FROM ccc_file_list")
data = cursor.fetchall()

global arrVar
arrVar = []
chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])

for i in data:
    if chek_search_File_ID !=0 and file_id < chek_search_File_ID:
            continue
    # print('Open {0}:\t{1}'.format(i[0], i[1]))
    mainSearchVar(i[0], i[1], i[2])



conn.close()
