import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.scrolledtext as scrolledtext
import threading
from gui_config import ConfigManager
from gui_analyzer import AnalyzerRunner
from gui_results import ResultsViewer
from gui_redundancy import RedundancyWindow
from gui_checksums import DebChecksumWindow, ArchiveChecksumWindow
from gui_graph import CallGraphWindow
from gui_dynamic import DynamicAnalysisWindow
from gui_critical_routes import CriticalRoutesWindow
from gui_export_csv import ExportCsvWindow
from gui_method_labels import method_display, method_from_display, LEGACY_METHOD_CODES

class CppAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализатор C++ кода")
        self.root.geometry("1200x800")
        
        # Инициализация модулей
        self.config_manager = ConfigManager()
        self.analyzer_runner = AnalyzerRunner(self.on_analysis_progress, self.on_analysis_complete)
        self.results_viewer = ResultsViewer()
        
        # Создание интерфейса
        self.create_menu()
        self.create_widgets()
        self.load_config()
        
    def create_menu(self):
        """Создание меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Настройки", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        # Меню "Анализ"
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Анализ", menu=analysis_menu)
        analysis_menu.add_command(label="Запустить анализ", command=self.start_analysis)
        analysis_menu.add_command(label="Остановить", command=self.stop_analysis, state='disabled')
        
        # Меню "Инструменты"
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        tools_menu.add_command(label="Проверка на избыточность", command=self.open_redundancy_window)
        tools_menu.add_command(label="Динамический анализ (сенсоры)", command=self.open_dynamic_window)
        tools_menu.add_command(label="Построение графа вызовов", command=self.open_call_graph_window)
        tools_menu.add_command(label="Диагностика Clang (парсинг AST)", command=self.open_clang_diagnosis)
        tools_menu.add_command(label="КС Deb (MD5 / ГОСТ)", command=self.open_deb_checksums)
        tools_menu.add_command(label="КС архивов (MD5 / ГОСТ)", command=self.open_archive_checksums)
        tools_menu.add_command(label="Анализ критических маршрутов", command=self.open_critical_routes)
        
        # Меню "Результаты"
        results_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Результаты", menu=results_menu)
        results_menu.add_command(label="Просмотр результатов", command=self.view_results)
        results_menu.add_command(label="Экспорт отчета", command=self.export_report)
        results_menu.add_command(label="Экспорт таблиц в CSV…", command=self.open_export_csv)
        
        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Левая панель - настройки и управление
        left_panel = ttk.LabelFrame(main_frame, text="Управление анализом", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_panel.columnconfigure(0, weight=1)
        
        # Настройки базы данных
        db_frame = ttk.LabelFrame(left_panel, text="База данных", padding="5")
        db_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        db_frame.columnconfigure(1, weight=1)
        
        ttk.Label(db_frame, text="Хост:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.db_host_label = ttk.Label(db_frame, text="", foreground="gray")
        self.db_host_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(db_frame, text="База:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.db_name_label = ttk.Label(db_frame, text="", foreground="gray")
        self.db_name_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Путь к проекту
        path_frame = ttk.LabelFrame(left_panel, text="Путь к проекту", padding="5")
        path_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        path_frame.columnconfigure(0, weight=1)
        
        self.project_path_label = ttk.Label(path_frame, text="", foreground="gray", wraplength=300)
        self.project_path_label.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        # Параметры анализа (методы по уровням — по _Starter.py)
        self.METHODS_BY_DEPTH = {
            "4": ["ALL", "FF_PFS", "FF", "PFS", "CO"],
            "3": ["ALL", "FF_PFS", "FF", "PFS", "CO", "ND", "C", "F", "V", "CPI", "ChI", "ADD_JSens", "CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"],
            "2": ["ALL", "FF_PFS", "FF", "PFS", "CO", "ND", "C", "F", "V", "CPI", "ChI", "LS", "ADD_JSens", "CLANG", "CLANG_AST", "CLANG_AST_NO_SENS"],
        }
        params_frame = ttk.LabelFrame(
            left_panel,
            text="Параметры анализа",
            padding="5",
        )
        params_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        params_frame.columnconfigure(1, weight=1)
        ttk.Label(
            params_frame,
            text="Уровень контроля (классификация РД, п. 1.2–1.5):",
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.depth_var = tk.StringVar(value="2")
        self.depth_combo = ttk.Combobox(params_frame, textvariable=self.depth_var,
                                        values=["2", "3", "4"], state="readonly", width=15)
        self.depth_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(params_frame, text="Сценарий анализа (метод):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.method_var = tk.StringVar(value="ALL")
        self.method_combo = ttk.Combobox(params_frame, textvariable=self.method_var, state="readonly", width=34)
        self.method_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        self.method_combo["values"] = self.METHODS_BY_DEPTH["2"]

        def on_depth_changed(*args):
            d = self.depth_var.get()
            methods = self.METHODS_BY_DEPTH.get(d, self.METHODS_BY_DEPTH["2"])
            try:
                import _Starter
                cfg = self.config_manager.load_config() if self.config_manager else {}
                avail = _Starter.list_available_methods(d, folder_override=cfg)
                if avail:
                    methods = [m for m in methods if m in avail]
            except Exception:
                pass
            prev_code = method_from_display(self.method_var.get())
            preferred = prev_code if prev_code in methods else None
            self._apply_method_codes_to_combo(methods, preferred_code=preferred)

        self.depth_var.trace("w", on_depth_changed)
        on_depth_changed()
        ttk.Label(
            params_frame,
            text=(
                "Значения 2 / 3 / 4 соответствуют уровням контроля II / III / IV по недекларированным возможностям; "
                "анализ строится по функциональным и информационным объектам, связям по управлению и данным "
                "(термины РД, п. 2). Контроль документации в программе не выполняется."
            ),
            font=("", 8),
            foreground="gray",
            wraplength=320,
            justify=tk.LEFT,
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(4, 0))

        # Кнопки управления
        buttons_frame = ttk.Frame(left_panel)
        buttons_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        buttons_frame.columnconfigure(0, weight=1)
        
        self.start_button = ttk.Button(buttons_frame, text="Запустить анализ", 
                                       command=self.start_analysis, width=20)
        self.start_button.grid(row=0, column=0, pady=5)
        
        self.stop_button = ttk.Button(buttons_frame, text="Остановить", 
                                     command=self.stop_analysis, state='disabled', width=20)
        self.stop_button.grid(row=1, column=0, pady=5)
        
        self.settings_button = ttk.Button(buttons_frame, text="Настройки", 
                                         command=self.open_settings, width=20)
        self.settings_button.grid(row=2, column=0, pady=5)
        
        self.results_button = ttk.Button(buttons_frame, text="Результаты", 
                                        command=self.view_results, width=20)
        self.results_button.grid(row=3, column=0, pady=5)
        
        # Правая панель - вывод и прогресс
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Прогресс-бар
        progress_frame = ttk.LabelFrame(right_panel, text="Прогресс выполнения", padding="5")
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="Готов к запуску")
        ttk.Label(progress_frame, textvariable=self.progress_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Лог-вывод
        log_frame = ttk.LabelFrame(right_panel, text="Журнал выполнения", padding="5")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=60, height=30)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text.config(state='disabled')
        def copy_log_selection(event=None):
            try:
                sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if sel:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(sel)
            except tk.TclError:
                pass
        self.log_text.bind("<Control-c>", copy_log_selection)
        # Разрешить выделение: при state=normal выделение работает; блокируем ввод
        def block_edit(event):
            if event.state & 0x4 and event.keysym.lower() == 'c':
                copy_log_selection()
            return "break"
        self.log_text.bind("<Key>", block_edit)
        self.log_text.config(state='normal')  # чтобы можно было выделять текст для копирования

    def _apply_method_codes_to_combo(self, codes, preferred_code=None):
        """Список кодов методов → подписи в Combobox; выбранное значение — подпись."""
        displays = [method_display(c) for c in codes]
        self.method_combo["values"] = displays
        if preferred_code and preferred_code in codes:
            pick = preferred_code
        elif codes:
            pick = codes[0]
        else:
            pick = "ALL"
        self.method_var.set(method_display(pick))

    def load_config(self, log_success=False):
        """Загрузка конфигурации и синхронизация с dbFolder/_Starter (чтобы скрипты видели актуальные настройки)."""
        try:
            config = self.config_manager.load_config()
            if config:
                self.db_host_label.config(text=config.get('DB_HOST', 'Не установлен'))
                self.db_name_label.config(text=config.get('DB_NAME', 'Не установлен'))
                path = config.get('PATH_FILE', 'Не установлен')
                self.project_path_label.config(text=path if len(path) < 50 else path[:47] + "...")
                
                depth = config.get('CHECK_DEPTH', '2')
                if depth in ['2', '3', '4']:
                    self.depth_var.set(depth)
                d = self.depth_var.get()
                methods = self.METHODS_BY_DEPTH.get(d, self.METHODS_BY_DEPTH["2"])
                try:
                    import _Starter
                    avail = _Starter.list_available_methods(d, folder_override=config)
                    if avail:
                        methods = [m for m in methods if m in avail]
                except Exception:
                    pass
                code = (config.get("SEARH_METH", "ALL") or "ALL").strip()
                if code not in methods:
                    code = methods[0] if methods else "ALL"
                self._apply_method_codes_to_combo(methods, preferred_code=code)
                # Синхронизация в глобальные folder (dbFolder, _Starter), чтобы анализ и граф использовали настройки из GUI
                try:
                    import dbFolder
                    import _Starter
                    dbFolder.folder.clear()
                    dbFolder.folder.update(config)
                    _Starter.folder.clear()
                    _Starter.folder.update(config)
                except Exception:
                    pass
                if log_success:
                    self.log_message("Конфигурация загружена успешно")
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка загрузки конфигурации: {}".format(str(e)))
            self.log_message("Ошибка загрузки конфигурации: {}".format(str(e)))
    
    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='normal')  # оставляем normal, чтобы можно было выделять и копировать (ввод блокируется в <Key>)
        
    def start_analysis(self):
        """Запуск анализа"""
        depth = self.depth_var.get()
        method = method_from_display(self.method_var.get())
        
        if not depth or not method:
            messagebox.showwarning("Предупреждение", "Выберите параметры анализа")
            return
        
        try:
            # Обновление конфигурации перед запуском
            config = self.config_manager.load_config()
            if not config:
                messagebox.showerror("Ошибка", "Не удалось загрузить конфигурацию")
                return
            
            config['CHECK_DEPTH'] = depth
            config['SEARH_METH'] = method
            self.config_manager.save_config(config)
            if method in LEGACY_METHOD_CODES:
                self.log_message("ВНИМАНИЕ: выбран legacy/fallback метод '{}' (пониженная точность)".format(method))
            if method == "LS":
                if not (config.get("COMPILE_COMMANDS") or "").strip():
                    self.log_message(
                        "LS: COMPILE_COMMANDS не задан — перед сегментами строк используется legacy (findFunction/funcToNormal)."
                    )
                else:
                    self.log_message(
                        "LS: с COMPILE_COMMANDS — сегменты строятся по функциям из clang_ast_runner (без findFunction)."
                    )
            if method in LEGACY_METHOD_CODES and (config.get("COMPILE_COMMANDS") or "").strip():
                self.log_message(
                    "Подсказка: при заданном COMPILE_COMMANDS для основного контура точнее использовать ALL или CLANG_AST."
                )
            
            # Запуск анализа в отдельном потоке
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.progress_bar.start()
            self.progress_var.set("Анализ запущен...")
            self.log_message(
                "Запуск анализа: Уровень={}, Метод={} ({})".format(depth, method, method_display(method))
            )
            
            thread = threading.Thread(target=self.analyzer_runner.run_analysis, args=(config,), daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка запуска анализа: {}".format(str(e)))
            self.log_message("Ошибка: {}".format(str(e)))
            self.on_analysis_complete(False, str(e))
    
    def stop_analysis(self):
        """Остановка анализа"""
        self.analyzer_runner.stop()
        self.log_message("Остановка анализа...")
    
    def on_analysis_progress(self, message):
        """Обработка прогресса анализа (безопасно для потоков)."""
        # Если вызвано из фонового потока – перенаправляем в главный через after.
        import threading
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda m=message: self.on_analysis_progress(m))
            return
        self.log_message(message)
        self.root.update_idletasks()
    
    def on_analysis_complete(self, success, message=""):
        """Обработка завершения анализа (безопасно для потоков)."""
        import threading
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda s=success, m=message: self.on_analysis_complete(s, m))
            return

        self.progress_bar.stop()
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        if success:
            self.progress_var.set("Анализ завершен успешно")
            self.log_message("Анализ завершен успешно")
            messagebox.showinfo("Успех", "Анализ завершен успешно")
        else:
            self.progress_var.set("Анализ завершен с ошибками")
            if message:
                self.log_message("Ошибка: {}".format(message))
                try:
                    import re
                    m = re.search(r"Шаг '([A-Za-z0-9_]+)' завершился с ошибкой", message)
                    if m:
                        failed = m.group(1)
                        self.log_message(
                            "Подсказка: в «Настройки» выберите «Продолжить с этапа» = {} и сохраните конфигурацию.".format(
                                failed
                            )
                        )
                except Exception:
                    pass
                messagebox.showerror("Ошибка", "Анализ завершен с ошибками:\n{}".format(message))
    
    def open_settings(self):
        """Открытие окна настроек"""
        from gui_config import SettingsWindow
        settings_window = SettingsWindow(self.root, self.config_manager)
        settings_window.show()
        # Перезагрузка конфигурации после закрытия окна настроек
        self.load_config(log_success=False)
    
    def view_results(self):
        """Просмотр результатов"""
        try:
            config = self.config_manager.load_config()
            if not config:
                messagebox.showerror("Ошибка", "Не удалось загрузить конфигурацию")
                return
            
            results_window = tk.Toplevel(self.root)
            results_window.title("Результаты анализа")
            results_window.geometry("1000x700")
            
            self.results_viewer.show_results(results_window, config)
            
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка просмотра результатов: {}".format(str(e)))
    
    def export_report(self):
        """Экспорт отчета"""
        try:
            config = self.config_manager.load_config()
            if not config:
                messagebox.showerror("Ошибка", "Не удалось загрузить конфигурацию")
                return
            
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
            )
            
            if filename:
                self.results_viewer.export_report(config, filename)
                messagebox.showinfo("Успех", "Отчет сохранен в {}".format(filename))
                
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка экспорта отчета: {}".format(str(e)))
    
    def show_about(self):
        """Показ информации о программе (окно с прокруткой)."""
        about_text = (
            "Анализатор C++ кода\n\n"
            "Графическая оболочка для статического и динамического анализа исходных текстов программ в рамках контроля отсутствия недекларированных возможностей (НДВ). "
            "Соответствие уровням контроля определяется выполнением набора требований к содержанию испытаний (РД по НДВ); контроль состава и содержания документации (спецификация, описание программы и т.д.) настоящей программой не выполняется.\n\n"
            "Версия 1.0. Разработано для Astra Linux.\n\n"
            "Уровни контроля отсутствия НДВ (CHECK_DEPTH)\n"
            "Устанавливается четыре уровня контроля; каждый уровень характеризуется определённой минимальной совокупностью требований. В программе реализованы второй, третий и четвёртый уровни:\n\n"
            "  Четвёртый уровень контроля — достаточен для ПО, используемого при защите конфиденциальной информации. "
            "Статический анализ: контроль полноты и отсутствия избыточности исходных текстов ПО на уровне файлов; связи между файлами. "
            "Контроль исходного состояния (контрольные суммы) — в разделе «КС архивов» / «КС Deb».\n\n"
            "  Третий уровень контроля — достаточен для ПО при защите информации с грифом «С». "
            "Дополнительно: контроль полноты и отсутствия избыточности на уровне функциональных объектов (процедур, функций); "
            "контроль связей функциональных объектов по управлению и по информации; контроль информационных объектов (переменные и т.п.); "
            "формирование перечня маршрутов выполнения функциональных объектов; динамический анализ (контроль выполнения функциональных объектов, сопоставление фактических маршрутов с маршрутами статического анализа) — сенсоры и сенсораграмма.\n\n"
            "  Второй уровень контроля — достаточен для ПО при защите информации с грифом «СС». "
            "Дополнительно: контроль на уровне функций (в т.ч. неиспользуемые функции); синтаксический контроль конструкций из списка потенциально опасных; "
            "маршруты выполнения на уровне ветвей (сегменты строк); анализ критических маршрутов; построение графа вызовов (диаграммы).\n\n"
            "Параметр CHECK_DEPTH (2, 3 или 4) задаёт сценарий анализа в соответствии с выбранным уровнем контроля по РД.\n\n"
            "Методы поиска (SEARH_METH):\n"
            "  ALL      — полный анализ по всем этапам;\n"
            "  FF       — только поиск файлов;\n"
            "  PFS/FF_PFS — поиск файлов и связей между ними;\n"
            "  C / F / V — только классы / функции / переменные;\n"
            "  CPI      — связи импортов/подключений между файлами;\n"
            "  ChI      — связи вызовов и использований (Communication IO/FO);\n"
            "  CO       — формирование отчёта по уже собранным данным;\n"
            "  ND       — поиск неиспользуемых функций;\n"
            "  ADD_JSens — добавление сенсоров в код;\n"
            "  CLANG    — анализ на базе Clang AST (без сенсоров) + диагностика clang-tidy + отчёт; нужен COMPILE_COMMANDS.\n"
            "  CLANG_AST — полный анализ с разбором функций/вызовов через Clang AST + сенсоры + отчёт; нужен COMPILE_COMMANDS и libclang.\n"
            "  CLANG_AST_NO_SENS — как CLANG_AST, но без сенсоров (сразу отчёт после связей и переменных).\n\n"
            "Диагностика кода (вкладка «Диагностика кода»):\n"
            "Чтобы получать предупреждения по коду (неиспользуемые функции/переменные, мёртвый код), перед анализом:\n"
            "1) В корневой CMakeLists.txt проекта добавьте:\n"
            "   set(CMAKE_EXPORT_COMPILE_COMMANDS ON)\n"
            "2) Выполните сборку СПО (как обычно).\n"
            "3) В настройках укажите путь к файлу команд компиляции — build/compile_commands.json (в настройках: «Файл команд компиляции»).\n"
            "При методе ALL (глубина 2 или 3) диагностика кода выполняется в начале сценария после поиска файлов.\n\n"
            "Если путь к compile_commands.json не задан или файл отсутствует, в журнале выполнения появится сообщение о пропуске диагностики кода (ошибки не блокируют анализ)."
        )
        win = tk.Toplevel(self.root)
        win.title("О программе")
        win.geometry("620x500")
        win.transient(self.root)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        txt = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("TkDefaultFont", 10))
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, about_text)
        def copy_selection(event=None):
            try:
                sel = txt.get(tk.SEL_FIRST, tk.SEL_LAST)
                if sel:
                    win.clipboard_clear()
                    win.clipboard_append(sel)
            except tk.TclError:
                pass
        txt.bind("<Control-c>", copy_selection)
        txt.bind("<Key>", lambda e: "break")  # только чтение, копирование по Ctrl+C
        ttk.Button(frame, text="Закрыть", command=win.destroy).pack(pady=5)

    def open_redundancy_window(self):
        """Открытие окна проверки на избыточность."""
        RedundancyWindow(self.root, self.config_manager)

    def open_dynamic_window(self):
        """Открытие окна динамического анализа (сенсоры)."""
        DynamicAnalysisWindow(self.root)

    def open_call_graph_window(self):
        """Открытие окна построения графа вызовов."""
        CallGraphWindow(self.root, self.config_manager)

    def open_deb_checksums(self):
        """Открытие окна подсчёта КС для .deb пакетов."""
        DebChecksumWindow(self.root)

    def open_archive_checksums(self):
        """Открытие окна подсчёта КС для архивов с исходным кодом."""
        ArchiveChecksumWindow(self.root)

    def open_critical_routes(self):
        """Открытие окна анализа критических маршрутов (список информационных объектов эксперта)."""
        CriticalRoutesWindow(self.root, self.config_manager)

    def open_export_csv(self):
        """Открытие окна экспорта таблиц БД в CSV."""
        ExportCsvWindow(self.root, self.config_manager)

    def open_clang_diagnosis(self):
        """Запуск диагностического скрипта Clang (libclang, compile_commands, парсинг) и вывод результата.

        Важно: запуск производится в фоне, чтобы не блокировать Tk mainloop.
        """
        script_name = "diagnose_clang_parse.py"
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
        else:
            candidates.append(os.path.dirname(os.path.abspath(__file__)))
        candidates.append(os.getcwd())
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "share", "cpp-analyzer"))
        script_path = None
        base_dir = candidates[0]
        for d in candidates:
            p = os.path.join(d, script_name)
            if os.path.isfile(p):
                script_path = p
                base_dir = d
                break
        if not script_path:
            searched = "\n".join("  • {}".format(os.path.join(d, script_name)) for d in candidates)
            messagebox.showerror(
                "Ошибка",
                "Файл diagnose_clang_parse.py не найден.\n\nПроверены каталоги:\n{}\n\nСкопируйте скрипт в каталог приложения (например /opt/cpp-analyzer/) или запустите программу из каталога с исходниками.".format(searched)
            )
            return

        # Окно результата создаём сразу, а наполнение — после фонового запуска.
        win = tk.Toplevel(self.root)
        win.title("Диагностика Clang (парсинг AST)")
        win.geometry("900x600")
        txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt.insert(tk.END, "Выполняется диагностика Clang...\n\n(Окно не блокирует GUI; результат появится здесь.)")
        txt.config(state=tk.DISABLED)

        def _copy_diagnosis():
            try:
                content = txt.get("1.0", tk.END)
                win.clipboard_clear()
                win.clipboard_append(content)
                messagebox.showinfo("Копирование", "Текст скопирован в буфер обмена.")
            except Exception as e:
                messagebox.showerror("Ошибка", "Не удалось скопировать: {}".format(e))
        txt.bind("<Control-c>", lambda e: _copy_diagnosis())
        win.bind("<Control-c>", lambda e: _copy_diagnosis())
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Копировать", command=_copy_diagnosis).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=win.destroy).pack(side=tk.LEFT, padx=5)

        # Tcl/Tk на многих системах не поддерживает символы выше U+FFFF (эмодзи и др.)
        def _sanitize_for_tk(s):
            return "".join(c if ord(c) <= 0xFFFF else "?" for c in s)

        def run_in_background():
            try:
                self.load_config()
                py_exe = "python3" if getattr(sys, "frozen", False) else sys.executable
                proc = subprocess.run(
                    [py_exe, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60,
                    cwd=base_dir,
                )
                out = (proc.stdout or b"").decode("utf-8", errors="replace") + (proc.stderr or b"").decode("utf-8", errors="replace")
                if not out.strip():
                    out = "(пустой вывод, код возврата: {})".format(proc.returncode)
            except subprocess.TimeoutExpired:
                out = "Таймаут выполнения (60 с)."
            except Exception as e:
                out = "Ошибка запуска: {}".format(e)

            out_safe = _sanitize_for_tk(out)

            def apply():
                try:
                    txt.config(state=tk.NORMAL)
                    txt.delete("1.0", tk.END)
                    txt.insert(tk.END, out_safe)
                    txt.config(state=tk.DISABLED)
                except Exception:
                    pass

            self.root.after(0, apply)

        threading.Thread(target=run_in_background, daemon=True).start()

def main():
    """
    Главная функция.

    В режиме сборки (PyInstaller, один исполняемый файл) поддерживается запуск анализа как подпроцесса:
    `cpp-analyzer --analyze` — выполняет пайплайн из `_Starter.py` без GUI и печатает лог в stdout.
    """
    if "--analyze" in sys.argv:
        import runpy
        import traceback
        # Сразу в stdout (для GUI-журнала): распаковка onefile / импорт могут молчать долго без flush.
        try:
            sys.stdout.write("cpp-analyzer: режим --analyze, загрузка...\n")
            sys.stdout.flush()
        except Exception:
            pass
        try:
            import _Starter
        except Exception as e:
            print("ОШИБКА: не удалось импортировать _Starter: {}".format(e))
            return 2

        def _runner(script_name: str):
            # Этапы пайплайна задаются как имена модулей без .py (см. _Starter._run_script).
            try:
                runpy.run_module(script_name, run_name="__main__")
                return 0
            except SystemExit as se:
                try:
                    return int(se.code) if se.code is not None else 0
                except Exception:
                    return 1
            except Exception:
                traceback.print_exc()
                return 1

        try:
            rc = _Starter.main(runner=_runner)
            return 0 if rc is None else int(rc)
        except SystemExit as se:
            try:
                return int(se.code) if se.code is not None else 0
            except Exception:
                return 1
        except Exception:
            traceback.print_exc()
            return 1

    root = tk.Tk()
    app = CppAnalyzerGUI(root)
    root.mainloop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

