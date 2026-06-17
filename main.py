import subprocess
import sqlite3
import threading
import os


class DataBase:  # Работа с БД
    inotify_table = '''
    CREATE TABLE inotify_out (
        directory   TEXT,
        method      TEXT,
        file        TEXT);
    ''' #Таблица для вывода inotify
    project_files_table = '''
    CREATE TABLE files (
        path        TEXT,
        file        TEXT,
        description TEXT);
    ''' #Таблица всех файлов проекта
    not_use_files_view = '''
    CREATE VIEW not_use_files AS 
        SELECT * FROM files
        WHERE (file, path) NOT IN (
            SELECT DISTINCT file, directory FROM inotify_out);
    ''' #Представление неиспользуемых в компиляции файлов
    use_files_view = '''
    CREATE VIEW use_files AS 
        SELECT * FROM files
        WHERE (file, path) IN (
            SELECT DISTINCT file, directory FROM inotify_out);
    '''  # Представление используемых в компиляции файлов
    
    def __init__(self, db_path='4ndv_python.db', interactive=True, overwrite=False):
        """
        interactive=True  – старый режим с вопросом в консоли.
        interactive=False – режим для GUI, решение принимается по флагу overwrite.
        """
        if interactive:
            if os.path.isfile(db_path):
                cr = input('База данных существует, хотите её дополнить? Y/N\n')
                if cr == 'Y':
                    self.db_path = db_path
                    self.sqlite_connection = sqlite3.connect(db_path)
                    self.cursor = self.sqlite_connection.cursor()
                    print('База данных успешно подключена к SQLite')
                else:
                    os.remove(db_path)
                    self.createDB(db_path)
            else:
                self.createDB(db_path)
        else:
            if os.path.isfile(db_path):
                if overwrite:
                    os.remove(db_path)
                    self.createDB(db_path)
                else:
                    self.db_path = db_path
                    self.sqlite_connection = sqlite3.connect(db_path)
                    self.cursor = self.sqlite_connection.cursor()
                    print('База данных успешно подключена к SQLite')
            else:
                self.createDB(db_path)
        
    def __del__(self):
        self.commit()
        self.cursor.close()
        self.sqlite_connection.close()
        print('Соединение с SQLite закрыто')
        
    def createDB(self, db_path): #Создание структуры и БД
        self.db_path = db_path
        self.sqlite_connection = sqlite3.connect(db_path)
        self.cursor = self.sqlite_connection.cursor()
        self.cursor.execute(DataBase.inotify_table)
        self.cursor.execute(DataBase.project_files_table)
        self.cursor.execute(DataBase.not_use_files_view)
        self.cursor.execute(DataBase.use_files_view)
        self.commit()
        print('База данных создана и успешно подключена к SQLite')
        
    def getVersion(self): #Версия БД
        self.cursor.execute('select sqlite_version();')
        print('Версия базы данных SQLite: ', cursor.fetchall())
        
    def insertFiles(self, path, _file, description): #Внесение данных в таблицу files
        self.cursor.execute('''
            INSERT INTO files (path, file, description)
            VALUES ('{}', '{}', '{}');
        '''.format(path, _file, description))
        
    def insertInotifyOut(self, directory, method, _file): #Внесение данных в таблицу inotify_out
        self.cursor.execute('''
            INSERT INTO inotify_out (directory, method, file)
            VALUES ('{}', '{}', '{}');
        '''.format(directory, method, _file))
        
    def commit(self):
        self.sqlite_connection.commit()

def run_inotifywait(log_file, directory):  # Запуск inotify на определенную директорию
    subprocess.run(['inotifywait', '-rmco', log_file, directory], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def inotifyWatcher(directory, log_file='log_4ndv.cvs'):  # CLI-режим: запуск и остановка процесса
    print('Лог вывода команды inotify в файле {}'.format(log_file))
    thread = threading.Thread(target=run_inotifywait, args=(log_file, directory))
    thread.start()
    input('\n\tВыполните компиляцию, когда она завершится нажмите Enter\n\n')
    del thread
    return log_file


def run_inotify_for_build(directory, stop_event, log_file='log_4ndv.cvs'):
    """
    GUI-режим: запускает inotifywait и ждёт сигнала stop_event от окна,
    вместо input() в консоли.
    """
    print('Лог вывода команды inotify в файле {}'.format(log_file))
    thread = threading.Thread(target=run_inotifywait, args=(log_file, directory), daemon=True)
    thread.start()
    if stop_event is not None:
        stop_event.wait()
    return log_file


def insertInotify(db, log_file):  # Разбор лога inotify и запись его в БД
    with open(log_file, 'r') as f:
        log = f.read().split('\n')
    for i in log:
        db.insertInotifyOut(i[:i.find(',')], i[i.find(',') + 1:i.rfind(',')], i[i.rfind(',') + 1:])
    db.commit()

def findProjectFiles(db, directory, log_file='temp.txt'):  # Запись пути всех файлов проекта в БД
    print('Лог вывода команды find в файле {}'.format(log_file))
    with open(log_file, 'w') as f:
        fnd = subprocess.run(['find', directory, '-type', 'f', '-exec', 'file', '{}', ';'], stdout=f)
    with open(log_file, 'r') as f:
        files = f.read().split('\n')
    for i in files:
        try:
            if i.rfind('/') > i.find(':'): #Костыль для вывода типа ./checkbox-checked.png: PNG image data, 48 x 48, 8-bit/color RGBA, non-interlaced
                db.insertFiles(i[:i.rfind('/', 0, i.find(':')) + 1], i[i[:i.find(':')].rfind('/') + 1:i.find(':')], i[i.find(':') + 1:])
            else:
                db.insertFiles(i[:i.rfind('/') + 1], i[i.rfind('/') + 1:i.find(':')], i[i.find(':') + 1:])
        except Exception:
            print(i)
    db.commit()


def run_redundancy(project_directory, db_path='4ndv_python.db', stop_event=None, progress_callback=None):
    """
    Общая функция запуска проверки на избыточность.
    Используется из GUI (stop_event передаётся из окна) и может использоваться из других мест.
    """
    if progress_callback:
        progress_callback("Создание/подключение БД избыточности...")
    db = DataBase(db_path=db_path, interactive=False, overwrite=True)

    if progress_callback:
        progress_callback("Поиск файлов проекта...")
    findProjectFiles(db, project_directory)

    if progress_callback:
        progress_callback("Запуск наблюдения за сборкой (inotify)...")
        progress_callback("Выполните сборку проекта, затем вернитесь в окно и нажмите «Сборка завершена».")

    log_file = run_inotify_for_build(project_directory, stop_event)

    if progress_callback:
        progress_callback("Анализ лога inotify и запись в БД...")
    insertInotify(db, log_file)

    if progress_callback:
        progress_callback("Анализ завершён. Результат в {}".format(db.db_path))

    del db


def main():
    print('Перед работой убедитесь что команда \n\tinotifywait -rcmo 1.cvs /\nработает, '
          'иногда нужно увеличить число в файле /proc/sys/fs/inotify/max_user_watches')
    project_directory = input('Введите путь к проекту:\t')
    db = DataBase()
    
    findProjectFiles(db, project_directory)
    insertInotify(db, inotifyWatcher(project_directory))
    
    print('Анализ завершён результат в ', db.db_path)
    del db
    

if __name__ == '__main__':
    main()
    
