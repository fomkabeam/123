import finderCommentAndQuoatsInCppLineCode as finder
from dbFolder import *
import re

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

global id
id = 0

def pasteData(caller_id, perl_file_id, num_line, line): #Добавление данных в таблицу
    global cursor
    global id
    id += 1
    cursor.execute('''
    INSERT INTO perl_external_calls
    VALUES (%s, %s, %s, %s, %s)
    ''', (caller_id, perl_file_id, 'C++ Qt', num_line, line))
    conn.commit()

DT = int(folder['DROP_TBL'])
if DT == 1:
    cursor.execute('''DROP TABLE IF EXISTS perl_external_calls''')
    cursor.execute('''
        CREATE TABLE perl_external_calls(
        	caller_id       INTEGER,
        	perl_file_id    INTEGER,
            lang            TEXT,
            num_line        INTEGER,
            line            TEXT);
    ''')
    conn.commit()

cursor.execute('''DELETE FROM perl_external_calls
                  WHERE lang = 'C++ Qt' ''')
conn.commit()

cursor.execute('''SELECT file_id, name FROM perl_files''')
perl_files = cursor.fetchall()

cursor.execute('''SELECT id_file, qoutes, num_line, line FROM ccc_start_qprocess''')
data = cursor.fetchall()

for qprocess in data:
    if qprocess[1].rfind('/') != -1:
        for file in perl_files:
            if file[1] == qprocess[1][qprocess[1].rfind('/') + 1:]:
                pasteData(qprocess[0], file[0], qprocess[2], qprocess[3])
