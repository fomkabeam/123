from dbFolder import *
import re
import os

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

global id
id = 0

def pasteData(connectid, id_file, namefile, connecttoname, line): #Добавление данных в таблицу
    global cursor
    global id
    id += 1
    cursor.execute('''
    INSERT INTO ccc_connect_list
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (connectid, id_file, namefile, -1, connecttoname, -1, line))
    conn.commit()



cursor.execute('''SELECT id_file, name_rash FROM ccc_not_use_files''')
files = cursor.fetchall()

command = '''grep -rs '{0}' /home/fokriz/Рабочий\ стол/Work/evrika/15ПК/src20210414/dgate'''
connectid = 64368

for file in files:
    name = file[1][:file[1].find('.')] + '\\' + file[1][file[1].find('.'):]

    data = os.popen(command.format(name)).read()
    data = data.split('\n')
    for line in data:
        file_path = line[57:line[57:].find(':') + 57]
        string = line[line[57:].find(':') + 58:]
        if 'Makefile' in file_path:
            connectid += 1
            print(connectid, file[0], file[1], file_path, string)
            pasteData(connectid, file[0], file[1], file_path, string)
            break

conn.close()
