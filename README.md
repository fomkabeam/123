# Анализатор 

## Настройка LOG_PATH.txt

```
DB_NAME=grant_2 - Имя базы данных
DB_USER=ndvparser - Имя пользователя базы данных
DB_PASS=pndv - Пароль базы данных
DB_HOST=192.168.0.37 - IP базы данных
DB_PORT=5433 - Порт базы данных
PATH_FILE=/home/fokriz/Рабочий стол/Work/granit/src/lab - Путь к проекту
PATH_PYTHON=/usr/bin/python - Путь к Python
FILE_EXTENSION=c cc cpp h hpp inl H C CPP HPP - Расширения файлов
FILE_ID_IN_TBL_SEARCH=0 - Файл с которого начинать анализ
PID_SEARCH_PATH=/home/pidSearch.h - Для вставки датчиков, то что будет записываться #include "сюда"
DROP_TBL=1 - Сбрасывать таблицу или нет в скрипте
SEARH_METH=ALL - Метод поиска
CHECK_DEPTH=2 - Уровень контроля
```

## Порядок запуска

```bash
python3 find_files.py
python3 findConnectionBetweenFilesCpp.py
#Если 4 уровень контроля то всё
python3 findCppClass.py
python3 findFunction.py
python3 funcToNormal.py
python3 NEW_3_F_Line_Seg.py #Для 2 уровня контроля
python3 NEW_5_JSensor_NEW_Variant.py
python3 NEW_4_Variabels_C.py
python3 findUseFunction.py
```

## Возможные проблемы

```bash
python3 NEW_3_F_Line_Seg.py
```
Тут может быть ошибка с border_f тогда создать блок типо этого

```python
if border_f == None:
                                        param_start=-1
                                        param_count_S=0
                                        param_SS=0
                                        param_lock=-1
                                        param_count_L=0
                                        param_LS=0
                                        param_STR=''
                                        detected_SWITCH=0
                                        line_seg_started=0
                                        line_seg_detected=0
                                        num_line_detected=0
                                        continue
                                    line_seg_id+=1
                                    #
                                    # try:
                                    if border_f[0][0] != 0:
                                        HBON=1
                                    else:
                                        HBON=0
                                    #
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'SWITCH', param_STR, num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                    conn.commit()
                                    conn.close()
                                    #
##                                    IN_SWITCH_BLOCK=1
                                    # print(border_f)
                                    switch_block.append((line_seg_id, border_f[0][0], border_f[0][2], border_f[1][0], border_f[1][2]))
##                                    switch_open_block.append((border_f[0][0],border_f[0][2]))
##                                    switch_close_block.append((border_f[1][0]),border_f[1][2]))
                                    #
                                    # except Exception:
                                    #     param_start=-1
                                    #     param_count_S=0
                                    #     param_SS=0
                                    #     param_lock=-1
                                    #     param_count_L=0
                                    #     param_LS=0
                                    #     param_STR=''
                                    #     detected_SWITCH=0
                                    #     line_seg_started=0
                                    #     line_seg_detected=0
                                    #     num_line_detected=0
                                    #     continue

                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_SWITCH=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    continue
                                continue
``` 
## Инструменты

Скрипты для нахождения Qt вызовов, перловских файлов из С++, порядок запуска после отработки анализатора
```bash
python3 QProcess.py
python3 startQprocess.py
python3 perl_files_in_quoats.py
python3 perl_calls_qprocess.py
```
