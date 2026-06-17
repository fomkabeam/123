
from dbFolder import *

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

tables = ['ccc_class_list', 'ccc_connect_list', 'ccc_declaration_function', 'ccc_definition_function', 'ccc_file_list', 'ccc_function_list', 'ccc_line_seg', 'ccc_use_function_list', 'ccc_unusevar', 'ccc_variables_v']
start = 'COPY public.{0}'
flag_table = False
temp_arr = []
index = 0
index_t = 0

with open('dump20201117', 'r') as file:
    code_line = 0
    for line in file:
        code_line += 1
        if code_line > 270:
            if flag_table:
                for i in data[index]:
                    temp_arr.append(i)
                if temp_arr != line[:-1].split('\t'):
                    print("Error!!! ", temp_arr, line)
                temp_arr = []
                index += 1
            else:
                if start.format(tables[index_t]) in line:
                    index_t += 1
                    index = 0
                    cursor.execute('select * from ' + tables[index_t - 1])
                    data = cursor.fetchall()
