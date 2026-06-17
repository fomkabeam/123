# -*- coding: utf-8 -*-
"""
Экспорт таблиц БД в CSV. Только таблицы, соответствующие вкладкам «Просмотр результатов».
Для каждой таблицы предлагается имя файла по умолчанию = имя таблицы в БД, можно изменить.
"""
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from gui_config import ConfigManager

# Таблицы, которые есть в «Просмотр результатов» (вкладки Статистика, Файлы, Классы, Функции и т.д.)
TABLES_IN_RESULTS = [
    "ccc_file_list",
    "ccc_class_list",
    "ccc_definition_function",
    "ccc_variables_v",
    "ccc_connect_list",
    "ccc_line_seg",
    "ccc_sensor_registry",
    "ccc_sensoragramma",
    "ccc_report",
    "clang_diagnostics",
]


class ExportCsvWindow(tk.Toplevel):
    """Окно экспорта таблиц БД в CSV (только таблицы из Просмотр результатов)."""

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent)
        self.title("Экспорт таблиц в CSV")
        self.geometry("500x450")
        self.config_manager = config_manager
        self.tables = []
        self._create_widgets()
        self._load_tables()

    def _create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        ttk.Label(main, text="Выберите таблицы для экспорта (Ctrl/Shift — несколько):").pack(anchor=tk.W)
        list_frame = ttk.Frame(main)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        scroll = ttk.Scrollbar(list_frame)
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=15, yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Экспорт выбранных", command=self._export_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Экспорт всех", command=self._export_all).pack(side=tk.LEFT, padx=5)

    def _load_tables(self):
        self.tables = list(TABLES_IN_RESULTS)
        self.listbox.delete(0, tk.END)
        for t in self.tables:
            self.listbox.insert(tk.END, t)

    def _get_connection(self):
        config = self.config_manager.load_config()
        import psycopg2
        return psycopg2.connect(
            database=config['DB_NAME'],
            user=config['DB_USER'],
            password=config['DB_PASS'],
            host=config['DB_HOST'],
            port=config['DB_PORT'],
        )

    def _export_tables(self, tables_to_export):
        if not tables_to_export:
            messagebox.showinfo("Подсказка", "Выберите хотя бы одну таблицу.")
            return
        try:
            conn = self._get_connection()
            cur = conn.cursor()
        except Exception as e:
            messagebox.showerror("Ошибка", "Подключение к БД: {}".format(e))
            return
        exported = 0
        for table in tables_to_export:
            path = filedialog.asksaveasfilename(
                title="Сохранить таблицу «{}»".format(table),
                defaultextension=".csv",
                initialfile=table + ".csv",
                filetypes=[("CSV", "*.csv"), ("Все файлы", "*")]
            )
            if not path:
                continue
            try:
                # Имя таблицы только из нашего списка; кавычки для поддержки смешанного регистра в PostgreSQL
                safe_name = '"' + table.replace('"', '""') + '"'
                cur.execute("SELECT * FROM {}".format(safe_name))
                col_names = [d[0] for d in cur.description]
                rows = cur.fetchall()
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(col_names)
                    for row in rows:
                        writer.writerow([str(x) if x is not None else "" for x in row])
                exported += 1
            except Exception as e:
                messagebox.showerror("Ошибка", "Таблица «{}»: {}".format(table, e))
        conn.close()
        if exported:
            messagebox.showinfo("Готово", "Экспортировано таблиц: {}.".format(exported))

    def _export_selected(self):
        sel = self.listbox.curselection()
        tables_to_export = [self.tables[i] for i in sel if 0 <= i < len(self.tables)]
        self._export_tables(tables_to_export)

    def _export_all(self):
        self._export_tables(list(self.tables))
