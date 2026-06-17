# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import threading
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

# ГОСТ Р 34.11-2012 (Streebog): используем системные утилиты Astra Linux
# Проверяем наличие gostsum или hashsum --gost-2012-256
_GOST_AVAILABLE = False
_GOST_CMD = None
_GOST_CMD_ARGS = []

def _check_gost_command():
    """Проверка доступности системной утилиты для ГОСТ."""
    global _GOST_AVAILABLE, _GOST_CMD, _GOST_CMD_ARGS

    # Самый простой и надёжный вариант для Astra: gostsum из /usr/bin
    if os.path.exists('/usr/bin/gostsum'):
        _GOST_CMD = 'gostsum'
        _GOST_CMD_ARGS = []  # по умолчанию считает ГОСТ Р 34.11-2012 (256 бит)
        _GOST_AVAILABLE = True
        return

    # Пробуем gost12sum (если вдруг есть)
    if os.path.exists('/usr/bin/gost12sum'):
        _GOST_CMD = 'gost12sum'
        _GOST_CMD_ARGS = []
        _GOST_AVAILABLE = True
        return

    # Пробуем hashsum с опцией --gost-2012-256
    try:
        test_file = '/dev/null' if os.path.exists('/dev/null') else os.devnull
        result = subprocess.run(['hashsum', '--gost-2012-256', test_file],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        if result.returncode == 0 and result.stdout:
            _GOST_CMD = 'hashsum'
            _GOST_CMD_ARGS = ['--gost-2012-256']
            _GOST_AVAILABLE = True
            return
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    # Пробуем openssl с GOST (если есть поддержка)
    try:
        test_file = '/dev/null' if os.path.exists('/dev/null') else os.devnull
        result = subprocess.run(['openssl', 'dgst', '-streebog256', test_file],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        if result.returncode == 0:
            _GOST_CMD = 'openssl'
            _GOST_CMD_ARGS = ['dgst', '-streebog256']
            _GOST_AVAILABLE = True
            return
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

# Проверяем при импорте модуля
_check_gost_command()


def md5_for_file(path, chunk_size=8192):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def gost256_for_file(path, chunk_size=8192):
    """Контрольная сумма по ГОСТ Р 34.11-2012 (Streebog, 256 бит) через системную утилиту."""
    if not _GOST_AVAILABLE:
        raise RuntimeError("Системная утилита для ГОСТ не найдена. Установите gostsum или hashsum.")
    
    try:
        # Вызываем системную команду
        cmd = [_GOST_CMD] + _GOST_CMD_ARGS + [path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        
        if result.returncode != 0:
            stderr_msg = result.stderr.decode('utf-8', errors='ignore')
            raise RuntimeError("Ошибка выполнения {}: {}".format(_GOST_CMD, stderr_msg))
        
        # Парсим вывод в зависимости от команды
        output = result.stdout.decode('utf-8', errors='ignore').strip()
        if not output:
            raise RuntimeError("Пустой вывод от {}".format(_GOST_CMD))
        
        hash_str = None
        
        # Формат openssl: "STREEBOG256(путь)=хеш" или "хеш путь"
        if _GOST_CMD == 'openssl':
            if '=' in output:
                # Формат "STREEBOG256(путь)=хеш"
                hash_str = output.split('=')[-1].strip()
            else:
                # Формат "хеш путь"
                parts = output.split()
                if parts:
                    hash_str = parts[0]
        else:
            # Формат gostsum/hashsum: "хеш  имя_файла" или "хеш *имя_файла" (binary mode)
            parts = output.split()
            if not parts:
                raise RuntimeError("Неверный формат вывода от {}".format(_GOST_CMD))
            
            # Хеш - первый элемент, может быть с '*' (binary mode)
            hash_str = parts[0]
            if hash_str.startswith('*'):
                hash_str = hash_str[1:]
        
        if not hash_str:
            raise RuntimeError("Не удалось извлечь хеш из вывода: {}".format(output))
        
        # Нормализуем: 256 бит = 64 hex символа
        hash_str = hash_str.lower().strip()
        if len(hash_str) > 64:
            # Берём первые 64 символа (если это 512-бит, обрезаем до 256)
            hash_str = hash_str[:64]
        elif len(hash_str) < 64:
            # Если меньше 64, возможно это неполный вывод или ошибка
            raise RuntimeError("Неверная длина хеша (ожидается 64 символа, получено {}): {}".format(len(hash_str), hash_str))
        
        return hash_str
    except subprocess.TimeoutExpired:
        raise RuntimeError("Таймаут при вычислении ГОСТ для файла {}".format(path))
    except Exception as e:
        raise RuntimeError("Ошибка при вычислении ГОСТ: {}".format(str(e)))


class DebChecksumWindow(tk.Toplevel):
    """Окно подсчёта КС для .deb пакетов (MD5 и/или ГОСТ Р 34.11-2012)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("КС Deb (MD5 / ГОСТ)")
        self.geometry("700x500")

        self.worker_thread = None

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Каталог с .deb
        deb_frame = ttk.LabelFrame(main_frame, text="Каталог с .deb пакетами", padding=5)
        deb_frame.pack(fill=tk.X, expand=False, pady=5)
        deb_row = ttk.Frame(deb_frame)
        deb_row.pack(fill=tk.X, padx=5, pady=2)
        self.deb_dir_var = tk.StringVar()
        ttk.Entry(deb_row, textvariable=self.deb_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(deb_row, text="Обзор…", command=lambda: self._browse_deb_dir()).pack(side=tk.RIGHT, padx=5)

        # Выбор алгоритмов: MD5 и/или ГОСТ
        algo_frame = ttk.LabelFrame(main_frame, text="Алгоритмы контрольной суммы", padding=5)
        algo_frame.pack(fill=tk.X, expand=False, pady=5)

        self.use_md5_var = tk.BooleanVar(value=True)
        self.use_gost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(algo_frame, text="MD5", variable=self.use_md5_var).pack(side=tk.LEFT, padx=10, pady=2)
        gost_cb = ttk.Checkbutton(algo_frame, text="ГОСТ Р 34.11-2012 (Streebog, 256 бит)", variable=self.use_gost_var)
        gost_cb.pack(side=tk.LEFT, padx=10, pady=2)
        if not _GOST_AVAILABLE:
            self.use_gost_var.set(False)
            gost_cb.config(state=tk.DISABLED)
            ttk.Label(algo_frame, text="(установите gostsum или hashsum)").pack(side=tk.LEFT, padx=5)

        # Файл вывода
        out_frame = ttk.LabelFrame(main_frame, text="Файл для сохранения контрольных сумм", padding=5)
        out_frame.pack(fill=tk.X, expand=False, pady=5)
        out_row = ttk.Frame(out_frame)
        out_row.pack(fill=tk.X, padx=5, pady=2)
        self.deb_out_var = tk.StringVar()
        ttk.Entry(out_row, textvariable=self.deb_out_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_row, text="Обзор…", command=lambda: self._browse_deb_out()).pack(side=tk.RIGHT, padx=5)

        # Кнопка
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, expand=False, pady=10)

        self.start_button = ttk.Button(btn_frame, text="Подсчитать КС для .deb", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Журнал", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')

    def _browse_deb_dir(self):
        path = filedialog.askdirectory(title="Каталог с .deb пакетами")
        if path:
            self.deb_dir_var.set(path)

    def _browse_deb_out(self):
        path = filedialog.asksaveasfilename(title="Файл для сохранения контрольных сумм", defaultextension=".txt")
        if path:
            self.deb_out_var.set(path)

    def log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start(self):
        deb_dir = self.deb_dir_var.get().strip()
        out_path = self.deb_out_var.get().strip()

        if not deb_dir or not os.path.isdir(deb_dir):
            messagebox.showerror("Ошибка", "Каталог с .deb пакетами не найден:\n{}".format(deb_dir or "<пусто>"))
            return
        if not out_path:
            messagebox.showerror("Ошибка", "Укажите файл для сохранения контрольных сумм.")
            return

        use_md5 = self.use_md5_var.get()
        use_gost = self.use_gost_var.get()
        if not use_md5 and not use_gost:
            messagebox.showerror("Ошибка", "Выберите хотя бы один алгоритм: MD5 или ГОСТ.")
            return

        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Предупреждение", "Подсчёт уже запущен.")
            return

        def worker():
            try:
                deb_files = [f for f in os.listdir(deb_dir) if f.endswith('.deb')]
                deb_files.sort()
                if not deb_files:
                    self.after(0, lambda: messagebox.showinfo("Информация", "В каталоге нет .deb файлов."))
                    return

                self.after(0, lambda: self.log("Найдено .deb файлов: {}".format(len(deb_files))))

                with open(out_path, 'w', encoding='utf-8') as out:
                    if use_md5:
                        out.write("# MD5\n")
                        for name in deb_files:
                            full = os.path.join(deb_dir, name)
                            try:
                                md5 = md5_for_file(full)
                                line = "{}  {}\n".format(md5, name)
                                out.write(line)
                                self.after(0, lambda m=("MD5 " + line.strip()): self.log(m))
                            except Exception as e:
                                err = "Ошибка для {}: {}".format(name, e)
                                out.write("# " + err + "\n")
                                self.after(0, lambda m=err: self.log(m))
                    if use_gost:
                        if use_md5:
                            out.write("\n")
                        out.write("# ГОСТ Р 34.11-2012 (Streebog, 256 бит)\n")
                        for name in deb_files:
                            full = os.path.join(deb_dir, name)
                            try:
                                gost = gost256_for_file(full)
                                line = "{}  {}\n".format(gost, name)
                                out.write(line)
                                self.after(0, lambda m=("ГОСТ " + line.strip()): self.log(m))
                            except Exception as e:
                                err = "Ошибка для {}: {}".format(name, e)
                                out.write("# " + err + "\n")
                                self.after(0, lambda m=err: self.log(m))

                algos = []
                if use_md5:
                    algos.append("MD5")
                if use_gost:
                    algos.append("ГОСТ Р 34.11-2012")
                self.after(0, lambda: messagebox.showinfo(
                    "Готово",
                    "Контрольные суммы ({}) для .deb сохранены в:\n{}".format(", ".join(algos), out_path),
                ))
            finally:
                self.after(0, lambda: self.start_button.config(state=tk.NORMAL))

        self.log("Запуск подсчёта КС для .deb...")
        self.start_button.config(state=tk.DISABLED)
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


class ArchiveChecksumWindow(tk.Toplevel):
    """Окно подсчёта КС для архивов с исходниками (MD5 и/или ГОСТ Р 34.11-2012)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("КС архивов (MD5 / ГОСТ)")
        self.geometry("700x550")

        self.archive_vars = []
        self.worker_thread = None

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Список архивов
        archives_frame = ttk.LabelFrame(main_frame, text="Архивы с исходным кодом", padding=5)
        archives_frame.pack(fill=tk.X, expand=False, pady=5)
        self.archives_frame = archives_frame

        add_btn = ttk.Button(archives_frame, text="Добавить архив", command=self.add_archive_entry)
        add_btn.pack(anchor=tk.W, padx=5, pady=2)

        # первая строка по умолчанию
        self.add_archive_entry()

        # Выбор алгоритмов: MD5 и/или ГОСТ
        algo_frame = ttk.LabelFrame(main_frame, text="Алгоритмы контрольной суммы", padding=5)
        algo_frame.pack(fill=tk.X, expand=False, pady=5)

        self.use_md5_var = tk.BooleanVar(value=True)
        self.use_gost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(algo_frame, text="MD5", variable=self.use_md5_var).pack(side=tk.LEFT, padx=10, pady=2)
        gost_cb = ttk.Checkbutton(algo_frame, text="ГОСТ Р 34.11-2012 (Streebog, 256 бит)", variable=self.use_gost_var)
        gost_cb.pack(side=tk.LEFT, padx=10, pady=2)
        if not _GOST_AVAILABLE:
            self.use_gost_var.set(False)
            gost_cb.config(state=tk.DISABLED)
            ttk.Label(algo_frame, text="(установите gostsum или hashsum)").pack(side=tk.LEFT, padx=5)

        # Файл вывода
        out_frame = ttk.LabelFrame(main_frame, text="Файл для сохранения контрольных сумм", padding=5)
        out_frame.pack(fill=tk.X, expand=False, pady=5)
        out_row = ttk.Frame(out_frame)
        out_row.pack(fill=tk.X, padx=5, pady=2)
        self.out_var = tk.StringVar()
        ttk.Entry(out_row, textvariable=self.out_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_row, text="Обзор…", command=lambda: self._browse_archive_out()).pack(side=tk.RIGHT, padx=5)

        # Кнопка
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, expand=False, pady=10)

        self.start_button = ttk.Button(btn_frame, text="Подсчитать КС архивов", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Журнал", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')

    def add_archive_entry(self):
        var = tk.StringVar()
        row = ttk.Frame(self.archives_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Обзор…", command=lambda v=var: self._browse_archive_file(v)).pack(side=tk.RIGHT, padx=5)
        self.archive_vars.append(var)

    def _browse_archive_file(self, var):
        path = filedialog.askopenfilename(
            title="Выберите архив",
            filetypes=[("Архивы", "*.tar.gz *.tar.bz2 *.zip *.tar"), ("Все файлы", "*")]
        )
        if path:
            var.set(path)

    def _browse_archive_out(self):
        path = filedialog.asksaveasfilename(title="Файл для сохранения контрольных сумм", defaultextension=".txt")
        if path:
            self.out_var.set(path)

    def log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start(self):
        archives = [v.get().strip() for v in self.archive_vars if v.get().strip()]
        out_path = self.out_var.get().strip()
        use_md5 = self.use_md5_var.get()
        use_gost = self.use_gost_var.get()

        if not archives:
            messagebox.showerror("Ошибка", "Укажите хотя бы один архив.")
            return
        if not out_path:
            messagebox.showerror("Ошибка", "Укажите файл для сохранения контрольных сумм.")
            return
        if not use_md5 and not use_gost:
            messagebox.showerror("Ошибка", "Выберите хотя бы один алгоритм: MD5 или ГОСТ.")
            return

        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Предупреждение", "Подсчёт уже запущен.")
            return

        def worker():
            try:
                self.after(0, lambda: self.log("Всего архивов: {}".format(len(archives))))
                with open(out_path, 'w', encoding='utf-8') as out:
                    if use_md5:
                        out.write("# MD5\n")
                        for path in archives:
                            name = os.path.basename(path)
                            if not os.path.isfile(path):
                                err = "Файл не найден: {}".format(path)
                                out.write("# " + err + "\n")
                                self.after(0, lambda m=err: self.log(m))
                                continue
                            try:
                                md5 = md5_for_file(path)
                                line = "{}  {}\n".format(md5, name)
                                out.write(line)
                                self.after(0, lambda m=("MD5 " + line.strip()): self.log(m))
                            except Exception as e:
                                err = "Ошибка для {}: {}".format(path, e)
                                out.write("# " + err + "\n")
                                self.after(0, lambda m=err: self.log(m))
                    if use_gost:
                        if use_md5:
                            out.write("\n")
                        out.write("# ГОСТ Р 34.11-2012 (Streebog, 256 бит)\n")
                        for path in archives:
                            name = os.path.basename(path)
                            if not os.path.isfile(path):
                                err = "Файл не найден: {}".format(path)
                                out.write("# " + err + "\n")
                                self.after(0, lambda m=err: self.log(m))
                                continue
                            try:
                                gost = gost256_for_file(path)
                                line = "{}  {}\n".format(gost, name)
                                out.write(line)
                                self.after(0, lambda m=("ГОСТ " + line.strip()): self.log(m))
                            except Exception as e:
                                err = "Ошибка для {}: {}".format(path, e)
                                out.write("# " + err + "\n")
                                self.after(0, lambda m=err: self.log(m))

                algos = []
                if use_md5:
                    algos.append("MD5")
                if use_gost:
                    algos.append("ГОСТ Р 34.11-2012")
                self.after(0, lambda: messagebox.showinfo(
                    "Готово",
                    "Контрольные суммы ({}) для архивов сохранены в:\n{}".format(", ".join(algos), out_path),
                ))
            finally:
                self.after(0, lambda: self.start_button.config(state=tk.NORMAL))

        self.log("Запуск подсчёта КС для архивов...")
        self.start_button.config(state=tk.DISABLED)
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

