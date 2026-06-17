# -*- coding: utf-8 -*-
from dbFolder import *

conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
cursor = conn.cursor()

def pasteData(name, coll = None):#Добавление данных в таблицу
    global cursor
    cursor.execute('''
        INSERT INTO ccc_report
        VALUES (%s, %s)
    ''', (name, coll))

cursor.execute('DROP TABLE IF EXISTS ccc_report CASCADE')
cursor.execute('''
CREATE TABLE ccc_report(
    name TEXT,
    coll FLOAT);
''')

cursor.execute('SELECT id_file from ccc_file_list')
data = cursor.fetchall()
print('1')
files = len(data)
print("I'm alive!")

try:
    cursor.execute('''SELECT id_file FROM ccc_file_list
    WHERE id_file NOT IN (SELECT id_file FROM ccc_connect_list) AND
    id_file NOT IN (SELECT connecttoid FROM ccc_connect_list)''')
    data = cursor.fetchall()
    useFiles = files - len(data)
except Exception:
    useFiles = files
print('2')

if files > 0:
    percentUseFiles = useFiles / float(files) * 100.0
else:
    percentUseFiles = 0.0

cursor.execute('SELECT idfunc from ccc_definition_function')
data = cursor.fetchall()
print('3')
if data:
    functions = len(data)
else:
    functions = 0

# «Функций со связями» = число уникальных определённых функций, которые хотя бы раз вызываются
# (ccc_use_function_list хранит каждое вхождение вызова — строк больше, чем функций)
cursor.execute('''
    SELECT COUNT(DISTINCT u.idfunc)
    FROM ccc_use_function_list u
    INNER JOIN ccc_definition_function d ON d.idfunc = u.idfunc
''')
row = cursor.fetchone()
useFunctions = row[0] if row and row[0] is not None else 0
print('4')
if useFunctions > functions:
    useFunctions = functions
if functions > 0:
    percentUseFunc = useFunctions / float(functions) * 100.0
else:
    percentUseFunc = 0.0

# Переменные: при наличии таблиц из clang_ast_variables используем их, иначе — ccc_variables_v / ccc_unuseVar
try:
    cursor.execute("SELECT COUNT(*) FROM ccc_definition_variable")
    row = cursor.fetchone()
    variables = int(row[0]) if row else 0
    use_ast_vars = True
except Exception:
    use_ast_vars = False
    variables = 0

if use_ast_vars:
    try:
        cursor.execute("SELECT COUNT(*) FROM ccc_not_use_variable_ast")
        r = cursor.fetchone()
        not_used = int(r[0]) if r else 0
        useVar = variables - not_used
    except Exception:
        useVar = variables
    print('5 (AST variables)')
else:
    cursor.execute('SELECT file_id from ccc_variables_v')
    data = cursor.fetchall()
    print('5')
    if data:
        variables = len(data)
    else:
        variables = 0
    try:
        cursor.execute('SELECT varid from ccc_unuseVar')
        data = cursor.fetchall()
        print('6')
        if data:
            useVar = variables - len(data)
        else:
            useVar = variables
    except Exception:
        useVar = variables

if variables > 0:
    percentUseVar = useVar / float(variables) * 100.0
else:
    percentUseVar = 0.0

pasteData('*--files--*')
pasteData('Файлов', files)
pasteData('Файлов со связями', useFiles)
pasteData('Файлов без связей', files - useFiles)
pasteData('Доля файлов со связями (%)', percentUseFiles)

pasteData('*--functions--*')
pasteData('Функций', functions)
pasteData('Функций со связями', useFunctions)
pasteData('Функций без связей', functions - useFunctions)
pasteData('Доля функций со связями (%)', percentUseFunc)

pasteData('*--variables--*')
pasteData('Переменных', variables)
pasteData('Переменных со связями', useVar)
pasteData('Переменных без связей', variables - useVar)
pasteData('Доля переменных со связями (%)', percentUseVar)

conn.commit()
