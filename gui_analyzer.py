# -*- coding: utf-8 -*-
"""
Модуль для запуска анализа с отображением прогресса
"""

import subprocess
import os
import sys
from threading import Event
import re

class AnalyzerRunner:
    """Класс для запуска анализа в отдельном потоке"""
    
    def __init__(self, progress_callback, complete_callback):
        self.progress_callback = progress_callback
        self.complete_callback = complete_callback
        self.stop_event = Event()
        self.process = None
        
    def run_analysis(self, config):
        """Запуск анализа"""
        try:
            self.stop_event.clear()
            # Режим «один исполняемый файл» (PyInstaller): запуск себя с --analyze
            if getattr(sys, 'frozen', False):
                script_dir = os.path.dirname(os.path.abspath(sys.executable))
                cmd = [sys.executable, '--analyze']
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                starter_script = os.path.join(script_dir, '_Starter.py')
                if not os.path.exists(starter_script):
                    self.complete_callback(False, "Файл {} не найден".format(starter_script))
                    return
                python_path = config.get('PATH_PYTHON', 'python3')
                if not python_path or not os.path.exists(python_path):
                    python_path = 'python3'
                cmd = [python_path, starter_script]

            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            self.progress_callback("Запуск анализатора...")
            self.progress_callback("Команда: {}".format(' '.join(cmd)))
            self.progress_callback(
                "Ожидание лога подпроцесса… Долгая пауза после find_files_Start — норма на большом проекте "
                "(обход каталога и запись в БД по каждому файлу). См. строки find_files: в журнале."
            )

            log_path = config.get('ANALYSIS_LOG', '').strip()
            log_file = None
            if log_path:
                try:
                    log_file = open(log_path, 'w', encoding='utf-8')
                    log_file.write("=== Лог анализа {} ===\n".format(' '.join(cmd)))
                    log_file.flush()
                    self.progress_callback("Лог анализа: {}".format(log_path))
                except Exception as e:
                    self.progress_callback("Не удалось открыть файл лога: {}".format(e))
                    log_file = None

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=script_dir,
                env=env
            )
            
            # Чтение вывода в реальном времени и запись в лог-файл
            failed_step = None
            failed_code = None
            try:
                for line in iter(self.process.stdout.readline, ''):
                    if self.stop_event.is_set():
                        self.process.terminate()
                        self.progress_callback("Анализ остановлен пользователем")
                        self.complete_callback(False, "Анализ остановлен пользователем")
                        return
                    
                    if line:
                        if log_file:
                            try:
                                log_file.write(line)
                                if not line.endswith('\n'):
                                    log_file.write('\n')
                                log_file.flush()
                            except Exception:
                                pass
                        line_stripped = line.strip()
                        if line_stripped:
                            m = re.search(r"^([A-Za-z0-9_]+)_FAILED:\s*код\s+(-?\d+)", line_stripped)
                            if m:
                                failed_step = m.group(1)
                                failed_code = m.group(2)
                            self.progress_callback(self._humanize_log_line(line_stripped))
            finally:
                if log_file:
                    try:
                        log_file.close()
                    except Exception:
                        pass
            
            # Ожидание завершения процесса
            return_code = self.process.wait()
            
            if return_code == 0 and failed_step is None:
                self.progress_callback("Анализ завершен успешно")
                self.complete_callback(True, "")
            else:
                if failed_step is not None:
                    error_msg = "Шаг '{}' завершился с ошибкой (код {})".format(failed_step, failed_code or return_code)
                else:
                    error_msg = "Анализ завершился с кодом возврата {}".format(return_code)
                self.progress_callback(error_msg)
                self.complete_callback(False, error_msg)
                
        except FileNotFoundError:
            error_msg = "Python не найден по пути: {}".format(config.get('PATH_PYTHON', 'python3'))
            self.progress_callback(error_msg)
            self.complete_callback(False, error_msg)
        except Exception as e:
            error_msg = "Ошибка выполнения анализа: {}".format(str(e))
            self.progress_callback(error_msg)
            self.complete_callback(False, error_msg)
        finally:
            self.process = None
    
    def stop(self):
        """Остановка анализа"""
        self.stop_event.set()
        if self.process:
            try:
                self.process.terminate()
            except:
                pass

    @staticmethod
    def _humanize_log_line(line):
        """
        Делает служебные логи пайплайна более понятными для пользователя.
        Оригинальная строка не теряется полностью — при необходимости оставляем хвост.
        """
        step_names = {
            "find_files": "Сканирование файлов проекта",
            "clang_ast_connect": "Поиск связей #include (AST)",
            "clang_ast_classes": "Поиск классов/структур (AST)",
            "clang_ast_runner": "Анализ функций и вызовов (AST)",
            "clang_ast_variables": "Анализ переменных (AST)",
            "NEW_3_F_Line_Seg": "Построение сегментов строк/ветвей",
            "clang_ast_var_view": "Подготовка представлений по переменным",
            "clang_runner": "Запуск диагностики clang-tidy",
            "createReport": "Формирование отчёта",
        }

        m = re.match(r"^([A-Za-z0-9_]+)_(Start|End)$", line)
        if m:
            step = m.group(1)
            phase = m.group(2)
            title = step_names.get(step, step)
            if phase == "Start":
                return "Этап: {} — начало".format(title)
            return "Этап: {} — завершено".format(title)

        m = re.match(r"^([A-Za-z0-9_]+)_FAILED:\s*код\s+(-?\d+)", line)
        if m:
            step = m.group(1)
            code = m.group(2)
            title = step_names.get(step, step)
            return "Этап: {} — ошибка (код {})".format(title, code)

        m = re.match(r"^clang_ast_connect:\s*\[(\d+)/(\d+)\]\s+(.+)$", line)
        if m:
            return "Поиск связей include: файл {}/{} — {}".format(m.group(1), m.group(2), m.group(3))

        m = re.match(r"^Parsing\s+(.+)\.\.\.$", line)
        if m:
            return "Разбор файла AST: {}".format(m.group(1))

        m = re.match(r"^PIPELINE_STAGE\s+(\d+)/(\d+):\s+([A-Za-z0-9_]+)$", line)
        if m:
            step = m.group(3)
            title = step_names.get(step, step)
            return "Шаг {}/{}: {}".format(m.group(1), m.group(2), title)

        return line

