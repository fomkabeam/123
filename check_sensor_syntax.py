# -*- coding: utf-8 -*-
"""
Проверка синтаксиса C++ файлов после вставки сенсоров.
Использование: python3 check_sensor_syntax.py <путь_к_файлу.cpp>
"""
import sys
import re

def check_file(file_path):
    """Проверка файла на потенциальные проблемы с вставленными сенсорами."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print("Ошибка чтения файла: {}".format(e))
        return False

    issues = []
    brace_count = 0
    paren_count = 0
    
    for i, line in enumerate(lines, start=1):
        # Проверка на SENSOR в неподходящих местах
        if 'SENSOR(' in line:
            stripped = line.strip()
            # Проверка: SENSOR не должен быть внутри выражений без точки с запятой
            if stripped.startswith('SENSOR(') and not stripped.endswith(';'):
                # Но может быть многострочное, проверим следующую строку
                if i < len(lines):
                    next_stripped = lines[i].strip() if i < len(lines) else ''
                    if not next_stripped.startswith(';'):
                        issues.append("Строка {}: SENSOR без точки с запятой в конце строки".format(i))
            
            # Проверка: SENSOR не должен быть внутри списков инициализации
            if '{' in line[:line.find('SENSOR(')] and '}' not in line[:line.find('SENSOR(')]:
                issues.append("Строка {}: SENSOR может быть внутри списка инициализации {{...}}".format(i))
        
        # Подсчёт скобок для проверки баланса
        brace_count += line.count('{') - line.count('}')
        paren_count += line.count('(') - line.count(')')
        
        # Если слишком много открывающих скобок без закрывающих - возможна проблема
        if brace_count > 10:
            issues.append("Строка {}: слишком много открывающих {{ без закрывающих (возможно незакрытый блок)".format(i))
    
    if brace_count != 0:
        issues.append("Несбалансированные фигурные скобки: разница = {}".format(brace_count))
    
    if issues:
        print("Найдены потенциальные проблемы в {}:".format(file_path))
        for issue in issues:
            print("  - {}".format(issue))
        return False
    else:
        print("Файл {} выглядит синтаксически корректным.".format(file_path))
        return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python3 check_sensor_syntax.py <путь_к_файлу.cpp>")
        sys.exit(1)
    
    check_file(sys.argv[1])
