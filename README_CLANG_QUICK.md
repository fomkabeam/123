# Что делать после сборки Skif_Service_Cert-1522 (когда уже есть compile_commands.json)

## 1. Где лежит compile_commands.json

После успешной сборки сервиса файл находится здесь:

```text
/home/user/projects/Skif_Service_Cert-1522/build/compile_commands.json
```

Убедись, что он есть: `ls -la /home/user/projects/Skif_Service_Cert-1522/build/compile_commands.json`

---

## 2. Настрой LOG_PATH.txt анализатора

Файл `LOG_PATH.txt` лежит рядом с запускаемым анализатором (в папке проекта С++ или рядом с exe).

Должны быть заданы (остальные ключи — как обычно: БД, путь к проекту и т.д.):

```text
PATH_FILE=/home/user/projects/Skif_Service_Cert-1522
COMPILE_COMMANDS=/home/user/projects/Skif_Service_Cert-1522/build/compile_commands.json
SEARH_METH=CLANG
```

- **PATH_FILE** — корень проекта, откуда `find_files.py` собирает список исходников в БД.
- **COMPILE_COMMANDS** — полный путь к `compile_commands.json` из сборки.
- **SEARH_METH=CLANG** — включить сценарий «только поиск файлов + clang-tidy», без полного анализа.

Пример полного фрагмента (подставь свои DB_* и пути):

```text
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=...
DB_USER=...
DB_PASS=...
PATH_FILE=/home/user/projects/Skif_Service_Cert-1522
COMPILE_COMMANDS=/home/user/projects/Skif_Service_Cert-1522/build/compile_commands.json
SEARH_METH=CLANG
```

Опционально: чтобы перед каждым запуском очищать таблицу диагностик, добавь `DROP_TBL=1`.

---

## 3. Запуск анализатора

Запусти анализатор как обычно (GUI или через `_Starter.py`). В логе должно быть что-то вроде:

```text
file_search_Start
file_search_End
clang_analysis_Start
...
clang_analysis_End
```

- Сначала заполняется `ccc_file_list` по `PATH_FILE`.
- Потом для каждого .c/.cc/.cpp из списка вызывается clang-tidy по `compile_commands.json`, результаты пишутся в таблицу `clang_diagnostics`.

---

## 4. Где смотреть результат

В GUI: **«Результаты» → «Просмотр результатов»** → вкладка **«Clang (диагностика)»**.

Там таблица из БД: файл, строка, столбец, серьёзность (warning/error/note), имя проверки, сообщение (unused function/variable, unreachable code и т.д.).

---

## 5. Если анализатор на Windows, а проект на Astra

Тогда либо:

- запускай анализатор на той же машине, где собран проект (Astra), с теми же путями в `LOG_PATH.txt`;  
или  
- копируй `compile_commands.json` и дерево исходников на Windows и в `LOG_PATH.txt` укажи соответствующие Windows-пути к `PATH_FILE` и `COMPILE_COMMANDS` (пути в `compile_commands.json` должны совпадать с реальным расположением файлов на той машине, где запускается анализатор).
