import psycopg2 #PostgreSQL
##import sqlite3
from _Start_Multy_Java import folder
import re



def get_class_info_for_file_id(file_id):
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select classid, start, end_, name from ccc_class_list where id_file = %s"%file_id)
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i)
    return list

def get_func_info_for_file_id(file_id):
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select '1' as parent_class_id, file_id, start_line, end_line from ccc_definition_function where file_id = %s"%file_id)
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i)
    return list

if __name__=='__main__':
    Mass = get_class_info_for_file_id(5)
    print(Mass)
