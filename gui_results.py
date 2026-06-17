# -*- coding: utf-8 -*-
"""
Модуль для просмотра результатов анализа из базы данных
"""

import csv
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import psycopg2

# Таймаут TCP-подключения к PostgreSQL (сек.), чтобы GUI не «висел» при неверном DB_HOST.
_DB_CONNECT_TIMEOUT_SEC = 15

class ResultsViewer:
    """Класс для просмотра результатов анализа"""
    
    def __init__(self):
        pass
    
    def get_db_connection(self, config):
        """Получение подключения к БД"""
        try:
            conn = psycopg2.connect(
                database=config['DB_NAME'],
                user=config['DB_USER'],
                password=config['DB_PASS'],
                host=config['DB_HOST'],
                port=config['DB_PORT'],
                connect_timeout=_DB_CONNECT_TIMEOUT_SEC,
            )
            return conn
        except Exception as e:
            raise Exception("Ошибка подключения к БД: {}".format(str(e)))
    
    def show_results(self, parent, config):
        """
        Отображение результатов в окне.

        Важно: для больших БД используем ленивую загрузку вкладок, чтобы не блокировать GUI
        массовыми fetchall/Treeview insert.
        """
        self._config = config
        self._loaded_tabs = set()
        self._results_parent = parent

        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        try:
            parent.update_idletasks()
        except Exception:
            pass

        # Реестр вкладок: имя -> (frame, loader)
        self._tabs = []

        def add_tab(title, loader):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)
            ttk.Label(frame, text="Загрузка…", foreground="gray").pack(padx=10, pady=10, anchor=tk.W)
            self._tabs.append((title, frame, loader))

        add_tab("Статистика", self._load_statistics)
        add_tab("Файлы", self._load_files)
        add_tab("Классы", self._load_classes)
        add_tab("Функции", self._load_functions)
        add_tab("Переменные", self._load_variables)
        add_tab("Сегменты строк", self._load_line_segments)
        add_tab("Сенсораграмма", self._load_sensoragramma)
        add_tab("Покрытие сенсоров", self._load_sensor_coverage)
        add_tab("Связи между файлами", self._load_connections)
        add_tab("Отчет", self._load_report)
        add_tab("Диагностика кода", self._load_code_diagnostics)

        def on_tab_changed(event=None):
            try:
                idx = notebook.index(notebook.select())
            except Exception:
                return
            if idx < 0 or idx >= len(self._tabs):
                return
            title, frame, loader = self._tabs[idx]
            if title in self._loaded_tabs:
                return
            # Очистка placeholder
            for w in frame.winfo_children():
                w.destroy()
            try:
                # «Статистика» тянет БД в фоне — иначе главный поток Tk зависает на connect/query.
                if title == "Статистика":
                    self._load_statistics(frame, mark_loaded_title=title)
                elif title == "Файлы":
                    self._load_files(frame, mark_loaded_title=title)
                elif title == "Классы":
                    self._load_classes(frame, mark_loaded_title=title)
                elif title == "Функции":
                    self._load_functions(frame, mark_loaded_title=title)
                elif title == "Сегменты строк":
                    self._load_line_segments(frame, mark_loaded_title=title)
                elif title == "Сенсораграмма":
                    self._load_sensoragramma(frame, mark_loaded_title=title)
                elif title == "Связи между файлами":
                    self._load_connections(frame, mark_loaded_title=title)
                else:
                    loader(frame)
                    self._loaded_tabs.add(title)
            except Exception as e:
                self._loaded_tabs.add(title)
                tk.Label(frame, text="Ошибка: {}".format(e), fg="red").pack(padx=10, pady=10, anchor=tk.W)

        notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
        # Загрузить первую вкладку сразу
        parent.after(0, on_tab_changed)
    
    def create_table_view(self, parent, columns, query, cursor, page_size=500):
        """
        Создание табличного представления.

        Для больших таблиц автоматически добавляем постраничный вывод, если в запросе нет LIMIT.
        """
        # Создание Treeview с прокруткой
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        top = ttk.Frame(frame)
        top.grid(row=0, column=0, sticky=(tk.W, tk.E))
        top.columnconfigure(0, weight=1)
        status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=status_var, foreground="gray").grid(row=0, column=0, sticky=tk.W)

        tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # Настройка колонок
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor=tk.W)
        
        paging = "limit" not in (query or "").lower()
        offset = 0

        def load_page(new_offset):
            nonlocal offset
            offset = max(0, int(new_offset))
            for item in tree.get_children():
                tree.delete(item)
            try:
                if paging:
                    q = query.rstrip().rstrip(";") + " LIMIT %s OFFSET %s"
                    cursor.execute(q, (page_size, offset))
                else:
                    cursor.execute(query)
                # fetchmany, чтобы не держать всё в памяти
                total = 0
                while True:
                    rows = cursor.fetchmany(1000)
                    if not rows:
                        break
                    for row in rows:
                        tree.insert('', tk.END, values=row)
                        total += 1
                if paging:
                    status_var.set("Показано: {} (смещение {}), шаг {}".format(total, offset, page_size))
                else:
                    status_var.set("Показано: {}".format(total))
            except Exception as e:
                status_var.set("Ошибка: {}".format(e))
                try:
                    cursor.connection.rollback()
                except Exception:
                    pass

        if paging:
            nav = ttk.Frame(frame)
            nav.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
            ttk.Button(nav, text="← Назад", command=lambda: load_page(offset - page_size)).pack(side=tk.LEFT, padx=5)
            ttk.Button(nav, text="Вперёд →", command=lambda: load_page(offset + page_size)).pack(side=tk.LEFT, padx=5)
            ttk.Button(nav, text="С начала", command=lambda: load_page(0)).pack(side=tk.LEFT, padx=5)

        load_page(0)
        
        tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=1, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=3, column=0, sticky=(tk.W, tk.E))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

    def create_table_view_nonblocking(
        self, parent, columns, base_query, page_size=500, mark_loaded_title=None
    ):
        """
        Постраничная таблица без блокировки главного потока Tk: LIMIT/OFFSET выполняются в фоне.
        Нужна для вкладок с большими таблицами (Файлы, функции и т.д.).
        """
        top = getattr(self, "_results_parent", None) or parent.winfo_toplevel()
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_bar = ttk.Frame(frame)
        top_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        top_bar.columnconfigure(0, weight=1)
        status_var = tk.StringVar(value="Загрузка…")
        ttk.Label(top_bar, textvariable=status_var, foreground="gray").grid(row=0, column=0, sticky=tk.W)

        tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor=tk.W)

        nav = ttk.Frame(frame)
        nav.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        page_size = int(page_size)
        offset_holder = [0]
        marked = [False]

        def mark_once():
            if marked[0] or not mark_loaded_title:
                return
            marked[0] = True
            self._loaded_tabs.add(mark_loaded_title)

        def fetch_and_fill(new_offset):
            off = max(0, int(new_offset))
            status_var.set("Загрузка (смещение {})…".format(off))

            def worker():
                err = None
                rows = None
                try:
                    conn = self.get_db_connection(self._config)
                    conn.autocommit = True
                    cur = conn.cursor()
                    q = base_query.rstrip().rstrip(";") + " LIMIT %s OFFSET %s"
                    cur.execute(q, (page_size, off))
                    rows = cur.fetchall()
                    conn.close()
                except Exception as e:
                    err = e

                def apply():
                    offset_holder[0] = off
                    for item in tree.get_children():
                        tree.delete(item)
                    if err is not None:
                        status_var.set("Ошибка: {}".format(err))
                        mark_once()
                        return
                    for row in rows:
                        tree.insert("", tk.END, values=row)
                    status_var.set(
                        "Строк: {} (смещение {}, шаг {})".format(len(rows), off, page_size)
                    )
                    mark_once()

                top.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(nav, text="← Назад", command=lambda: fetch_and_fill(offset_holder[0] - page_size)).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(nav, text="Вперёд →", command=lambda: fetch_and_fill(offset_holder[0] + page_size)).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(nav, text="С начала", command=lambda: fetch_and_fill(0)).pack(side=tk.LEFT, padx=5)

        tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=1, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=3, column=0, sticky=(tk.W, tk.E))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        fetch_and_fill(0)

    @staticmethod
    def _sensoragramma_column_names(cursor):
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'ccc_sensoragramma'
            """
        )
        return {str(r[0]).lower() for r in cursor.fetchall()}

    @staticmethod
    def _sensoragramma_select_and_order(cols):
        """
        Возвращает (select_sql, order_sql) для нормализованного набора из 8 колонок:
        event_id, sensor_id, pid, parent_pid, ts, run_id, host, payload
        Поддержка новой схемы и устаревшей (id, pid, parent_id, time).
        """
        parts = []
        if "event_id" in cols:
            parts.append("event_id")
        else:
            parts.append("NULL::bigint AS event_id")

        if "sensor_id" in cols:
            parts.append("sensor_id")
        elif "id" in cols:
            parts.append("id AS sensor_id")
        else:
            parts.append("NULL::integer AS sensor_id")

        if "pid" in cols:
            parts.append("pid")
        else:
            parts.append("NULL::integer AS pid")

        if "parent_pid" in cols:
            parts.append("parent_pid")
        elif "parent_id" in cols:
            parts.append("parent_id AS parent_pid")
        else:
            parts.append("NULL::integer AS parent_pid")

        if "ts" in cols:
            parts.append("ts")
        elif "time" in cols:
            parts.append("time AS ts")
        else:
            parts.append("NULL::timestamp AS ts")

        if "run_id" in cols:
            parts.append("run_id")
        else:
            parts.append("NULL::bigint AS run_id")

        if "host" in cols:
            parts.append("COALESCE(host, '') AS host")
        else:
            parts.append("''::text AS host")

        if "payload" in cols:
            parts.append("COALESCE(payload, '') AS payload")
        else:
            parts.append("''::text AS payload")

        if "event_id" in cols:
            order = "event_id DESC"
        elif "ts" in cols:
            order = "ts DESC NULLS LAST, sensor_id DESC NULLS LAST"
        elif "time" in cols:
            order = "time DESC NULLS LAST, id DESC"
        elif "sensor_id" in cols:
            order = "sensor_id DESC"
        elif "id" in cols:
            order = "id DESC"
        else:
            order = "1"

        return ", ".join(parts), order

    def _with_cursor(self):
        conn = self.get_db_connection(self._config)
        conn.autocommit = True
        return conn, conn.cursor()

    # --- Lazy loaders (each opens its own cursor) ---
    def _load_statistics(self, frame, mark_loaded_title=None):
        """
        Вкладка «Статистика»: запросы к БД в фоновом потоке, виджеты — в главном потоке Tk.
        """
        top = getattr(self, "_results_parent", None) or frame.winfo_toplevel()

        def worker():
            err = None
            text = None
            try:
                conn, cur = self._with_cursor()
                try:
                    text = self._collect_statistics_text(cur)
                finally:
                    conn.close()
            except Exception as e:
                err = e

            def apply_ui():
                for w in frame.winfo_children():
                    w.destroy()
                st = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=30)
                st.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                if err is not None:
                    st.insert(tk.END, "Ошибка получения статистики: {}".format(err))
                else:
                    st.insert(tk.END, text or "")
                st.config(state="disabled")
                if mark_loaded_title:
                    self._loaded_tabs.add(mark_loaded_title)

            top.after(0, apply_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _load_files(self, frame, mark_loaded_title=None):
        self.create_table_view_nonblocking(
            frame,
            ("ID", "Путь", "Имя"),
            "SELECT id_file, path, name_rash FROM ccc_file_list ORDER BY id_file",
            page_size=500,
            mark_loaded_title=mark_loaded_title,
        )

    def _load_classes(self, frame, mark_loaded_title=None):
        self.create_table_view_nonblocking(
            frame,
            ("ID класса", "ID файла", "Имя класса"),
            "SELECT classid, id_file, name FROM ccc_class_list ORDER BY id_file",
            page_size=500,
            mark_loaded_title=mark_loaded_title,
        )

    def _load_functions(self, frame, mark_loaded_title=None):
        self.create_table_view_nonblocking(
            frame,
            (
                "ID функции",
                "ID файла",
                "Имя",
                "Параметры",
                "Строка обнаружения",
                "Модификатор/тип",
                "Строка кода",
            ),
            """
                SELECT idfunc, file_id, name, param_func,
                       line_detect, modifier_and_return_type, line
                FROM ccc_definition_function
                ORDER BY file_id, idfunc
            """,
            page_size=500,
            mark_loaded_title=mark_loaded_title,
        )

    def _load_variables(self, frame):
        conn, cur = self._with_cursor()
        try:
            self.show_variables(frame, cur)
        finally:
            conn.close()

    def _load_line_segments(self, frame, mark_loaded_title=None):
        self.create_table_view_nonblocking(
            frame,
            (
                "ID файла",
                "ID класса",
                "ID функции",
                "ID сегмента",
                "Имя",
                "Строка обнаружения",
                "Нач. строка",
                "Кон. строка",
                "Блок?",
                "Тип IF/EL",
            ),
            """
                SELECT file_id, parent_class_id, parent_func_id, line_seg_id,
                       name, line_detect, start_line, end_line, have_block_or_not, L_IF_EL
                FROM ccc_line_seg
                ORDER BY file_id, line_seg_id
            """,
            page_size=500,
            mark_loaded_title=mark_loaded_title,
        )

    def _load_sensoragramma(self, frame, mark_loaded_title=None):
        conn, cur = self._with_cursor()
        try:
            self.show_sensoragramma(frame, cur, mark_loaded_title=mark_loaded_title)
        finally:
            conn.close()

    def _load_sensor_coverage(self, frame):
        conn, cur = self._with_cursor()
        try:
            self.show_sensor_coverage(frame, cur)
        finally:
            conn.close()

    def _load_connections(self, frame, mark_loaded_title=None):
        self.create_table_view_nonblocking(
            frame,
            ("ID файла", "Имя файла", "ID подключения", "Имя подключения", "Строка"),
            """
                SELECT c.id_file, COALESCE(f1.path, '') AS nameFile,
                       c.connectToID, COALESCE(f2.path, '') AS connectToName,
                       c.lineID
                FROM ccc_connect_list c
                LEFT JOIN ccc_file_list f1 ON c.id_file = f1.id_file
                LEFT JOIN ccc_file_list f2 ON c.connectToID = f2.id_file
                ORDER BY c.id_file, c.connectToID
            """,
            page_size=500,
            mark_loaded_title=mark_loaded_title,
        )

    def _load_report(self, frame):
        conn, cur = self._with_cursor()
        try:
            self.show_report(frame, cur)
        finally:
            conn.close()

    def _load_code_diagnostics(self, frame):
        conn, cur = self._with_cursor()
        try:
            self.show_code_diagnostics(frame, cur, self._config)
        finally:
            conn.close()
    
    def _collect_statistics_text(self, cursor):
        """Собрать текст статистики по курсору (можно вызывать из фонового потока)."""
        # Статистика по файлам
        cursor.execute("SELECT COUNT(*) FROM ccc_file_list")
        files_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ccc_connect_list")
        connections_count = cursor.fetchone()[0]

        try:
            cursor.execute("SELECT COUNT(*) FROM ccc_class_list")
            classes_count = cursor.fetchone()[0]
        except Exception:
            classes_count = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM ccc_definition_function")
            functions_count = cursor.fetchone()[0]
        except Exception:
            functions_count = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM ccc_variables_v")
            variables_count = cursor.fetchone()[0]
        except Exception:
            variables_count = 0

        stats = (
            "СТАТИСТИКА АНАЛИЗА\n\n"
            "Файлы:\n"
            "  Всего файлов: {}\n"
            "  Связей между файлами: {}\n\n"
            "Классы:\n"
            "  Всего классов: {}\n\n"
            "Функции:\n"
            "  Всего функций: {}\n\n"
            "Переменные:\n"
            "  Всего переменных: {}\n"
        ).format(files_count, connections_count, classes_count, functions_count, variables_count)

        try:
            cursor.execute("SELECT COUNT(*) FROM ccc_sensor_registry")
            registry_total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ccc_sensoragramma")
            sensor_events = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT sensor_id) FROM ccc_sensoragramma")
            fired_distinct = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT COUNT(DISTINCT r.sensor_id)
                FROM ccc_sensor_registry r
                INNER JOIN ccc_sensoragramma s ON s.sensor_id = r.sensor_id
                """
            )
            covered_registry = cursor.fetchone()[0]
            uncovered_registry = max(registry_total - covered_registry, 0)
            coverage_pct = (float(covered_registry) / float(registry_total) * 100.0) if registry_total else 0.0
            stats += (
                "\nДинамика (сенсоры):\n"
                "  Сенсоров в реестре: {}\n"
                "  Всего событий сенсоров: {}\n"
                "  Уникальных сработавших sensor_id: {}\n"
                "  Покрыто из реестра: {} ({:.2f}%)\n"
                "  Не покрыто из реестра: {}\n"
            ).format(
                registry_total,
                sensor_events,
                fired_distinct,
                covered_registry,
                coverage_pct,
                uncovered_registry,
            )
        except Exception:
            stats += "\nДинамика (сенсоры): данные пока недоступны.\n"
        return stats

    def show_statistics(self, parent, cursor):
        """Отображение статистики (синхронно; для GUI используется _load_statistics)."""
        stats_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, width=80, height=30)
        stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        try:
            stats_text.insert(tk.END, self._collect_statistics_text(cursor))
            stats_text.config(state="disabled")
        except Exception as e:
            stats_text.insert(tk.END, "Ошибка получения статистики: {}".format(str(e)))
            stats_text.config(state="disabled")
    
    def show_files(self, parent, cursor):
        """Отображение списка файлов"""
        try:
            query = "SELECT id_file, path, name_rash FROM ccc_file_list"
            self.create_table_view(parent, ("ID", "Путь", "Имя"), query, cursor)
        except:
            label = tk.Label(parent, text="Таблица файлов не найдена или пуста")
            label.pack(padx=10, pady=10)
    
    def show_classes(self, parent, cursor):
        """Отображение классов"""
        try:
            # В таблице ccc_class_list поля называются classid и id_file
            query = "SELECT classid, id_file, name FROM ccc_class_list"
            self.create_table_view(parent, ("ID класса", "ID файла", "Имя класса"), query, cursor)
        except:
            label = tk.Label(parent, text="Таблица классов не найдена или пуста")
            label.pack(padx=10, pady=10)
    
    def show_functions(self, parent, cursor):
        """Отображение функций"""
        try:
            query = """
                SELECT idfunc, file_id, name, param_func,
                       line_detect, modifier_and_return_type, line
                FROM ccc_definition_function
            """
            self.create_table_view(
                parent,
                (
                    "ID функции", "ID файла", "Имя",
                    "Параметры", "Строка обнаружения",
                    "Модификатор/тип", "Строка кода",
                ),
                query,
                cursor,
            )
        except:
            label = tk.Label(parent, text="Таблица функций не найдена или пуста")
            label.pack(padx=10, pady=10)
    
    def show_variables(self, parent, cursor):
        """Отображение переменных (ccc_definition_variable из Clang или ccc_variables_v)."""
        try:
            cursor.execute("SELECT 1 FROM ccc_definition_variable LIMIT 1")
            cursor.fetchone()
            query = """
                SELECT idvar, file_id, name, var_type, line_detect
                FROM ccc_definition_variable
                ORDER BY file_id, line_detect
                LIMIT 5000
            """
            self.create_table_view(parent, ("ID переменной", "ID файла", "Имя", "Тип", "Строка"), query, cursor)
        except Exception:
            try:
                query = "SELECT var_id, file_id, var_name FROM ccc_variables_v LIMIT 5000"
                self.create_table_view(parent, ("ID переменной", "ID файла", "Имя переменной"), query, cursor)
            except Exception:
                label = tk.Label(parent, text="Таблица переменных не найдена или пуста.\nВыполните анализ (CLANG_AST или уровень 2 с переменными).")
                label.pack(padx=10, pady=10)

    def show_unused_functions(self, parent, cursor):
        """Отображение неиспользуемых функций (по данным анализа)."""
        try:
            # Если есть представление ccc_not_use_function – используем его.
            # Оно уже отфильтровывает main и operator*.
            # Ограничиваем выборку, чтобы окно не зависало на очень больших проектах
            query = """
                SELECT nf.idfunc,
                       nf.file_id,
                       fl.path,
                       nf.name,
                       nf.line_detect,
                       nf.line
                FROM ccc_not_use_function nf
                LEFT JOIN ccc_file_list fl ON nf.file_id = fl.id_file
                ORDER BY fl.path, nf.line_detect
                LIMIT 5000
            """
            self.create_table_view(
                parent,
                (
                    "ID функции",
                    "ID файла",
                    "Путь файла",
                    "Имя функции",
                    "Строка обнаружения",
                    "Строка кода",
                ),
                query,
                cursor,
            )
        except:
            label = tk.Label(
                parent,
                text="Данные о неиспользуемых функциях не найдены.\n"
                     "Убедитесь, что был выполнен скрипт findUseFunction/findUseFunction_V2."
            )
            label.pack(padx=10, pady=10)

    def show_unused_variables(self, parent, cursor):
        """Отображение неиспользуемых переменных (AST Clang или regex-пайплайн)."""
        try:
            # Сначала пробуем представление из clang_ast_variables
            try:
                cursor.execute("SELECT 1 FROM ccc_not_use_variable_ast LIMIT 1")
                cursor.fetchone()
                has_ast = True
            except Exception:
                has_ast = False
            if has_ast:
                query = """
                    SELECT n.idvar,
                           n.file_id,
                           fl.path,
                           n.name,
                           n.line_detect,
                           n.line,
                           COALESCE(n.scope, '') AS scope,
                           COALESCE(n.severity, '') AS severity,
                           COALESCE(n.has_init, 0) AS has_init,
                           COALESCE(n.is_security_critical, 0) AS is_security_critical
                    FROM ccc_not_use_variable_ast n
                    LEFT JOIN ccc_file_list fl ON n.file_id = fl.id_file
                    ORDER BY CASE n.severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, fl.path, n.line_detect
                    LIMIT 5000
                """
                columns = ("ID", "ID файла", "Путь", "Имя", "Строка", "Код", "Область", "Критичность", "Инициализ.", "Безопасность")
            else:
                query = """
                    SELECT u.VarID,
                           u.id_file,
                           fl.path,
                           v.var_name,
                           v.num_line,
                           v.line
                    FROM ccc_unuseVar u
                    LEFT JOIN ccc_variables_v v ON u.VarID = v.var_id
                    LEFT JOIN ccc_file_list fl ON u.id_file = fl.id_file
                    ORDER BY fl.path, v.num_line
                    LIMIT 5000
                """
                columns = ("ID переменной", "ID файла", "Путь файла", "Имя переменной", "Номер строки", "Строка кода")
            self.create_table_view(parent, columns, query, cursor)
        except:
            label = tk.Label(
                parent,
                text="Данные о неиспользуемых переменных не найдены.\n"
                     "Убедитесь, что был выполнен скрипт usingVariables."
            )
            label.pack(padx=10, pady=10)
    
    def show_connections(self, parent, cursor):
        """Отображение связей между файлами (ccc_connect_list).
        lineID (номер строки #include) заполняется clang_ast_connect при наличии колонки."""
        try:
            # JOIN с ccc_file_list; lineID есть после обновления clang_ast_connect
            query = """
                SELECT c.id_file, COALESCE(f1.path, '') AS nameFile,
                       c.connectToID, COALESCE(f2.path, '') AS connectToName,
                       c.lineID
                FROM ccc_connect_list c
                LEFT JOIN ccc_file_list f1 ON c.id_file = f1.id_file
                LEFT JOIN ccc_file_list f2 ON c.connectToID = f2.id_file
                ORDER BY c.id_file, c.connectToID
            """
            self.create_table_view(parent, ("ID файла", "Имя файла", "ID подключения", "Имя подключения", "Строка"), query, cursor)
        except Exception:
            try:
                # Старая схема без колонки lineID
                query = """
                    SELECT c.id_file, COALESCE(f1.path, '') AS nameFile,
                           c.connectToID, COALESCE(f2.path, '') AS connectToName,
                           NULL::integer AS lineID
                    FROM ccc_connect_list c
                    LEFT JOIN ccc_file_list f1 ON c.id_file = f1.id_file
                    LEFT JOIN ccc_file_list f2 ON c.connectToID = f2.id_file
                    ORDER BY c.id_file, c.connectToID
                """
                self.create_table_view(parent, ("ID файла", "Имя файла", "ID подключения", "Имя подключения", "Строка"), query, cursor)
            except Exception:
                label = tk.Label(parent, text="Таблица связей не найдена или пуста")
                label.pack(padx=10, pady=10)
    
    def _report_ru_section(self, name):
        """Русские названия секций отчёта (из ccc_report)."""
        s = (name or "").strip().lower()
        if s == "files":
            return "Файлы"
        if s == "functions":
            return "Функции"
        if s == "variables":
            return "Переменные"
        return name

    def _report_ru_row(self, name):
        """Русские названия строк отчёта (поддержка старых записей на английском)."""
        ru = {
            "files": "Файлов", "file link": "Файлов со связями",
            "files not have link": "Файлов без связей", "percentage ratio files": "Доля файлов со связями (%)",
            "functions": "Функций", "functions link": "Функций со связями",
            "functions not have link": "Функций без связей", "percentage ratio functions": "Доля функций со связями (%)",
            "variables": "Переменных", "variables link": "Переменных со связями",
            "variables not have link": "Переменных без связей", "percentage ratio variables": "Доля переменных со связями (%)",
        }
        key = (name or "").strip().lower()
        return ru.get(key, name)

    def show_report(self, parent, cursor):
        """Отображение отчёта (общая статистика из ccc_report + проблемы из clang_diagnostics), на русском."""
        report_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, width=80, height=30)
        report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        root = parent.winfo_toplevel()
        def copy_selection(event=None):
            try:
                sel = report_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if sel:
                    root.clipboard_clear()
                    root.clipboard_append(sel)
            except tk.TclError:
                pass
        report_text.bind("<Control-c>", copy_selection)

        try:
            report = "ОТЧЁТ ПО РЕЗУЛЬТАТАМ АНАЛИЗА\n" + "=" * 50 + "\n\n"
            report += "(Файлы «со связями» — участвуют в #include; функции/переменные «со связями» — вызываются/используются. "
            report += "Без связей: неиспользуемые — см. вкладки «Неиспользуемые функции» и «Неиспользуемые переменные».)\n\n"

            cursor.execute("SELECT name, coll FROM ccc_report")
            rows = cursor.fetchall()
            # Группируем по секциям: при ORDER BY name заголовки *--files--* и т.д. шли первыми, данные — потом.
            # Выводим секции в фиксированном порядке: Файлы, Функции, Переменные.
            section_headers = {"files": "*--files--*", "functions": "*--functions--*", "variables": "*--variables--*"}
            section_names = {
                "files": ("Файлов", "Файлов со связями", "Файлов без связей", "Доля файлов со связями (%)",
                          "Files", "File link", "Files not have link", "Percentage ratio files"),
                "functions": ("Функций", "Функций со связями", "Функций без связей", "Доля функций со связями (%)",
                              "Functions", "Functions link", "Functions not have link", "Percentage ratio functions"),
                "variables": ("Переменных", "Переменных со связями", "Переменных без связей", "Доля переменных со связями (%)",
                              "Variables", "Variables link", "Variables not have link", "Percentage ratio variables"),
            }
            row_map = {r[0]: r[1] for r in rows}
            for key in ("files", "functions", "variables"):
                report += "\n{}:\n".format(self._report_ru_section(key))
                report += "-" * 30 + "\n"
                for name in section_names[key]:
                    if name in row_map:
                        coll = row_map[name]
                        label = self._report_ru_row(name)
                        if coll is not None:
                            report += "  {}: {}\n".format(label, coll)
                        else:
                            report += "  {}\n".format(label)
            if not rows:
                report += "Общая статистика не сформирована. Запустите анализ с методом CO или ALL.\n"

            # Блок проблем из clang_diagnostics
            report += "\n\nПРОБЛЕМЫ (ДИАГНОСТИКА КОДА)\n" + "-" * 40 + "\n"
            try:
                cursor.execute("""
                    SELECT file_path, line, col, severity, check_name, message
                    FROM clang_diagnostics
                    WHERE message NOT LIKE '%file not found%' AND severity != 'note'
                    ORDER BY file_path, line, col
                """)
                diag_rows = cursor.fetchall()
                if diag_rows:
                    for file_path, line, col, severity, check_name, message in diag_rows:
                        report += "  {}:{}:{}  [{}]  {}  — {}\n".format(
                            file_path, line, col, severity, check_name or "", (message or "")[:80]
                        )
                    report += "\nВсего записей: {}.\n".format(len(diag_rows))
                else:
                    report += "  Нет записей (или диагностика не выполнялась).\n"
                    report += "  Укажите COMPILE_COMMANDS и выполните анализ (ALL или CLANG).\n"
            except Exception:
                report += "  Таблица clang_diagnostics недоступна или пуста.\n"

            report_text.insert(tk.END, report)
            report_text.bind("<Key>", lambda e: "break")
            report_text.config(state='normal')

        except Exception as e:
            report_text.insert(tk.END, "Ошибка получения отчёта: {}\n\n".format(str(e)))
            report_text.insert(tk.END, "Возможно, отчёт ещё не был создан. Запустите анализ с методом CO или ALL.")
            report_text.bind("<Key>", lambda e: "break")
            report_text.config(state='normal')

    def show_line_segments(self, parent, cursor):
        """Отображение сегментов строк (ccc_line_seg)."""
        try:
            query = """
                SELECT file_id, parent_class_id, parent_func_id, line_seg_id,
                       name, line_detect, start_line, end_line, have_block_or_not, L_IF_EL
                FROM ccc_line_seg
            """
            self.create_table_view(
                parent,
                (
                    "ID файла", "ID класса", "ID функции", "ID сегмента",
                    "Имя", "Строка обнаружения",
                    "Нач. строка", "Кон. строка",
                    "Блок?", "Тип IF/EL",
                ),
                query,
                cursor,
            )
        except:
            label = tk.Label(parent, text="Таблица ccc_line_seg не найдена или пуста")
            label.pack(padx=10, pady=10)
    
    def show_sensoragramma(self, parent, cursor, mark_loaded_title=None):
        """Отображение данных сенсораграммы (ccc_sensoragramma)."""
        marked = [False]

        def mark_done():
            if mark_loaded_title and not marked[0]:
                marked[0] = True
                self._loaded_tabs.add(mark_loaded_title)

        try:
            cols = self._sensoragramma_column_names(cursor)
            if not cols:
                tk.Label(parent, text="Таблица ccc_sensoragramma не найдена или пуста").pack(
                    padx=10, pady=10
                )
                mark_done()
                return

            base_select, order_by = self._sensoragramma_select_and_order(cols)
            # В таблице — превью payload (полная строка в CSV)
            display_select = base_select.replace(
                "COALESCE(payload, '') AS payload",
                "LEFT(COALESCE(payload, ''), 300) AS payload",
            )

            outer = tk.Frame(parent)
            outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            top = ttk.Frame(outer)
            top.pack(fill=tk.X, pady=(0, 8))
            ttk.Label(
                top,
                text=(
                    "Сырые события ccc_sensoragramma. В таблице показаны первые 300 символов поля «Payload»; "
                    "полный текст — в CSV."
                ),
                wraplength=720,
                justify=tk.LEFT,
            ).pack(side=tk.LEFT, anchor=tk.W)

            def export_all_csv():
                path = filedialog.asksaveasfilename(
                    title="Выгрузить ccc_sensoragramma в CSV",
                    defaultextension=".csv",
                    initialfile="ccc_sensoragramma_events.csv",
                    filetypes=[("CSV", "*.csv"), ("Все файлы", "*")],
                )
                if not path:
                    return
                conn = None
                cur = None
                try:
                    conn = self.get_db_connection(self._config)
                    conn.autocommit = True
                    cur = conn.cursor()
                    q = "SELECT {} FROM ccc_sensoragramma ORDER BY {}".format(base_select, order_by)
                    cur.execute(q)
                    headers = (
                        "event_id",
                        "sensor_id",
                        "pid",
                        "parent_pid",
                        "ts",
                        "run_id",
                        "host",
                        "payload",
                    )
                    with open(path, "w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                        writer.writerow(headers)
                        while True:
                            rows = cur.fetchmany(5000)
                            if not rows:
                                break
                            for row in rows:
                                writer.writerow(["" if x is None else str(x) for x in row])
                    messagebox.showinfo("Готово", "Файл сохранён:\n{}".format(path))
                except Exception as ex:
                    messagebox.showerror("Ошибка экспорта", str(ex))
                finally:
                    if cur is not None:
                        try:
                            cur.close()
                        except Exception:
                            pass
                    if conn is not None:
                        try:
                            conn.close()
                        except Exception:
                            pass

            ttk.Button(top, text="Выгрузить всё в CSV…", command=export_all_csv).pack(
                side=tk.RIGHT, padx=(10, 0)
            )

            frame = ttk.Frame(outer)
            frame.pack(fill=tk.BOTH, expand=True)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(1, weight=1)

            status_var = tk.StringVar(value="")
            ttk.Label(frame, textvariable=status_var, foreground="gray").grid(
                row=0, column=0, sticky=tk.W
            )

            columns = (
                "Event ID",
                "Sensor ID",
                "PID",
                "Parent PID",
                "Время",
                "Run ID",
                "Host",
                "Payload (превью)",
            )
            tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
            scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
            for col in columns:
                tree.heading(col, text=col)
                w = 260 if "Payload" in col else 130
                tree.column(col, width=w, anchor=tk.W)

            page_size = 500
            offset_holder = [0]
            tk_root = parent.winfo_toplevel()

            def load_page(new_offset):
                off = max(0, int(new_offset))
                offset_holder[0] = off
                status_var.set("Загрузка…")
                for item in tree.get_children():
                    tree.delete(item)

                def worker():
                    err = None
                    rows_batch = []
                    try:
                        conn = self.get_db_connection(self._config)
                        conn.autocommit = True
                        cur = conn.cursor()
                        q = "SELECT {} FROM ccc_sensoragramma ORDER BY {} LIMIT %s OFFSET %s".format(
                            display_select, order_by
                        )
                        cur.execute(q, (page_size, off))
                        while True:
                            chunk = cur.fetchmany(1000)
                            if not chunk:
                                break
                            rows_batch.extend(chunk)
                        conn.close()
                    except Exception as e:
                        err = e

                    def apply_ui():
                        if err is not None:
                            status_var.set("Ошибка: {}".format(err))
                            mark_done()
                            return
                        total = 0
                        for row in rows_batch:
                            tree.insert("", tk.END, values=tuple(row))
                            total += 1
                        status_var.set(
                            "Показано: {} (смещение {}), шаг {}".format(total, off, page_size)
                        )
                        mark_done()

                    tk_root.after(0, apply_ui)

                threading.Thread(target=worker, daemon=True).start()

            nav = ttk.Frame(frame)
            nav.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
            ttk.Button(nav, text="← Назад", command=lambda: load_page(offset_holder[0] - page_size)).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(nav, text="Вперёд →", command=lambda: load_page(offset_holder[0] + page_size)).pack(
                side=tk.LEFT, padx=5
            )
            ttk.Button(nav, text="С начала", command=lambda: load_page(0)).pack(side=tk.LEFT, padx=5)

            load_page(0)

            tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            scrollbar_y.grid(row=1, column=1, sticky=(tk.N, tk.S))
            scrollbar_x.grid(row=3, column=0, sticky=(tk.W, tk.E))
            frame.rowconfigure(1, weight=1)
        except Exception as e:
            tk.Label(
                parent,
                text="Не удалось открыть сенсораграмму: {}".format(e),
                fg="red",
                wraplength=720,
                justify=tk.LEFT,
            ).pack(padx=10, pady=10, anchor=tk.W)
            mark_done()

    def show_sensor_coverage(self, parent, cursor):
        """Сводка покрытия: ccc_sensor_registry vs ccc_sensoragramma, непокрытые сенсоры, экспорт CSV."""

        def _table_exists(c, name):
            c.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = %s
                """,
                (name,),
            )
            return c.fetchone() is not None

        outer = tk.Frame(parent)
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if not _table_exists(cursor, "ccc_sensor_registry"):
            tk.Label(
                outer,
                text=(
                    "Таблица ccc_sensor_registry не найдена.\n"
                    "Выполните этап построения реестра (пайплайн с инструментированием и sensor_registry_builder) "
                    "или создайте схему через create_sensoragramma_table.py."
                ),
                justify=tk.LEFT,
                wraplength=720,
            ).pack(anchor=tk.W)
            return

        if not _table_exists(cursor, "ccc_sensoragramma"):
            tk.Label(
                outer,
                text=(
                    "Таблица ccc_sensoragramma не найдена — сравнение с событиями невозможно.\n"
                    "Создайте схему (create_sensoragramma_table.py) и соберите события через приёмник сенсоров."
                ),
                justify=tk.LEFT,
                wraplength=720,
            ).pack(anchor=tk.W)
            try:
                cursor.execute("SELECT COUNT(*) FROM ccc_sensor_registry")
                n = cursor.fetchone()[0]
                ttk.Label(outer, text="Записей в реестре: {}".format(n)).pack(anchor=tk.W, pady=6)
            except Exception:
                pass
            return

        summary_lines = []
        reg_total = covered = uncovered = orphan_ids = events_total = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM ccc_sensor_registry")
            reg_total = int(cursor.fetchone()[0] or 0)
        except Exception as ex:
            summary_lines.append("Реестр: ошибка чтения ({}).".format(ex))

        try:
            cursor.execute("SELECT COUNT(*) FROM ccc_sensoragramma")
            events_total = int(cursor.fetchone()[0] or 0)
        except Exception:
            events_total = 0

        try:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT r.sensor_id)
                FROM ccc_sensor_registry r
                INNER JOIN ccc_sensoragramma s ON s.sensor_id = r.sensor_id
                """
            )
            covered = int(cursor.fetchone()[0] or 0)
            uncovered = max(reg_total - covered, 0)
            pct = (float(covered) / float(reg_total) * 100.0) if reg_total else 0.0
            summary_lines.append("Сенсоров в реестре: {}".format(reg_total))
            summary_lines.append("Записей событий в ccc_sensoragramma: {}".format(events_total))
            summary_lines.append("Уникальных сенсоров сработало (есть в реестре): {}".format(covered))
            summary_lines.append("Не сработало из реестра: {}".format(uncovered))
            summary_lines.append("Покрытие реестра: {:.2f}%".format(pct))
        except Exception as ex:
            summary_lines.append("Покрытие: ошибка ({}).".format(ex))

        try:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT s.sensor_id)
                FROM ccc_sensoragramma s
                LEFT JOIN ccc_sensor_registry r ON r.sensor_id = s.sensor_id
                WHERE r.sensor_id IS NULL
                """
            )
            orphan_ids = int(cursor.fetchone()[0] or 0)
            if orphan_ids:
                summary_lines.append(
                    "Внимание: событий с sensor_id, которых нет в реестре (уникальных ID): {}".format(
                        orphan_ids
                    )
                )
        except Exception:
            pass

        top = ttk.Frame(outer)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            top,
            text=(
                "Сравнение ожидаемых точек (реестр) и фактических срабатываний. "
                "Ниже — сенсоры из реестра, по которым нет ни одного события."
            ),
            wraplength=720,
            justify=tk.LEFT,
        ).pack(side=tk.LEFT, anchor=tk.W)

        def export_uncovered_csv():
            path = filedialog.asksaveasfilename(
                title="Непокрытые сенсоры (реестр без событий)",
                defaultextension=".csv",
                initialfile="sensor_uncovered_from_registry.csv",
                filetypes=[("CSV", "*.csv"), ("Все файлы", "*")],
            )
            if not path:
                return
            conn = None
            cur = None
            try:
                conn = self.get_db_connection(self._config)
                conn.autocommit = True
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT r.sensor_id,
                           COALESCE(r.file_path, ''),
                           r.line_no,
                           COALESCE(r.kind, ''),
                           COALESCE(r.object_type, ''),
                           COALESCE(r.object_name, ''),
                           r.object_id
                    FROM ccc_sensor_registry r
                    LEFT JOIN (SELECT DISTINCT sensor_id FROM ccc_sensoragramma) s
                      ON s.sensor_id = r.sensor_id
                    WHERE s.sensor_id IS NULL
                    ORDER BY r.sensor_id
                    """
                )
                headers = (
                    "sensor_id",
                    "file_path",
                    "line_no",
                    "kind",
                    "object_type",
                    "object_name",
                    "object_id",
                )
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(headers)
                    while True:
                        rows = cur.fetchmany(5000)
                        if not rows:
                            break
                        for row in rows:
                            writer.writerow(["" if x is None else str(x) for x in row])
                messagebox.showinfo("Готово", "Файл сохранён:\n{}".format(path))
            except Exception as ex:
                messagebox.showerror("Ошибка экспорта", str(ex))
            finally:
                if cur is not None:
                    try:
                        cur.close()
                    except Exception:
                        pass
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

        ttk.Button(top, text="Выгрузить все непокрытые (CSV)…", command=export_uncovered_csv).pack(
            side=tk.RIGHT, padx=(10, 0)
        )

        sum_frame = ttk.LabelFrame(outer, text="Сводка", padding=6)
        sum_frame.pack(fill=tk.X, pady=(0, 8))
        sum_text = scrolledtext.ScrolledText(sum_frame, wrap=tk.WORD, height=6, state="normal")
        sum_text.insert(tk.END, "\n".join(summary_lines) if summary_lines else "Нет данных.")
        sum_text.config(state="disabled")
        sum_text.pack(fill=tk.X)

        table_wrap = ttk.LabelFrame(outer, text="Непокрытые сенсоры (постранично)", padding=5)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(1, weight=1)

        status_var = tk.StringVar(value="")
        ttk.Label(table_wrap, textvariable=status_var, foreground="gray").grid(row=0, column=0, sticky=tk.W)

        columns = (
            "Sensor ID",
            "Файл",
            "Строка",
            "Kind",
            "Тип объекта",
            "Имя объекта",
            "object_id",
        )
        tree = ttk.Treeview(table_wrap, columns=columns, show="headings", height=14)
        sy = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=tree.yview)
        sx = ttk.Scrollbar(table_wrap, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        for col in columns:
            tree.heading(col, text=col)
            w = 280 if col in ("Файл", "Имя объекта") else 100
            tree.column(col, width=w, anchor=tk.W)

        page_size = 500
        offset = 0

        def load_page(new_offset):
            nonlocal offset
            offset = max(0, int(new_offset))
            for item in tree.get_children():
                tree.delete(item)
            try:
                q = """
                    SELECT r.sensor_id,
                           COALESCE(r.file_path, ''),
                           r.line_no,
                           COALESCE(r.kind, ''),
                           COALESCE(r.object_type, ''),
                           COALESCE(r.object_name, ''),
                           r.object_id
                    FROM ccc_sensor_registry r
                    LEFT JOIN (SELECT DISTINCT sensor_id FROM ccc_sensoragramma) s
                      ON s.sensor_id = r.sensor_id
                    WHERE s.sensor_id IS NULL
                    ORDER BY r.sensor_id
                    LIMIT %s OFFSET %s
                """
                cursor.execute(q, (page_size, offset))
                total = 0
                while True:
                    rows = cursor.fetchmany(500)
                    if not rows:
                        break
                    for row in rows:
                        tree.insert("", tk.END, values=tuple(row))
                        total += 1
                status_var.set(
                    "Показано: {} (смещение {}), шаг {}".format(total, offset, page_size)
                )
            except Exception as e:
                status_var.set("Ошибка: {}".format(e))
                try:
                    cursor.connection.rollback()
                except Exception:
                    pass

        nav = ttk.Frame(table_wrap)
        nav.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Button(nav, text="← Назад", command=lambda: load_page(offset - page_size)).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(nav, text="Вперёд →", command=lambda: load_page(offset + page_size)).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(nav, text="С начала", command=lambda: load_page(0)).pack(side=tk.LEFT, padx=5)

        load_page(0)

        tree.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        sy.grid(row=1, column=1, sticky=(tk.N, tk.S))
        sx.grid(row=2, column=0, sticky=(tk.W, tk.E))
        table_wrap.rowconfigure(1, weight=1)
    
    def show_code_diagnostics(self, parent, cursor, config=None):
        """Отображение статической диагностики кода (все проверки clang-tidy, в т.ч. доп. из CLANG_TIDY_CHECKS)."""
        columns = ("Файл", "Строка", "Столбец", "Серьёзность", "Проверка", "Сообщение")
        try:
            top = ttk.Frame(parent)
            top.pack(fill=tk.X, padx=10, pady=5)
            hide_include_errors = tk.BooleanVar(value=True)
            hide_notes = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                top,
                text="Скрыть ошибки подключения заголовков — показывать только предупреждения по коду",
                variable=hide_include_errors,
            ).pack(anchor=tk.W)
            cb_notes = ttk.Checkbutton(
                top,
                text="Скрыть примечания (note) — показывать только warning и error",
                variable=hide_notes,
            )
            cb_notes.pack(anchor=tk.W)
            # Фильтр по имени проверки (в т.ч. доп. проверки из CLANG_TIDY_CHECKS)
            filter_frame = ttk.Frame(top)
            filter_frame.pack(anchor=tk.W, pady=3)
            ttk.Label(filter_frame, text="Проверка:").pack(side=tk.LEFT, padx=(0, 5))
            check_filter_var = tk.StringVar(value="Все")
            check_combo = ttk.Combobox(filter_frame, textvariable=check_filter_var, width=50, state="readonly")

            def fill_check_list(c):
                try:
                    c.execute("SELECT DISTINCT check_name FROM clang_diagnostics WHERE check_name IS NOT NULL AND check_name != '' ORDER BY check_name")
                    names = ["Все"] + [r[0] for r in c.fetchall()]
                    check_combo["values"] = names
                except Exception:
                    check_combo["values"] = ["Все"]

            def refresh(c):
                q = """
                    SELECT file_path, line, col, severity, check_name, message
                    FROM clang_diagnostics
                    WHERE 1=1
                """
                params = []
                if hide_include_errors.get():
                    q += " AND message NOT LIKE '%file not found%'"
                if hide_notes.get():
                    q += " AND severity != 'note'"
                cf = check_filter_var.get()
                if cf and cf != "Все":
                    q += " AND check_name = %s"
                    params.append(cf)
                q += " ORDER BY file_path, line, col"
                for i in tree.get_children():
                    tree.delete(i)
                try:
                    if params:
                        c.execute(q, params)
                    else:
                        c.execute(q)
                    for row in c.fetchall():
                        tree.insert("", tk.END, values=tuple((x if x is not None else "") for x in row))
                except Exception:
                    try:
                        c.connection.rollback()
                    except Exception:
                        pass

            fill_check_list(cursor)
            check_combo.pack(side=tk.LEFT, padx=5)
            if config:
                def on_refresh():
                    try:
                        conn = self.get_db_connection(config)
                        conn.autocommit = True
                        cur = conn.cursor()
                        fill_check_list(cur)
                        refresh(cur)
                        conn.close()
                    except Exception:
                        pass
                ttk.Button(filter_frame, text="Обновить", command=on_refresh).pack(side=tk.LEFT, padx=5)

            hide_include_errors.trace_add("write", lambda *a: refresh(cursor))
            hide_notes.trace_add("write", lambda *a: refresh(cursor))
            check_filter_var.trace_add("write", lambda *a: refresh(cursor))

            # Таблица
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
            scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=150, anchor=tk.W)
            tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
            scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)

            refresh(cursor)
        except Exception:
            label = tk.Label(
                parent,
                text="Таблица диагностик не найдена или пуста.\n"
                     "Запустите анализ (метод ALL, CLANG или CLANG_AST) с настроенным COMPILE_COMMANDS в LOG_PATH.txt.\n"
                     "Диагностики заполняются этапом clang_runner (clang-tidy) в пайплайне."
            )
            label.pack(padx=10, pady=10)

    def export_report(self, config, filename):
        """Экспорт отчёта в файл (общая статистика на русском + проблемы из clang_diagnostics)."""
        try:
            conn = self.get_db_connection(config)
            cursor = conn.cursor()
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("ОТЧЁТ ПО РЕЗУЛЬТАТАМ АНАЛИЗА\n")
                f.write("=" * 50 + "\n\n")
                cursor.execute("SELECT name, coll FROM ccc_report")
                rows = cursor.fetchall()
                section_names = {
                    "files": ("Файлов", "Файлов со связями", "Файлов без связей", "Доля файлов со связями (%)",
                              "Files", "File link", "Files not have link", "Percentage ratio files"),
                    "functions": ("Функций", "Функций со связями", "Функций без связей", "Доля функций со связями (%)",
                                  "Functions", "Functions link", "Functions not have link", "Percentage ratio functions"),
                    "variables": ("Переменных", "Переменных со связями", "Переменных без связей", "Доля переменных со связями (%)",
                                  "Variables", "Variables link", "Variables not have link", "Percentage ratio variables"),
                }
                row_map = {r[0]: r[1] for r in rows}
                for key in ("files", "functions", "variables"):
                    f.write("\n{}:\n".format(self._report_ru_section(key)))
                    f.write("-" * 30 + "\n")
                    for name in section_names[key]:
                        if name in row_map:
                            coll = row_map[name]
                            label = self._report_ru_row(name)
                            if coll is not None:
                                f.write("  {}: {}\n".format(label, coll))
                            else:
                                f.write("  {}\n".format(label))
                f.write("\n\nПРОБЛЕМЫ (ДИАГНОСТИКА КОДА)\n")
                f.write("-" * 40 + "\n")
                try:
                    cursor.execute("""
                        SELECT file_path, line, col, severity, check_name, message
                        FROM clang_diagnostics
                        WHERE message NOT LIKE '%file not found%' AND severity != 'note'
                        ORDER BY file_path, line, col
                    """)
                    diag_rows = cursor.fetchall()
                    for file_path, line, col, severity, check_name, message in diag_rows:
                        f.write("  {}:{}:{}  [{}]  {}  — {}\n".format(
                            file_path, line, col, severity, check_name or "", (message or "")[:80]
                        ))
                    f.write("\nВсего записей: {}.\n".format(len(diag_rows)))
                except Exception:
                    f.write("  Таблица clang_diagnostics недоступна или пуста.\n")
            conn.close()
        except Exception as e:
            raise Exception("Ошибка экспорта отчёта: {}".format(str(e)))

