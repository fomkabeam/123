# -*- coding: utf-8 -*-
"""
Окно «Анализ критических маршрутов» (РД НДВ): список информационных объектов из таблицы
переменных (ccc_variables_v) или вручную; поиск сегментов (ccc_line_seg), в которых они участвуют.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

from gui_config import ConfigManager

try:
    from critical_routes import get_connection, run_analysis
except ImportError:
    get_connection = None
    run_analysis = None


class CriticalRoutesWindow(tk.Toplevel):
    """Окно анализа критических маршрутов: выбор переменных из БД или ввод списка."""

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent)
        self.title("Анализ критических маршрутов")
        self.geometry("800x600")
        self.config_manager = config_manager
        self.variables_from_db = []  # список (var_name,) после загрузки из БД
        self._create_widgets()

    def _create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        # Блок: переменные из БД
        db_frame = ttk.LabelFrame(main, text="Переменные из БД (таблица ccc_variables_v)", padding=5)
        db_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        db_frame.columnconfigure(0, weight=1)
        db_frame.rowconfigure(1, weight=1)
        btn_db = ttk.Button(db_frame, text="Загрузить переменные из БД", command=self._load_from_db)
        btn_db.grid(row=0, column=0, sticky=tk.W, pady=2)
        list_frame = ttk.Frame(db_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        scroll = ttk.Scrollbar(list_frame)
        self.listbox_db = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10, yscrollcommand=scroll.set)
        self.listbox_db.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scroll.config(command=self.listbox_db.yview)
        scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        ttk.Label(main, text="Или введите имена переменных вручную (по одному на строку) / загрузите из файла:").pack(anchor=tk.W, pady=(5, 0))
        self.text_vars = scrolledtext.ScrolledText(main, height=4, wrap=tk.WORD)
        self.text_vars.pack(fill=tk.X, pady=5)
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="Загрузить из файла…", command=self._load_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="Выполнить анализ", command=self._run).pack(side=tk.LEFT, padx=5)
        ttk.Label(main, text="Результат (сегменты, затрагивающие заданные объекты):").pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(
            main,
            text="Сегмент — блок управления (IF, FOR, WHILE, SWITCH, ELSE) из ccc_line_seg. Критический маршрут — путь выполнения кода через такие блоки, затрагивающий выбранные переменные (РД НДВ).",
            font=("", 8),
            foreground="gray",
        ).pack(anchor=tk.W)
        self.text_result = scrolledtext.ScrolledText(main, height=12, wrap=tk.WORD)
        self.text_result.pack(fill=tk.BOTH, expand=True, pady=5)

    def _load_from_db(self):
        if not get_connection:
            messagebox.showerror("Ошибка", "Модуль critical_routes не найден.")
            return
        try:
            config = self.config_manager.load_config()
            import psycopg2
            conn = psycopg2.connect(
                database=config['DB_NAME'],
                user=config['DB_USER'],
                password=config['DB_PASS'],
                host=config['DB_HOST'],
                port=config['DB_PORT'],
            )
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT v.var_name
                FROM ccc_variables_v v
                ORDER BY v.var_name
            """)
            self.variables_from_db = [row[0] for row in cur.fetchall() if row[0]]
            conn.close()
        except Exception as e:
            messagebox.showerror("Ошибка", "Не удалось загрузить переменные из БД: {}".format(e))
            return
        self.listbox_db.delete(0, tk.END)
        for name in self.variables_from_db:
            self.listbox_db.insert(tk.END, name)
        messagebox.showinfo("Готово", "Загружено переменных: {}.\nВыделите нужные и нажмите «Выполнить анализ».".format(len(self.variables_from_db)))
        self.after(50, self._bring_window_front)

    def _bring_window_front(self):
        """Вернуть окно на передний план после messagebox."""
        self.lift()
        self.focus_force()

    def _load_file(self):
        path = filedialog.askopenfilename(
            title="Файл со списком переменных (одно имя на строку)",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*")]
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.text_vars.delete("1.0", tk.END)
                    self.text_vars.insert(tk.END, f.read())
            except Exception as e:
                messagebox.showerror("Ошибка", "Не удалось прочитать файл: {}".format(e))

    def _run(self):
        if not get_connection or not run_analysis:
            messagebox.showerror("Ошибка", "Модуль critical_routes не найден.")
            return
        names = []
        sel = self.listbox_db.curselection()
        if sel:
            for i in sel:
                if i < len(self.variables_from_db):
                    names.append(self.variables_from_db[i])
        if not names:
            text = self.text_vars.get("1.0", tk.END)
            names = [s.strip() for s in text.splitlines() if s.strip()]
        if not names:
            messagebox.showinfo("Подсказка", "Загрузите переменные из БД и выделите нужные, либо введите имена в текстовое поле (или загрузите из файла).")
            return
        self.text_result.delete("1.0", tk.END)
        try:
            conn = get_connection()
        except Exception as e:
            messagebox.showerror("Ошибка", "Подключение к БД: {}".format(e))
            return
        try:
            rows, stats = run_analysis(conn, names)
            conn.close()
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            messagebox.showerror("Ошибка", "Ошибка анализа: {}".format(e))
            return
        if stats.get("table_missing"):
            self.text_result.insert(
                tk.END,
                "Таблица ccc_line_seg или ccc_variables_v отсутствует в БД.\n"
                "Выполните анализ с 2-м уровнем контроля (метод ALL или LS), затем повторите."
            )
            return
        self.text_result.insert(tk.END, "Выбрано переменных: {}.\n".format(stats["total_vars_checked"]))
        self.text_result.insert(
            tk.END,
            "Из них сегменты найдены для: {}  |  без сегментов: {}  |  всего записей сегментов: {}.\n\n".format(
                stats["vars_with_segments"], stats["vars_without_segments"], stats["total_segment_hits"]
            )
        )
        self.text_result.insert(
            tk.END,
            "Пояснение: в ccc_line_seg попадают только блоки управления (IF, FOR, WHILE, SWITCH, ELSE). "
            "Переменные вне таких блоков (объявление в начале функции, «плоский» код) не попадут ни в один сегмент — это нормально.\n"
            "Показанные ниже сегменты — это маршруты, затрагивающие выбранные переменные; их рассматривают как кандидаты в критические маршруты (РД НДВ, п. 3.4.3).\n\n"
        )
        if not rows:
            self.text_result.insert(tk.END, "Нет сегментов, содержащих выбранные переменные (все они вне блоков IF/FOR/WHILE/SWITCH/ELSE).\n")
            return
        self.text_result.insert(tk.END, "Маршруты (сегменты), затрагивающие заданные объекты:\n")
        self.text_result.insert(tk.END, "-" * 70 + "\n")
        for r in rows:
            self.text_result.insert(
                tk.END,
                "  Переменная: {}  |  Файл: {}  |  Функция ID: {}  |  Сегмент: {} (id={})  строки {}-{}\n".format(
                    r[0], r[1], r[2], r[4], r[3], r[5], r[6]
                )
            )
        self.text_result.insert(tk.END, "\nВсего записей: {}".format(len(rows)))
