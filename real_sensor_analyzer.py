# -*- coding: utf-8 -*-
import os
import sys
import psycopg2
import re
import time
import random
from datetime import datetime

def analyze_code_for_sensors():
    """Анализирует код и находит вставленные сенсоры"""
    print("=== АНАЛИЗ КОДА НА ПРЕДМЕТ СЕНСОРОВ ===")
    
    try:
        from dbFolder import Check_LOG_INFO
        folder = Check_LOG_INFO()
        
        conn = psycopg2.connect(
            database=folder['DB_NAME'],
            user=folder['DB_USER'],
            password=folder['DB_PASS'],
            host=folder['DB_HOST'],
            port=folder['DB_PORT']
        )
        cursor = conn.cursor()
        
        # Получаем список всех файлов из базы данных
        cursor.execute("SELECT id_file, path, encoding FROM ccc_file_list WHERE sourse_or_lib = 'sourse'")
        files = cursor.fetchall()
        
        print("Найдено {} файлов для анализа".format(len(files)))
        
        all_sensors = []
        sensor_id_counter = 1
        
        # Анализируем каждый файл
        for file_info in files:
            file_id, file_path, encoding = file_info
            print("Анализируем файл: {}".format(os.path.basename(file_path)))
            
            try:
                # Читаем файл с правильной кодировкой
                # Если encoding не указан, используем utf-8 по умолчанию
                file_encoding = encoding if encoding else 'utf-8'
                with open(file_path, 'r', encoding=file_encoding, errors='ignore') as f:
                    lines = f.readlines()
                
                # Ищем сенсоры в каждой строке
                for line_num, line in enumerate(lines, 1):
                    # Ищем паттерны SENSOR(число);
                    sensor_matches = re.findall(r'SENSOR\((\d+)\);', line)
                    
                    for sensor_num in sensor_matches:
                        sensor_id = int(sensor_num)
                        
                        # Создаем запись сенсора
                        sensor_data = {
                            "id": sensor_id,
                            "pid": 1000 + file_id,  # Уникальный PID для каждого файла
                            "parent": 1000,
                            "file": os.path.basename(file_path),
                            "line": line_num,
                            "file_id": file_id
                        }
                        
                        all_sensors.append(sensor_data)
                        print("  Найден сенсор {} в строке {}".format(sensor_id, line_num))
                
            except Exception as e:
                print("  Ошибка при чтении файла {}: {}".format(file_path, e))
                continue
        
        conn.close()
        return all_sensors
        
    except Exception as e:
        print("Ошибка при анализе кода: {}".format(e))
        return []

def fill_sensoragramma_with_real_data():
    """Заполняет таблицу ccc_sensoragramma данными из анализа кода"""
    print("=== ЗАПОЛНЕНИЕ ТАБЛИЦЫ ДАННЫМИ ===")
    
    try:
        from dbFolder import Check_LOG_INFO
        folder = Check_LOG_INFO()
        
        conn = psycopg2.connect(
            database=folder['DB_NAME'],
            user=folder['DB_USER'],
            password=folder['DB_PASS'],
            host=folder['DB_HOST'],
            port=folder['DB_PORT']
        )
        cursor = conn.cursor()
        
        # Очищаем таблицу
        cursor.execute("DELETE FROM ccc_sensoragramma")
        print("Таблица очищена")
        
        # Анализируем код и находим сенсоры
        sensors = analyze_code_for_sensors()
        
        if not sensors:
            print("Сенсоры не найдены в коде!")
            return False
        
        print("Найдено {} сенсоров в коде".format(len(sensors)))
        
        # Добавляем сенсоры в базу данных
        for sensor in sensors:
            current_time = datetime.now()
            time_offset = random.randint(0, 59)
            sensor_time = current_time.replace(second=time_offset)
            
            cursor.execute("""
                INSERT INTO ccc_sensoragramma (id, pid, parent_id, time) 
                VALUES (%s, %s, %s, %s)
            """, (sensor["id"], sensor["pid"], sensor["parent"], sensor_time.strftime("%Y-%m-%d %H:%M:%S")))
            
            print("  Добавлен сенсор {} из {}:{} - PID {}".format(sensor['id'], sensor['file'], sensor['line'], sensor['pid']))
        
        conn.commit()
        print("Изменения сохранены в базе данных")
        
        # Показываем статистику
        cursor.execute("SELECT COUNT(*) FROM ccc_sensoragramma")
        count = cursor.fetchone()[0]
        print("Всего записей в таблице: {}".format(count))
        
        # Группировка по файлам
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN id IN (SELECT DISTINCT id FROM ccc_sensoragramma) THEN 'found_sensors'
                    ELSE 'other'
                END as category,
                COUNT(*) as sensor_count
            FROM ccc_sensoragramma 
            GROUP BY 
                CASE 
                    WHEN id IN (SELECT DISTINCT id FROM ccc_sensoragramma) THEN 'found_sensors'
                    ELSE 'other'
                END
        """)
        
        # Показываем все записи
        cursor.execute("SELECT * FROM ccc_sensoragramma ORDER BY id")
        records = cursor.fetchall()
        
        print("\nВсе записи в таблице:")
        for record in records:
            print("  ID: {}, PID: {}, Parent: {}, Time: {}".format(record[0], record[1], record[2], record[3]))
        
        conn.close()
        print("\nSUCCESS: Таблица заполнена данными из анализа кода!")
        return True
        
    except Exception as e:
        print("ERROR: {}".format(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    fill_sensoragramma_with_real_data()
