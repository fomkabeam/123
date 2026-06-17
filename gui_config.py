# -*- coding: utf-8 -*-
"""
Модуль для управления конфигурацией анализатора
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import psycopg2

from gui_method_labels import method_display, method_from_display


def _normalize_pipeline_from(raw):
    """Из строки комбобокса «N/M: step_name» или просто «step_name» — только имя этапа."""
    s = (raw or "").strip()
    if ": " in s:
        s = s.split(": ", 1)[1].strip()
    return s


class ConfigManager:
    """Класс для управления конфигурацией"""
    
    def __init__(self, config_file='LOG_PATH.txt'):
        self.config_file = config_file
        # В frozen-режиме (PyInstaller) конфиг рядом с исполняемым файлом
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, config_file)
    
    def load_config(self):
        """Загрузка конфигурации из файла"""
        config = {}
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            return config
        except Exception as e:
            raise Exception("Ошибка чтения конфигурации: {}".format(str(e)))
    
    def save_config(self, config):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                for key, value in config.items():
                    f.write("{}={}\n".format(key, value))
            return True
        except Exception as e:
            raise Exception("Ошибка записи конфигурации: {}".format(str(e)))
    
    def get_config_value(self, key, default=None):
        """Получение значения конфигурации"""
        config = self.load_config()
        return config.get(key, default)

class SettingsWindow:
    """Окно настроек"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.config = {}
        self.entries = {}
        self.status_labels = {}
        self.entry_widgets = {}
        self.advanced_keys = []
        
        self.window = tk.Toplevel(parent)
        self.window.title("Настройки анализатора")
        self.window.geometry("600x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
        self.load_current_config()
        self.refresh_statuses()
        
    def create_widgets(self):
        """Создание виджетов окна настроек"""
        # Главный контейнер с прокруткой
        canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Настройки базы данных
        db_frame = ttk.LabelFrame(scrollable_frame, text="Настройки базы данных PostgreSQL", padding="10")
        db_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        db_frame.columnconfigure(1, weight=1)
        
        self.create_entry(db_frame, "DB_NAME", "Имя базы данных:", 0)
        self.create_entry(db_frame, "DB_USER", "Пользователь:", 1)
        self.create_entry(db_frame, "DB_PASS", "Пароль:", 2, show="*")
        self.create_entry(db_frame, "DB_HOST", "Хост:", 3)
        self.create_entry(db_frame, "DB_PORT", "Порт:", 4)
        
        # Пути
        path_frame = ttk.LabelFrame(scrollable_frame, text="Пути и файлы", padding="10")
        path_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        path_frame.columnconfigure(1, weight=1)
        
        path_entry = self.create_entry(path_frame, "PATH_FILE", "Путь к проекту:", 0)
        ttk.Button(path_frame, text="Обзор...", command=lambda: self.browse_folder(path_entry, "PATH_FILE")).grid(row=0, column=2, padx=5)
        
        compile_commands_entry = self.create_entry(path_frame, "COMPILE_COMMANDS", "Файл команд компиляции (если имеется):", 1)
        ttk.Button(path_frame, text="Обзор...", command=lambda: self.browse_compile_commands(compile_commands_entry, "COMPILE_COMMANDS")).grid(row=1, column=2, padx=5)
        
        clang_lib_entry = self.create_entry(path_frame, "CLANG_LIB", "Библиотека libclang (для AST и графа вызовов):", 2)
        ttk.Button(path_frame, text="Обзор...", command=lambda: self.browse_libclang(clang_lib_entry, "CLANG_LIB")).grid(row=2, column=2, padx=5)
        ttk.Button(path_frame, text="Найти", command=lambda: self.auto_fill_clang_lib(clang_lib_entry, "CLANG_LIB")).grid(row=2, column=3, padx=2)
        ttk.Label(path_frame, text="(пусто = авто; кнопка «Найти» — подставить первый найденный путь)", font=("", 8)).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        python_entry = self.create_entry(path_frame, "PATH_PYTHON", "Путь к Python:", 4)
        ttk.Button(path_frame, text="Обзор...", command=lambda: self.browse_file(python_entry, "PATH_PYTHON")).grid(row=4, column=2, padx=5)
        
        self.create_entry(path_frame, "PID_SEARCH_PATH", "Путь к pidSearch.h:", 5)
        
        log_entry = self.create_entry(path_frame, "ANALYSIS_LOG", "Файл лога анализа (путь и имя .txt, в реальном времени):", 6)
        ttk.Button(path_frame, text="Обзор...", command=lambda: self.browse_log_file(log_entry, "ANALYSIS_LOG")).grid(row=6, column=2, padx=5)
        ttk.Label(path_frame, text="(оставьте пустым, чтобы не писать лог в файл)", font=("", 8)).grid(row=7, column=1, sticky=tk.W, padx=5)
        self.create_entry(path_frame, "CLANG_TIDY_CHECKS", "Доп. проверки clang-tidy (через запятую, для метода CLANG):", 8)
        ttk.Label(
            path_frame,
            text="РД НДВ: bugprone-use-after-move, cert-err34-c, cppcoreguidelines-pro-bounds-pointer-arithmetic, misc-unused-parameters. Подробнее — README_CLANG.md",
            font=("", 8)
        ).grid(row=9, column=1, sticky=tk.W, padx=5)
        
        # Статусы путей и окружения
        status_frame = ttk.LabelFrame(scrollable_frame, text="Статусы проверки", padding="10")
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        status_frame.columnconfigure(1, weight=1)

        self._add_status_row(status_frame, "db", "Подключение к БД:", 0)
        self._add_status_row(status_frame, "project", "Папка проекта (PATH_FILE):", 1)
        self._add_status_row(status_frame, "compile_commands", "compile_commands.json:", 2)
        self._add_status_row(status_frame, "python", "Интерпретатор Python (PATH_PYTHON):", 3)
        self._add_status_row(status_frame, "pidsearch", "Файл pidSearch.h:", 4)
        self._add_status_row(status_frame, "libclang", "Библиотека libclang (CLANG_LIB):", 5)

        ttk.Button(status_frame, text="Обновить статусы", command=self.refresh_statuses).grid(
            row=6, column=1, sticky=tk.W, padx=5, pady=(6, 0)
        )

        # Параметры анализа
        params_frame = ttk.LabelFrame(scrollable_frame, text="Параметры анализа", padding="10")
        params_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        params_frame.columnconfigure(1, weight=1)
        # Профиль отображения полей
        self.profile_var = tk.StringVar(value="Базовый")
        ttk.Label(params_frame, text="Профиль интерфейса:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        profile_combo = ttk.Combobox(
            params_frame, textvariable=self.profile_var, values=["Базовый", "Эксперт"], state="readonly", width=14
        )
        profile_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        self.profile_var.trace("w", lambda *a: self.apply_profile_visibility())
        
        # Методы по уровням контроля (по _Starter.py): только те, что реально обрабатываются для данного DEPTH
        self.METHODS_BY_DEPTH = {
            "4": ["ALL", "FF_PFS", "FF", "PFS", "CO"],
            "3": ["ALL", "FF_PFS", "FF", "PFS", "CO", "ND", "C", "F", "V", "CPI", "ChI", "ADD_JSens", "CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"],
            "2": ["ALL", "FF_PFS", "FF", "PFS", "CO", "ND", "C", "F", "V", "CPI", "ChI", "LS", "ADD_JSens", "CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"],
        }
        depth_var = tk.StringVar()
        depth_combo = ttk.Combobox(params_frame, textvariable=depth_var, values=["2", "3", "4"],
                                   state="readonly", width=30)
        depth_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(params_frame, text="Уровень контроля НДВ по РД (CHECK_DEPTH, II–IV):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.entries["CHECK_DEPTH"] = (depth_combo, depth_var)
        method_var = tk.StringVar()
        method_combo = ttk.Combobox(params_frame, textvariable=method_var, state="readonly", width=30)
        method_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(params_frame, text="Сценарий анализа исходников (SEARH_METH):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.entries["SEARH_METH"] = (method_combo, method_var)
        self._depth_var = depth_var
        self._method_var = method_var

        drop_var = tk.StringVar()
        drop_combo = ttk.Combobox(params_frame, textvariable=drop_var, values=["0", "1"],
                                 state="readonly", width=30)
        drop_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(params_frame, text="Сбрасывать таблицы (DROP_TBL):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        drop_var.trace('w', lambda *args: self.update_config("DROP_TBL", drop_var.get()))
        self.entries["DROP_TBL"] = (drop_combo, drop_var)

        # Продолжить с этапа — создаём до привязки trace, чтобы _update_pipeline_from_combo имел _from_combo
        from_frames_var = tk.StringVar()
        from_combo = ttk.Combobox(params_frame, textvariable=from_frames_var, width=28)
        from_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(params_frame, text="Продолжить с этапа (PIPELINE_FROM):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(params_frame, text="(пусто = с начала; иначе этот этап и далее. Список — по текущему методу.)", font=("", 8)).grid(row=4, column=1, sticky=tk.W, padx=5)
        def on_from_change(*_args):
            self.update_config("PIPELINE_FROM", _normalize_pipeline_from(from_frames_var.get()))
        from_frames_var.trace("w", on_from_change)
        self.entries["PIPELINE_FROM"] = (from_combo, from_frames_var)
        self._from_combo = from_combo
        self._pipeline_steps_hint = ttk.Label(params_frame, text="", font=("", 8), foreground="gray", wraplength=520, justify=tk.LEFT)
        self._pipeline_steps_hint.grid(row=4, column=2, columnspan=2, sticky=tk.W, padx=5)

        def _update_pipeline_from_combo():
            """Обновить список этапов «Продолжить с этапа» по текущим уровню и методу."""
            try:
                from _Starter import get_effective_pipeline
                depth = self._depth_var.get()
                method_code = method_from_display(self._method_var.get())
                pipeline = get_effective_pipeline(depth, method_code, folder_override=self.config)
                steps = [""]
                pretty_steps = []
                if pipeline:
                    for i, st in enumerate(pipeline, 1):
                        steps.append("{}/{}: {}".format(i, len(pipeline), st))
                        pretty_steps.append("{}/{} {}".format(i, len(pipeline), st))
                self._from_combo["values"] = steps
                cur = self._from_combo.get()
                if cur and cur not in steps:
                    self._from_combo.set("")
                if pretty_steps:
                    self._pipeline_steps_hint.config(
                        text="Этапы текущего сценария: {}\nЧтобы продолжить после ошибки: выберите этап и нажмите «Сохранить».".format(
                            " | ".join(pretty_steps)
                        )
                    )
                else:
                    self._pipeline_steps_hint.config(text="Этапы не определены для текущего сценария.")
            except Exception:
                try:
                    self._from_combo["values"] = [""]
                    self._pipeline_steps_hint.config(text="Этапы недоступны (ошибка чтения пайплайна).")
                except Exception:
                    pass

        def on_depth_change(*args):
            d = depth_var.get()
            self.update_config("CHECK_DEPTH", d)
            methods = self.METHODS_BY_DEPTH.get(d, self.METHODS_BY_DEPTH["2"])
            try:
                import _Starter
                cfg = getattr(self, "config", None) or {}
                avail = _Starter.list_available_methods(d, folder_override=cfg)
                if avail:
                    methods = [m for m in methods if m in avail]
            except Exception:
                pass
            prev_code = method_from_display(method_var.get())
            displays = [method_display(m) for m in methods]
            method_combo["values"] = displays
            if prev_code in methods:
                method_var.set(method_display(prev_code))
            else:
                method_var.set(method_display(methods[0]) if methods else "")
            self.update_config("SEARH_METH", method_from_display(method_var.get()))
            _update_pipeline_from_combo()

        def on_method_change(*args):
            self.update_config("SEARH_METH", method_from_display(method_var.get()))
            _update_pipeline_from_combo()

        depth_var.trace("w", on_depth_change)
        method_var.trace("w", on_method_change)
        on_depth_change()  # задать список методов и этапов по текущему уровню
        self._update_pipeline_from_combo = _update_pipeline_from_combo

        # Пропустить этапы (через запятую)
        self.create_entry(params_frame, "PIPELINE_SKIP", "Пропустить этапы (PIPELINE_SKIP):", 5)
        ttk.Label(params_frame, text="(через запятую, например: clang_runner,NEW_3_F_Line_Seg)", font=("", 8)).grid(row=6, column=1, sticky=tk.W, padx=5)
        self.create_entry(params_frame, "AST_SKIP_TIDY", "Быстрый AST без clang-tidy (0/1):", 10)
        ttk.Label(
            params_frame,
            text="1 = быстрее (пропускается этап clang_runner), 0 = полный прогон с диагностикой clang-tidy.",
            font=("", 8),
            foreground="gray",
        ).grid(row=10, column=2, columnspan=2, sticky=tk.W, padx=5)
        self.create_entry(params_frame, "MAX_FILES", "Ограничить число файлов (MAX_FILES):", 11)
        ttk.Label(
            params_frame,
            text="Для smoke-прогона: пусто = без ограничения, число > 0 = анализ только первых N файлов.",
            font=("", 8),
            foreground="gray",
        ).grid(row=11, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        self.create_entry(params_frame, "FILE_EXTENSION", "Расширения исходников (обычно не менять):", 7)
        self.create_entry(params_frame, "FILE_ID_IN_TBL_SEARCH", "Начальный ID файла (служебный параметр):", 8)
        
        ttk.Label(params_frame, text="(CLANG/CLANG_AST/CLANG_AST_NO_SENS — при COMPILE_COMMANDS; для AST/графа нужен CLANG_LIB)", font=("", 8)).grid(row=9, column=1, sticky=tk.W, padx=5)
        
        # Кнопки
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=20)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)
        
        ttk.Button(buttons_frame, text="Сохранить", command=self.save_config).grid(row=0, column=0, padx=5, sticky=(tk.W, tk.E))
        ttk.Button(buttons_frame, text="Отмена", command=self.window.destroy).grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        ttk.Button(buttons_frame, text="Тест подключения к БД", command=self.test_db_connection).grid(row=0, column=2, padx=5, sticky=(tk.W, tk.E))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Привязка прокрутки колесом мыши
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.advanced_keys = ["PIPELINE_FROM", "PIPELINE_SKIP", "FILE_EXTENSION", "FILE_ID_IN_TBL_SEARCH", "DROP_TBL"]
        self.apply_profile_visibility()
    
    def create_entry(self, parent, key, label, row, show=None):
        """Создание поля ввода"""
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=30, show=show)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        var.trace('w', lambda *args: self.update_config(key, var.get()))
        self.entries[key] = (entry, var)
        self.entry_widgets[key] = (lbl, entry)
        return entry

    def apply_profile_visibility(self):
        """Базовый профиль скрывает служебные поля, эксперт показывает всё."""
        is_expert = (self.profile_var.get() == "Эксперт")
        for key in self.advanced_keys:
            widgets = self.entry_widgets.get(key)
            if not widgets:
                continue
            lbl, entry = widgets
            if is_expert:
                lbl.grid()
                entry.grid()
            else:
                lbl.grid_remove()
                entry.grid_remove()

    def _add_status_row(self, parent, key, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
        value = ttk.Label(parent, text="—", foreground="gray", wraplength=320, justify=tk.LEFT)
        value.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
        self.status_labels[key] = value

    def _set_status(self, key, text, color):
        lbl = self.status_labels.get(key)
        if lbl:
            lbl.config(text=text, foreground=color)

    @staticmethod
    def _exists_file(path):
        return bool(path and os.path.isfile(path))

    @staticmethod
    def _exists_dir(path):
        return bool(path and os.path.isdir(path))

    def refresh_statuses(self):
        """Обновить видимые статусы по текущим полям настроек."""
        cfg = dict(self.config or {})
        for key, (_w, var) in self.entries.items():
            if key == "SEARH_METH":
                cfg[key] = method_from_display(var.get())
            else:
                cfg[key] = var.get()

        # База данных
        try:
            conn = psycopg2.connect(
                database=cfg.get('DB_NAME', ''),
                user=cfg.get('DB_USER', ''),
                password=cfg.get('DB_PASS', ''),
                host=cfg.get('DB_HOST', ''),
                port=cfg.get('DB_PORT', ''),
                connect_timeout=3,
            )
            conn.close()
            self._set_status("db", "OK: подключение установлено", "#1a7f37")
        except Exception as e:
            self._set_status("db", "Ошибка: {}".format(str(e)[:120]), "#b42318")

        project = (cfg.get("PATH_FILE") or "").strip()
        if self._exists_dir(project):
            self._set_status("project", "OK: папка найдена", "#1a7f37")
        else:
            self._set_status("project", "Не найдено", "#b42318")

        cc = (cfg.get("COMPILE_COMMANDS") or "").strip()
        if self._exists_file(cc):
            self._set_status("compile_commands", "OK: файл найден", "#1a7f37")
        else:
            self._set_status("compile_commands", "Не найдено (AST-методы недоступны)", "#b42318")

        py = (cfg.get("PATH_PYTHON") or "").strip()
        if not py:
            self._set_status("python", "Не задано (будет использован python3)", "#946200")
        elif self._exists_file(py):
            self._set_status("python", "OK: файл найден", "#1a7f37")
        else:
            self._set_status("python", "Не найдено", "#b42318")

        pid = (cfg.get("PID_SEARCH_PATH") or "").strip()
        if not pid:
            self._set_status("pidsearch", "Не задано", "#946200")
        elif self._exists_file(pid):
            self._set_status("pidsearch", "OK: файл найден", "#1a7f37")
        else:
            self._set_status("pidsearch", "Не найдено", "#b42318")

        cl = (cfg.get("CLANG_LIB") or "").strip()
        if not cl:
            self._set_status("libclang", "Не задано (будет авто-поиск)", "#946200")
        elif self._exists_file(cl):
            self._set_status("libclang", "OK: файл найден", "#1a7f37")
        else:
            self._set_status("libclang", "Не найдено", "#b42318")
    
    def update_config(self, key, value):
        """Обновление значения в конфигурации"""
        self.config[key] = value
    
    def load_current_config(self):
        """Загрузка текущей конфигурации"""
        try:
            config = self.config_manager.load_config()
            self.config = config.copy()
            ui_prof = (config.get("UI_PROFILE") or "Базовый").strip()
            if ui_prof not in ("Базовый", "Эксперт"):
                ui_prof = "Базовый"
            self.profile_var.set(ui_prof)
            self.apply_profile_visibility()
            for key, (widget, var) in self.entries.items():
                if key == "SEARH_METH":
                    continue
                if key == "PIPELINE_FROM":
                    value = config.get("PIPELINE_FROM") or config.get("CLANG_AST_FROM", "")
                else:
                    value = config.get(key, "")
                if isinstance(widget, ttk.Combobox):
                    opts = widget["values"] if widget["values"] else []
                    if value in opts:
                        var.set(value)
                    elif key == "PIPELINE_FROM" and value:
                        var.set(value)
                else:
                    var.set(value)
            # После загрузки: список методов по уровню (подписи), значение — подпись; в self.config — код
            depth_var = self.entries["CHECK_DEPTH"][1]
            method_combo, method_var = self.entries["SEARH_METH"]
            d = depth_var.get()
            methods = self.METHODS_BY_DEPTH.get(d, self.METHODS_BY_DEPTH["2"])
            try:
                import _Starter
                avail = _Starter.list_available_methods(d, folder_override=self.config)
                if avail:
                    methods = [m for m in methods if m in avail]
            except Exception:
                pass
            method_combo["values"] = [method_display(m) for m in methods]
            code = (config.get("SEARH_METH", "") or "ALL").strip()
            if code not in methods:
                code = methods[0] if methods else "ALL"
            method_var.set(method_display(code))
            self.config["SEARH_METH"] = code
            try:
                self._update_pipeline_from_combo()
                pf = (config.get("PIPELINE_FROM") or config.get("CLANG_AST_FROM", "")).strip()
                if pf:
                    for disp in self._from_combo["values"]:
                        if isinstance(disp, str) and disp.endswith(": " + pf):
                            self.entries["PIPELINE_FROM"][1].set(disp)
                            break
            except Exception:
                pass
            # Автоподстановка CLANG_LIB при пустом значении (поиск libclang в стандартных путях)
            if "CLANG_LIB" in self.entries and not (self.config.get("CLANG_LIB") or "").strip():
                paths = self.find_libclang_paths()
                if paths:
                    self.config["CLANG_LIB"] = paths[0]
                    self.entries["CLANG_LIB"][1].set(paths[0])
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка загрузки конфигурации: {}".format(str(e)))
    
    def save_config(self):
        """Сохранение конфигурации"""
        try:
            # Обновление всех значений из полей ввода (SEARH_METH в файл — всегда код, не подпись)
            for key, (widget, var) in self.entries.items():
                if key == "SEARH_METH":
                    self.config[key] = method_from_display(var.get())
                elif key == "PIPELINE_FROM":
                    # Иначе в файл уйдёт «4/9: clang_ast_runner», а _Starter ищет только clang_ast_runner
                    self.config[key] = _normalize_pipeline_from(var.get())
                else:
                    self.config[key] = var.get()
            self.config["UI_PROFILE"] = self.profile_var.get()

            # Валидация: базовые поля
            proj = (self.config.get("PATH_FILE") or "").strip()
            if not proj or not os.path.isdir(proj):
                messagebox.showerror("Ошибка", "PATH_FILE должен указывать на существующую папку проекта.")
                return
            # Порт
            port = (self.config.get("DB_PORT") or "").strip()
            try:
                int(port)
            except Exception:
                messagebox.showerror("Ошибка", "DB_PORT должен быть числом.")
                return
            # CLANG/AST методы требуют compile_commands.json
            method = (self.config.get("SEARH_METH") or "").strip()
            if method in ("CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"):
                cc = (self.config.get("COMPILE_COMMANDS") or "").strip()
                if not cc or not os.path.isfile(cc):
                    messagebox.showerror(
                        "Ошибка",
                        "Для метода {} требуется существующий файл COMPILE_COMMANDS (compile_commands.json).".format(method),
                    )
                    return
            # libclang — если задан явно, файл должен существовать
            clang_lib = (self.config.get("CLANG_LIB") or "").strip()
            if clang_lib and not os.path.isfile(clang_lib):
                messagebox.showerror("Ошибка", "CLANG_LIB указан, но файл не найден:\n{}".format(clang_lib))
                return
            
            self.config_manager.save_config(self.config)
            messagebox.showinfo("Успех", "Конфигурация сохранена успешно")
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка сохранения конфигурации: {}".format(str(e)))
    
    def test_db_connection(self):
        """Проверка подключения к БД PostgreSQL по текущим настройкам."""
        try:
            # Берём текущую конфигурацию и накрываем её текущими значениями полей
            cfg = self.config_manager.load_config()
            for key, (widget, var) in self.entries.items():
                if key == "SEARH_METH":
                    cfg[key] = method_from_display(var.get())
                elif key == "PIPELINE_FROM":
                    cfg[key] = _normalize_pipeline_from(var.get())
                else:
                    cfg[key] = var.get()
            
            conn = psycopg2.connect(
                database=cfg.get('DB_NAME', ''),
                user=cfg.get('DB_USER', ''),
                password=cfg.get('DB_PASS', ''),
                host=cfg.get('DB_HOST', ''),
                port=cfg.get('DB_PORT', ''),
                connect_timeout=15,
            )
            conn.close()
            messagebox.showinfo("Проверка подключения", "Подключение к базе данных выполнено успешно.")
            self.refresh_statuses()
        except Exception as e:
            messagebox.showerror("Проверка подключения", "Ошибка подключения к БД: {}".format(str(e)))
            self.refresh_statuses()
    
    def browse_folder(self, entry_widget, config_key):
        """Выбор папки"""
        folder = filedialog.askdirectory(title="Выберите папку проекта")
        if folder:
            _, var = self.entries[config_key]
            var.set(folder)
    
    def browse_file(self, entry_widget, config_key):
        """Выбор файла"""
        filename = filedialog.askopenfilename(title="Выберите файл Python")
        if filename:
            _, var = self.entries[config_key]
            var.set(filename)
    
    def browse_compile_commands(self, entry_widget, config_key):
        """Выбор файла compile_commands.json (каталог build после сборки CMake)"""
        filename = filedialog.askopenfilename(
            title="Выберите файл команд компиляции (compile_commands.json)",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*")]
        )
        if filename:
            _, var = self.entries[config_key]
            var.set(filename)

    @staticmethod
    def find_libclang_paths():
        """Поиск libclang.so в стандартных путях (LLVM 16, 19, 14, 6.0). Возвращает список путей."""
        candidates = []
        for ver in ["16", "19", "14", "6.0"]:
            path = os.path.join("/usr", "lib", "llvm-" + ver, "lib", "libclang.so.1")
            if os.path.isfile(path):
                candidates.append(path)
            path_alt = os.path.join("/usr", "lib", "llvm-" + ver, "lib", "libclang-{}.so.1".format(ver))
            if os.path.isfile(path_alt) and path_alt not in candidates:
                candidates.append(path_alt)
        return candidates

    def auto_fill_clang_lib(self, entry_widget, config_key):
        """Подставить первый найденный путь к libclang (кнопка «Найти»)."""
        paths = self.find_libclang_paths()
        if paths:
            _, var = self.entries[config_key]
            var.set(paths[0])
            self.config[config_key] = paths[0]
            messagebox.showinfo("CLANG_LIB", "Подставлен путь:\n{}".format(paths[0]))
        else:
            messagebox.showwarning(
                "CLANG_LIB",
                "Библиотека libclang не найдена в стандартных путях.\n"
                "Установите LLVM и привязки (см. SETUP_GUIDE.md):\n"
                "  sudo apt install llvm-16 python3-clang-16\n"
                "  pip3 uninstall libclang"
            )

    def browse_libclang(self, entry_widget, config_key):
        """Выбор файла библиотеки libclang (.so, .so.1)."""
        filename = filedialog.askopenfilename(
            title="Выберите библиотеку libclang (libclang.so.1 или libclang-16.so.1)",
            filetypes=[("Библиотеки", "*.so*"), ("Все файлы", "*")]
        )
        if filename:
            _, var = self.entries[config_key]
            var.set(filename)
    
    def browse_log_file(self, entry_widget, config_key):
        """Выбор пути и имени файла лога анализа (.txt) — запись в реальном времени"""
        filename = filedialog.asksaveasfilename(
            title="Укажите файл лога анализа (путь и имя)",
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*")]
        )
        if filename:
            _, var = self.entries[config_key]
            var.set(filename)
    
    def show(self):
        """Показ окна"""
        self.window.wait_window()

