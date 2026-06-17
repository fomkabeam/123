# -*- coding: utf-8 -*-
from dbFolder import *

global connected_files

def searchConnectTree(id_file):
    global cursor
    global connected_files

    cursor.execute('SELECT id_file FROM ccc_connect_list WHERE connectToID = {0}'.format(id_file))

    for i in cursor.fetchall():
        if i[0] not in connected_files:
            connected_files.append(i[0])
            searchConnectTree(i[0])

class func:
    global ID
    def __init__(self, func_id, file_id, name, param_func, line_detect, start_line, start_pos, end_line, end_pos, modifier_and_return_type, line, IDT = -1):
        self.ID = IDT
        self.func_id = func_id
        self.file_id = file_id
        self.name = name
        self.param_func = param_func
        self.line_detect = line_detect
        self.start_line = start_line
        self.start_pos = start_pos
        self.end_line = end_line
        self.end_pos = end_pos
        self.modifier_and_return_type = modifier_and_return_type
        self.line = line
        if self.ID != -1:
            self.connectTree = []
    def searchID(self, arr):
        global ID
        if '::' in self.name:
            name = self.name[self.name.find('::') + 2:]
        else:
            name = self.name
        for fun in arr:
            if self.file_id in fun.connectTree:
                if fun.name == name:
                    if self.modifier_and_return_type == fun.modifier_and_return_type:
                        self.ID = fun.ID
                        break
        if self.ID == -1:
            ID += 1
            self.ID = ID
global cursor
conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

DT=int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS ccc_declaration_function CASCADE''')
    cursor.execute('''
    CREATE TABLE ccc_declaration_function(
    	IDfunc	        INTEGER NOT NULL PRIMARY KEY,
        IDfromAllList   INTEGER,
        file_id         int,
        name            text,
        param_func      text,
        line_detect     int,
        modifier_and_return_type text,
        line            text);
    ''')
    cursor.execute('''DROP TABLE IF EXISTS ccc_definition_function CASCADE''')
    cursor.execute('''
    CREATE TABLE ccc_definition_function(
    	IDfunc	        INTEGER,
        IDfromAllList   INTEGER,
        file_id         int,
        name            text,
        param_func      text,
        line_detect     int,
        start_line      int,
        start_pos       int,
        end_line        int,
        end_pos         int,
        modifier_and_return_type text,
        line            text);
    ''')
    conn.commit()

cursor.execute('''select func_id, file_id, name, param_func, line_detect, modifier_and_return_type, line
from ccc_function_list
where modifier_and_return_type != '' and have_block_or_not = 0 and strpos(line, ';') > 0
and strpos(modifier_and_return_type, ':') != length(modifier_and_return_type) - 1 and (modifier_and_return_type != 'throw' or modifier_and_return_type != 'throw ')
order by file_id asc''')

global ID
dec_data = []
ID = 0
last_file_id = -1
connected_files = []
print('Start dec')
# for i in cursor.fetchall():
#     ID += 1
#     #cursor.execute('''
#     #INSERT INTO ccc_declaration_function VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#     #''', (ID, i[0], i[1], i[2], i[3], i[4], i[5], i[6]))
#     print('\t', ID, i[0], i[1], i[2], i[3], i[4], i[5], i[6])
#     if last_file_id == -1:
#         connected_files = [i[1]]
#     dec_data.append(func(i[0], i[1], i[2], i[3], i[4], -1, -1, -1, -1, i[5], i[6], ID))
#     if last_file_id == i[1]:
#         dec_data[-1].connectTree = connected_files
#     else:
#         connected_files = [i[1]]
#         searchConnectTree(i[1])
#         dec_data[-1].connectTree = connected_files
# conn.commit()


cursor.execute('''select func_id, file_id, name, param_func, line_detect, start_line, start_pos, end_line, end_pos, modifier_and_return_type, line
from ccc_function_list
where modifier_and_return_type != '' and have_block_or_not = 1 and name != 'if'
and strpos(modifier_and_return_type, ':') != length(modifier_and_return_type) - 1''')

data_func = []
print('Start def')
id = 0
for i in cursor.fetchall():
    if '{}' in i[10]:
        continue
    id += 1
    temp_obj = func(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9], i[10], id)
    # temp_obj.searchID(dec_data)
    cursor.execute('''
    INSERT INTO ccc_definition_function VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (temp_obj.ID, temp_obj.func_id, temp_obj.file_id, temp_obj.name, temp_obj.param_func, temp_obj.line_detect, temp_obj.start_line, temp_obj.start_pos, temp_obj.end_line, temp_obj.end_pos, temp_obj.modifier_and_return_type, temp_obj.line))



conn.commit()
