import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

from gui_config import ConfigManager
from main import run_redundancy


class RedundancyWindow(tk.Toplevel):
    """Окно проверки на избыточность (inotify + SQLite)."""

    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent)
        self.title("Проверка на избыточность")
        self.geometry("700x500")

        self.config_manager = config_manager
        self.stop_event = None
        self.worker_thread = None

        self._create_widgets()
        self._load_defaults()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Путь к проекту
        project_frame = ttk.LabelFrame(main_frame, text="Путь к проекту", padding=5)
        project_frame.pack(fill=tk.X, expand=False, pady=5)
        proj_row = ttk.Frame(project_frame)
        proj_row.pack(fill=tk.X, padx=5, pady=2)
        self.project_var = tk.StringVar()
        ttk.Entry(proj_row, textvariable=self.project_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(proj_row, text="Обзор…", command=self._browse_project).pack(side=tk.RIGHT, padx=5)

        # Путь к БД
        db_frame = ttk.LabelFrame(main_frame, text="Путь к базе SQLite", padding=5)
        db_frame.pack(fill=tk.X, expand=False, pady=5)
        db_row = ttk.Frame(db_frame)
        db_row.pack(fill=tk.X, padx=5, pady=2)
        self.db_path_var = tk.StringVar()
        ttk.Entry(db_row, textvariable=self.db_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(db_row, text="Обзор…", command=self._browse_db).pack(side=tk.RIGHT, padx=5)

        # Кнопки управления
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, expand=False, pady=10)

        self.start_button = ttk.Button(
            buttons_frame,
            text="1. Запустить проверку",
            command=self.start_redundancy,
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.finish_button = ttk.Button(
            buttons_frame,
            text="2. Сборка завершена",
            command=self.finish_build,
            state=tk.DISABLED,
        )
        self.finish_button.pack(side=tk.LEFT, padx=5)

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Журнал", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')

    def _browse_project(self):
        path = filedialog.askdirectory(title="Путь к проекту")
        if path:
            self.project_var.set(path)

    def _browse_db(self):
        path = filedialog.askopenfilename(
            title="Путь к базе SQLite",
            filetypes=[("База SQLite", "*.db"), ("Все файлы", "*")]
        )
        if path:
            self.db_path_var.set(path)

    def _load_defaults(self):
        """Подтянуть значения по умолчанию из LOG_PATH.txt."""
        try:
            cfg = self.config_manager.load_config()
        except Exception:
            cfg = {}

        project_path = cfg.get('PATH_FILE', '')
        self.project_var.set(project_path)

        if project_path:
            default_db = os.path.join(project_path, '4ndv_python.db')
        else:
            default_db = os.path.join(os.getcwd(), '4ndv_python.db')
        self.db_path_var.set(default_db)

    def log(self, message: str):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start_redundancy(self):
        project_dir = self.project_var.get().strip()
        db_path = self.db_path_var.get().strip()

        if not project_dir:
            messagebox.showwarning("Предупреждение", "Укажите путь к проекту.")
            return

        if not os.path.isdir(project_dir):
            messagebox.showerror("Ошибка", "Каталог проекта не найден:\n{}".format(project_dir))
            return

        if not db_path:
            db_path = os.path.join(project_dir, '4ndv_python.db')
            self.db_path_var.set(db_path)

        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Предупреждение", "Проверка уже запущена.")
            return

        self.stop_event = threading.Event()

        def progress_cb(msg):
            # вызывать в GUI-потоке
            self.after(0, lambda m=msg: self.log(m))

        def worker():
            try:
                run_redundancy(project_dir, db_path, stop_event=self.stop_event, progress_callback=progress_cb)
                self.after(0, lambda: messagebox.showinfo(
                    "Готово",
                    "Проверка на избыточность завершена.\nРезультат в:\n{}".format(db_path),
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Ошибка",
                    "Ошибка при проверке на избыточность:\n{}".format(e),
                ))
            finally:
                self.after(0, self._on_worker_finished)

        self.log("Запуск проверки на избыточность...")
        self.start_button.config(state=tk.DISABLED)
        self.finish_button.config(state=tk.NORMAL)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def finish_build(self):
        """Пользователь сообщает, что сборка завершена – даём сигнал остановить inotify."""
        if not self.stop_event:
            return
        self.log("Сигнал завершения сборки отправлен. Завершаем наблюдение...")
        self.stop_event.set()

    def _on_worker_finished(self):
        self.start_button.config(state=tk.NORMAL)
        self.finish_button.config(state=tk.DISABLED)

