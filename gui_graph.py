# -*- coding: utf-8 -*-
"""
Окно «Построение графа вызовов»: запуск GraphAnalyserC++ с конфигурацией из LOG_PATH.txt.
Граф вызовов (call graph) строится по исходникам C++ и экспортируется в PDF.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from gui_config import ConfigManager


class CallGraphWindow(tk.Toplevel):
    """Окно построения графа вызовов (блок-схема с графом вызовов функций)."""

    def __init__(self, parent, config_manager):
        super(CallGraphWindow, self).__init__(parent)
        self.title("Построение графа вызовов")
        self.geometry("750x520")

        self.config_manager = config_manager
        self.stop_event = None
        self.worker_thread = None

        self._create_widgets()
        self._load_defaults()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Путь к проекту C++
        project_frame = ttk.LabelFrame(main_frame, text="Каталог с исходниками C++", padding=5)
        project_frame.pack(fill=tk.X, expand=False, pady=5)
        self.project_var = tk.StringVar()
        ttk.Entry(project_frame, textvariable=self.project_var).pack(fill=tk.X, padx=5, pady=2)

        # Каталог для сохранения графа (PDF)
        out_frame = ttk.LabelFrame(main_frame, text="Каталог для сохранения графа (по умолчанию — graphs)", padding=5)
        out_frame.pack(fill=tk.X, expand=False, pady=5)
        self.output_var = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.output_var).pack(fill=tk.X, padx=5, pady=2)

        mode_frame = ttk.LabelFrame(main_frame, text="Источник узлов", padding=5)
        mode_frame.pack(fill=tk.X, expand=False, pady=5)
        self.use_regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            mode_frame,
            text="Упрощённый анализ (regex) — меньше узлов, без Clang (по умолчанию: Clang, точный анализ)",
            variable=self.use_regex_var,
        ).pack(anchor=tk.W, pady=2)

        filter_frame = ttk.LabelFrame(main_frame, text="Упрощение графа вызовов (graph_calls)", padding=5)
        filter_frame.pack(fill=tk.X, expand=False, pady=5)
        self.filter_std_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            filter_frame,
            text="Исключить вызовы std::, boost::, Qt::",
            variable=self.filter_std_var,
        ).pack(anchor=tk.W, pady=2)
        self.filter_util_var = tk.BooleanVar(value=True)
        self.filter_util_threshold_var = tk.IntVar(value=30)
        ttk.Checkbutton(
            filter_frame,
            text="Скрыть часто вызываемые функции (порог входящих вызовов:",
            variable=self.filter_util_var,
        ).pack(anchor=tk.W, pady=2)
        thresh_frame = ttk.Frame(filter_frame)
        thresh_frame.pack(anchor=tk.W, pady=0)
        self.filter_spin = tk.Spinbox(thresh_frame, from_=5, to=200, width=4, textvariable=self.filter_util_threshold_var)
        self.filter_spin.pack(side=tk.LEFT, padx=(0, 5))
        self.filter_spin.delete(0, tk.END)
        self.filter_spin.insert(0, "30")
        ttk.Label(thresh_frame, text=")").pack(side=tk.LEFT)

        # Кнопки
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, expand=False, pady=10)
        self.run_button = ttk.Button(
            buttons_frame,
            text="Построить граф вызовов",
            command=self._run_build,
        )
        self.run_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(
            buttons_frame,
            text="Остановить",
            command=self._stop_build,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.copy_log_btn = ttk.Button(buttons_frame, text="Копировать журнал", command=self._copy_log)
        self.copy_log_btn.pack(side=tk.LEFT, padx=5)

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Журнал (Ctrl+C — копировать)", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=16)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state="disabled")
        self.log_text.bind("<Control-c>", lambda e: self._copy_log())
        self.bind("<Control-c>", lambda e: self._copy_log())

    def _load_defaults(self):
        try:
            cfg = self.config_manager.load_config()
        except Exception:
            cfg = {}
        self.project_var.set(cfg.get("PATH_FILE", ""))
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_out = os.path.join(base_dir, "GraphAnalyserC++", "graphs")
        self.output_var.set(default_out)

    def _log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _log_safe(self, message):
        if threading.current_thread() is threading.main_thread():
            self._log(message)
        else:
            self.after(0, lambda: self._log(message))

    def _copy_log(self):
        """Копировать содержимое журнала в буфер обмена."""
        try:
            content = self.log_text.get("1.0", tk.END)
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Копирование", "Журнал скопирован в буфер обмена.")
        except Exception as e:
            messagebox.showerror("Ошибка", "Не удалось скопировать: {}".format(e))

    def _show_graph_choice_dialog(self, num_nodes, num_edges, out_dir, result_holder, event):
        """Диалог выбора при большом графе: полный .gv/PDF и фильтрация графа вызовов."""
        dlg = tk.Toplevel(self)
        dlg.title("Построение графа — выбор действий")
        dlg.geometry("560x400")
        dlg.transient(self)
        dlg.grab_set()
        frame = ttk.Frame(dlg, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            frame,
            text="Граф большой: {} узлов, {} рёбер.\nРендер полного PDF может занять много часов.".format(num_nodes, num_edges),
            font=("", 10),
        ).pack(anchor=tk.W, pady=(0, 10))
        var_save_gv = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Сохранить полный исходный граф (graph_full_original.gv) — все узлы и рёбра",
            variable=var_save_gv,
        ).pack(anchor=tk.W, pady=4)
        ttk.Label(frame, text="Что делать с PDF:", font=("", 9)).pack(anchor=tk.W, pady=(10, 4))
        var_pdf = tk.StringVar(value="calls")
        ttk.Radiobutton(
            frame, text="Только граф вызовов (graph_calls.pdf) — быстро", variable=var_pdf, value="calls"
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            frame, text="Полный граф в PDF — может занять много часов", variable=var_pdf, value="full"
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(frame, text="Не строить PDF", variable=var_pdf, value="none").pack(anchor=tk.W, pady=2)
        ttk.Label(frame, text="Упрощение графа вызовов (рекомендуется для обзора):", font=("", 9)).pack(anchor=tk.W, pady=(12, 4))
        var_exclude_std = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Исключить вызовы std::, boost::, Qt:: (стандартные/внешние библиотеки)",
            variable=var_exclude_std,
        ).pack(anchor=tk.W, pady=2)
        var_hide_utility = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Скрыть часто вызываемые функции (логгеры, утилиты) — по порогу входящих вызовов",
            variable=var_hide_utility,
        ).pack(anchor=tk.W, pady=2)
        util_frame = ttk.Frame(frame)
        util_frame.pack(anchor=tk.W, pady=2)
        ttk.Label(util_frame, text="Порог (скрыть функции с входящих вызовов больше чем):").pack(side=tk.LEFT, padx=(0, 5))
        var_util_threshold = tk.IntVar(value=30)
        spin = tk.Spinbox(util_frame, from_=5, to=200, width=5, textvariable=var_util_threshold)
        spin.pack(side=tk.LEFT)
        spin.delete(0, tk.END)
        spin.insert(0, "30")

        def _get_threshold():
            try:
                return max(0, int(var_util_threshold.get()))
            except (ValueError, tk.TclError):
                return 30

        def on_ok():
            pdf_choice = var_pdf.get()
            result_holder.append({
                "save_full_gv": var_save_gv.get(),
                "render_full_pdf": pdf_choice == "full",
                "build_calls_pdf": pdf_choice == "calls",
                "exclude_std_lib": var_exclude_std.get(),
                "hide_utility_threshold": _get_threshold() if var_hide_utility.get() else 0,
            })
            event.set()
            dlg.destroy()

        def on_cancel():
            result_holder.append({
                "save_full_gv": True,
                "render_full_pdf": False,
                "build_calls_pdf": True,
                "exclude_std_lib": False,
                "hide_utility_threshold": 0,
            })
            event.set()
            dlg.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена (по умолчанию: только .gv и graph_calls)", command=on_cancel).pack(side=tk.LEFT, padx=5)

    def _run_build(self):
        project_path = self.project_var.get().strip()
        if not project_path:
            messagebox.showwarning("Предупреждение", "Укажите каталог с исходниками C++.")
            return
        if not os.path.isdir(project_path):
            messagebox.showerror("Ошибка", "Каталог не найден: {}".format(project_path))
            return

        out_dir = self.output_var.get().strip()
        if out_dir and not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Ошибка", "Не удалось создать каталог вывода: {}".format(e))
                return

        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.stop_event = threading.Event()
        self.stop_event.clear()

        def ask_callback(num_nodes, num_edges, out_dir):
            """Вызывается из потока построения при большом графе; блокируется до выбора пользователя."""
            result_holder = []
            ev = threading.Event()

            def show():
                self._show_graph_choice_dialog(num_nodes, num_edges, out_dir, result_holder, ev)
            self.after(0, show)
            ev.wait()
            return result_holder[0] if result_holder else None

        def _get_util_threshold():
            try:
                return max(0, int(self.filter_util_threshold_var.get()))
            except (ValueError, tk.TclError):
                return 30

        def work():
            try:
                cfg = self.config_manager.load_config() if self.config_manager else None
                import graph_runner
                success, msg = graph_runner.run_graph_pipeline(
                    project_path=project_path,
                    output_dir=out_dir if out_dir else None,
                    progress_callback=self._log_safe,
                    stop_event=self.stop_event,
                    config=cfg,
                    ask_before_full_graph=ask_callback,
                    filter_std_lib=self.filter_std_var.get(),
                    filter_utility_threshold=_get_util_threshold() if self.filter_util_var.get() else 0,
                    use_regex_nodes=self.use_regex_var.get(),
                )
                self.after(0, lambda: self._on_done(success, msg))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda: self._on_done(False, str(e)))

        self.worker_thread = threading.Thread(target=work, daemon=True)
        self.worker_thread.start()

    def _stop_build(self):
        if self.stop_event:
            self.stop_event.set()
        self._log("Остановка по запросу пользователя...")

    def _on_done(self, success, message):
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.worker_thread = None
        if success:
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка построения графа", message)
