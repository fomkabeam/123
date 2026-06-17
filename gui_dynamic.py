# -*- coding: utf-8 -*-
"""
Окно динамического анализа (сенсоры).
Показывает статистику по таблице ccc_sensoragramma и простое покрытие по сенсорам.
"""

import csv
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import psycopg2

from gui_config import ConfigManager


class DynamicAnalysisWindow(tk.Toplevel):
    """Окно динамического анализа на основе сенсоров (ccc_sensoragramma)."""

    def __init__(self, parent):
        super(DynamicAnalysisWindow, self).__init__(parent)
        self.title("Динамический анализ (сенсоры)")
        self.geometry("800x600")

        self.config_manager = ConfigManager()

        self._create_widgets()
        self._load_and_refresh()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        info_label = ttk.Label(
            main_frame,
            text=(
                "Динамический анализ использует записи, которые сенсоры добавляют в таблицу ccc_sensoragramma.\n"
                "Перед обновлением статистики выполните сценарии работы исследуемого приложения,\n"
                "собранного с сенсорами."
            ),
            justify=tk.LEFT,
        )
        info_label.pack(fill=tk.X, pady=(0, 10))

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            buttons_frame,
            text="Обновить статистику",
            command=self._load_and_refresh,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            buttons_frame,
            text="Экспорт агрегации (CSV)…",
            command=self._export_aggregation_csv,
        ).pack(side=tk.LEFT, padx=5)

        # Статистика
        stats_frame = ttk.LabelFrame(main_frame, text="Сводная статистика", padding=5)
        stats_frame.pack(fill=tk.X, pady=5)

        self.stats_text = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD, height=8)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.stats_text.config(state="disabled")

        table_frame = ttk.LabelFrame(main_frame, text="Срабатывания сенсоров (агрегировано по ID)", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("id", "count", "pids"),
            show="headings",
            height=15,
        )
        self.tree.heading("id", text="ID сенсора")
        self.tree.heading("count", text="Количество срабатываний")
        self.tree.heading("pids", text="PID (уникальные)")
        self.tree.column("id", width=120, anchor=tk.W)
        self.tree.column("count", width=160, anchor=tk.W)
        self.tree.column("pids", width=400, anchor=tk.W)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        extra_frame = ttk.Frame(main_frame)
        extra_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        extra_frame.columnconfigure(0, weight=1)
        extra_frame.columnconfigure(1, weight=1)
        extra_frame.rowconfigure(0, weight=1)

        uncovered_frame = ttk.LabelFrame(extra_frame, text="Непокрытые сенсоры (из реестра)", padding=5)
        uncovered_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 5))
        uncovered_frame.columnconfigure(0, weight=1)
        uncovered_frame.rowconfigure(0, weight=1)
        self.uncovered_tree = ttk.Treeview(
            uncovered_frame,
            columns=("sensor_id", "file_path", "line_no"),
            show="headings",
            height=10,
        )
        self.uncovered_tree.heading("sensor_id", text="Sensor ID")
        self.uncovered_tree.heading("file_path", text="Файл")
        self.uncovered_tree.heading("line_no", text="Строка")
        self.uncovered_tree.column("sensor_id", width=100, anchor=tk.W)
        self.uncovered_tree.column("file_path", width=420, anchor=tk.W)
        self.uncovered_tree.column("line_no", width=80, anchor=tk.W)
        uncovered_scroll = ttk.Scrollbar(uncovered_frame, orient=tk.VERTICAL, command=self.uncovered_tree.yview)
        self.uncovered_tree.configure(yscrollcommand=uncovered_scroll.set)
        self.uncovered_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        uncovered_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        uncovered_btns = ttk.Frame(uncovered_frame)
        uncovered_btns.grid(row=1, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=(5, 0))
        ttk.Button(uncovered_btns, text="Экспорт непокрытых (CSV)…", command=self._export_uncovered_csv).pack(
            side=tk.RIGHT
        )

        top_frame = ttk.LabelFrame(extra_frame, text="Топ срабатываний (sensor_id)", padding=5)
        top_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(5, 0))
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)
        self.top_tree = ttk.Treeview(
            top_frame,
            columns=("sensor_id", "events"),
            show="headings",
            height=10,
        )
        self.top_tree.heading("sensor_id", text="Sensor ID")
        self.top_tree.heading("events", text="Срабатываний")
        self.top_tree.column("sensor_id", width=120, anchor=tk.W)
        self.top_tree.column("events", width=120, anchor=tk.W)
        top_scroll = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=top_scroll.set)
        self.top_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        top_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        top_btns = ttk.Frame(top_frame)
        top_btns.grid(row=1, column=0, columnspan=2, sticky=(tk.E, tk.W), pady=(5, 0))
        ttk.Button(top_btns, text="Экспорт топа (CSV)…", command=self._export_top_hits_csv).pack(side=tk.RIGHT)

    @staticmethod
    def _csv_cell(value):
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(x) for x in value)
        return str(value)

    def _connect_db(self):
        cfg = self.config_manager.load_config()
        if not cfg:
            messagebox.showerror("Ошибка", "Не удалось загрузить конфигурацию LOG_PATH.txt")
            return None, None
        conn = psycopg2.connect(
            database=cfg.get("DB_NAME", ""),
            user=cfg.get("DB_USER", ""),
            password=cfg.get("DB_PASS", ""),
            host=cfg.get("DB_HOST", ""),
            port=cfg.get("DB_PORT", ""),
        )
        conn.autocommit = True
        return conn, conn.cursor()

    def _export_rows_to_csv(self, path, headers, cur):
        """Пишет все строки из уже выполненного cur (порциями)."""
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            while True:
                rows = cur.fetchmany(5000)
                if not rows:
                    break
                for row in rows:
                    writer.writerow([self._csv_cell(x) for x in row])

    def _export_uncovered_csv(self):
        path = filedialog.asksaveasfilename(
            title="Непокрытые сенсоры (реестр без событий)",
            defaultextension=".csv",
            initialfile="sensor_uncovered_from_registry.csv",
            filetypes=[("CSV", "*.csv"), ("Все файлы", "*")],
        )
        if not path:
            return
        conn, cur = self._connect_db()
        if not conn:
            return
        try:
            cur.execute(
                """
                SELECT r.sensor_id, COALESCE(r.file_path, ''), r.line_no
                FROM ccc_sensor_registry r
                LEFT JOIN (SELECT DISTINCT sensor_id FROM ccc_sensoragramma) s ON s.sensor_id = r.sensor_id
                WHERE s.sensor_id IS NULL
                ORDER BY r.sensor_id
                """
            )
            self._export_rows_to_csv(path, ("sensor_id", "file_path", "line_no"), cur)
            messagebox.showinfo("Готово", "Файл сохранён:\n{}".format(path))
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))
        finally:
            conn.close()

    def _export_top_hits_csv(self):
        path = filedialog.asksaveasfilename(
            title="Топ срабатываний по sensor_id",
            defaultextension=".csv",
            initialfile="sensor_hits_by_id.csv",
            filetypes=[("CSV", "*.csv"), ("Все файлы", "*")],
        )
        if not path:
            return
        conn, cur = self._connect_db()
        if not conn:
            return
        try:
            cur.execute(
                """
                SELECT sensor_id, COUNT(*) AS event_count
                FROM ccc_sensoragramma
                GROUP BY sensor_id
                ORDER BY event_count DESC, sensor_id
                """
            )
            self._export_rows_to_csv(path, ("sensor_id", "event_count"), cur)
            messagebox.showinfo("Готово", "Файл сохранён:\n{}".format(path))
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))
        finally:
            conn.close()

    def _export_aggregation_csv(self):
        path = filedialog.asksaveasfilename(
            title="Агрегация срабатываний (sensor_id, количество, PID)",
            defaultextension=".csv",
            initialfile="sensor_aggregation_by_id.csv",
            filetypes=[("CSV", "*.csv"), ("Все файлы", "*")],
        )
        if not path:
            return
        conn, cur = self._connect_db()
        if not conn:
            return
        try:
            cur.execute(
                """
                SELECT sensor_id, COUNT(*) AS event_count, ARRAY_AGG(DISTINCT pid) AS pids
                FROM ccc_sensoragramma
                GROUP BY sensor_id
                ORDER BY sensor_id
                """
            )
            self._export_rows_to_csv(path, ("sensor_id", "event_count", "pids"), cur)
            messagebox.showinfo("Готово", "Файл сохранён:\n{}".format(path))
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))
        finally:
            conn.close()

    def _log_stats(self, text):
        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, text)
        self.stats_text.config(state="disabled")

    def _load_and_refresh(self):
        """Загрузка данных из БД и обновление статистики/таблицы."""
        try:
            cfg = self.config_manager.load_config()
            if not cfg:
                messagebox.showerror("Ошибка", "Не удалось загрузить конфигурацию LOG_PATH.txt")
                return

            conn = psycopg2.connect(
                database=cfg.get("DB_NAME", ""),
                user=cfg.get("DB_USER", ""),
                password=cfg.get("DB_PASS", ""),
                host=cfg.get("DB_HOST", ""),
                port=cfg.get("DB_PORT", ""),
            )
            conn.autocommit = True
            cur = conn.cursor()

            # Общая статистика
            stats_lines = []
            try:
                cur.execute("SELECT COUNT(*) FROM ccc_sensoragramma")
                total_events = cur.fetchone()[0]

                cur.execute("SELECT COUNT(DISTINCT sensor_id) FROM ccc_sensoragramma")
                distinct_sensors = cur.fetchone()[0]

                cur.execute("SELECT COUNT(DISTINCT pid) FROM ccc_sensoragramma")
                distinct_pids = cur.fetchone()[0]

                if total_events > 0:
                    cur.execute(
                        "SELECT MIN(ts), MAX(ts) FROM ccc_sensoragramma WHERE ts IS NOT NULL"
                    )
                    row = cur.fetchone()
                    t_min, t_max = row[0], row[1]
                else:
                    t_min = t_max = None

                stats_lines.append("Всего записей от сенсоров: {}".format(total_events))
                stats_lines.append("Уникальных сенсоров (ID): {}".format(distinct_sensors))
                stats_lines.append("Уникальных PID процессов: {}".format(distinct_pids))
                try:
                    cur.execute("SELECT COUNT(*) FROM ccc_sensor_registry")
                    total_registry = cur.fetchone()[0]
                    cur.execute(
                        """
                        SELECT COUNT(DISTINCT r.sensor_id)
                        FROM ccc_sensor_registry r
                        INNER JOIN ccc_sensoragramma s ON s.sensor_id = r.sensor_id
                        """
                    )
                    covered = cur.fetchone()[0]
                    uncovered = max(total_registry - covered, 0)
                    coverage = (float(covered) / float(total_registry) * 100.0) if total_registry else 0.0
                    stats_lines.append("Сенсоров в реестре: {}".format(total_registry))
                    stats_lines.append("Сработало из реестра: {} (покрытие {:.2f}%)".format(covered, coverage))
                    stats_lines.append("Не сработало из реестра: {}".format(uncovered))
                except Exception:
                    pass
                if t_min and t_max:
                    stats_lines.append("Интервал времени: {}  —  {}".format(t_min, t_max))
                else:
                    stats_lines.append("Интервал времени: нет данных")
            except Exception as e:
                stats_lines.append("Ошибка получения статистики: {}".format(e))

            self._log_stats("\n".join(stats_lines))

            # Агрегация по ID сенсора
            for item in self.tree.get_children():
                self.tree.delete(item)

            try:
                cur.execute(
                    """
                    SELECT sensor_id, COUNT(*) AS cnt, ARRAY_AGG(DISTINCT pid) AS pids
                    FROM ccc_sensoragramma
                    GROUP BY sensor_id
                    ORDER BY sensor_id
                    """
                )
                rows = cur.fetchall()
                for sensor_id, cnt, pids in rows:
                    pids_str = ", ".join(str(p) for p in (pids or []))
                    self.tree.insert("", tk.END, values=(sensor_id, cnt, pids_str))
            except Exception:
                # Если нет таблицы или другой сбой — просто игнорируем, сообщение уже выше
                pass

            for item in self.uncovered_tree.get_children():
                self.uncovered_tree.delete(item)
            try:
                cur.execute(
                    """
                    SELECT r.sensor_id, COALESCE(r.file_path, ''), r.line_no
                    FROM ccc_sensor_registry r
                    LEFT JOIN (SELECT DISTINCT sensor_id FROM ccc_sensoragramma) s ON s.sensor_id = r.sensor_id
                    WHERE s.sensor_id IS NULL
                    ORDER BY r.sensor_id
                    LIMIT 500
                    """
                )
                for sensor_id, file_path, line_no in cur.fetchall():
                    self.uncovered_tree.insert("", tk.END, values=(sensor_id, file_path, line_no))
            except Exception:
                pass

            for item in self.top_tree.get_children():
                self.top_tree.delete(item)
            try:
                cur.execute(
                    """
                    SELECT sensor_id, COUNT(*) AS cnt
                    FROM ccc_sensoragramma
                    GROUP BY sensor_id
                    ORDER BY cnt DESC
                    LIMIT 100
                    """
                )
                for sensor_id, cnt in cur.fetchall():
                    self.top_tree.insert("", tk.END, values=(sensor_id, cnt))
            except Exception:
                pass

            conn.close()

        except Exception as e:
            messagebox.showerror("Ошибка динамического анализа", "{}".format(e))

