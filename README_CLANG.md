# Интеграция clang / clang-tidy с анализатором C++ кода

Этот файл описывает, как подключить **clang / clang-tidy** к нашему анализатору, чтобы получать
реальные диагностические сообщения уровня компилятора (unused function/variable, unreachable code и т.д.).

**Единое руководство по установке и зависимостям (для новичков):** см. **SETUP_GUIDE.md** — там по шагам описаны установка LLVM 16 и привязок, настройка CLANG_LIB, LOG_PATH.txt и устранение типичных ошибок.

## 1. Что нужно установить на Astra Linux

На машине, где собирается и анализируется проект C++ (обе части СПО):

```bash
sudo apt-get update
sudo apt-get install clang clang-tidy clang-tools

clang --version
clang-tidy --version
```

Должны успешно отработать без ошибок.

---

## 2. Включаем экспорт `compile_commands.json` в CMake-проектах

Для каждого CMake-проекта, который мы анализируем (например, `Skif_Service_Cert-1522` и `Skif_Gui_Cert-8615`):

1. В корневом `CMakeLists.txt` добавить строку:

   ```cmake
   set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
   ```

   Либо при конфигурации проекта добавить флаг:

   ```bash
   cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B build -S .
   ```

2. После конфигурации/сборки в каталоге сборки должен появиться файл:

   ```bash
   build/compile_commands.json
   ```

   Это JSON с полным списком команд компиляции для всех файлов проекта; clang-tidy использует его,
   чтобы знать флаги, include-пути и т.д.

---

## 3. Настройка `LOG_PATH.txt` для clang-анализа

В файле `LOG_PATH.txt` анализатора (лежит рядом с `cpp-analyzer` или в корне проекта `С++`) нужно добавить ключ:

```text
COMPILE_COMMANDS=/полный/путь/к/build/compile_commands.json
```

Примеры:

```text
COMPILE_COMMANDS=/home/user/projects/Skif_Service_Cert-1522/build/compile_commands.json
```

Дополнительные ключи в `LOG_PATH.txt` для clang:

| Ключ | Описание |
|------|----------|
| `CLANG_TIDY_CHECKS=check1,check2,...` | Дополнительные проверки clang-tidy (добавляются к базовому набору). См. раздел «Рекомендуемые проверки для РД НДВ» ниже. |
| `CLANG_FILES_FROM=compile_commands` | Список файлов из compile_commands.json (по умолчанию). |
| `CLANG_FILES_FROM=ccc_file_list` | Список файлов из БД. |
| `CLANG_DEBUG=1` | Вывод stdout/stderr clang-tidy для первых двух файлов. |
| `CLANG_LIB=/путь/к/libclang.so.1` | Путь к библиотеке libclang (если установлен LLVM из apt.llvm.org, см. ниже). |

Базовый набор проверок уже включает: unused-function, unused-variable, DeadStores, UnreachableCode, CallAndMessage (возможный null при вызове).

### Несовместимость версий libclang (AST, граф вызовов)

Если при запуске «Диагностика Clang» или построении графа вызовов появляется ошибка вида  
`undefined symbol: clang_CXXMethod_isDeleted` или «python bindings are compatible with your libclang.so version»:

- На системе стоит **LLVM 6** (Astra), а пакет **libclang** с pip собран под более новую версию; в PyPI **нет** libclang 6.x (минимальная — 9.0.1).

**Вариант А — системные привязки под LLVM 6 (если есть в репозитории):**

```bash
apt-cache search python3 clang
# Если есть python3-clang-6 или python3-clang — установить и убрать pip-пакет:
sudo apt install python3-clang-6   # или как покажет search
pip3 uninstall libclang
```

**Вариант Б — установить новый LLVM из репозитория apt.llvm.org:**

```bash
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 14
pip3 install 'libclang==14.0.6'
```

В **LOG_PATH.txt** добавить строку:

```text
CLANG_LIB=/usr/lib/llvm-14/lib/libclang.so.1
```

(Путь может отличаться; проверьте: `ls /usr/lib/llvm-14/lib/libclang*`.)

### Рекомендуемые дополнительные проверки для РД НДВ (уровни контроля 2–4)

Подходят для контроля «потенциально опасных конструкций» и полноты/надёжности кода. Указывать в поле «Доп. проверки clang-tidy» или в `CLANG_TIDY_CHECKS` через запятую. Состав проверок зависит от версии clang-tidy (Astra: LLVM 6); при отсутствии проверки clang-tidy выдаст предупреждение — её можно убрать из списка.

**Потенциально опасные функции и API (уровень 2, синтаксический контроль):**

- `clang-analyzer-security.insecureAPI.strcpy` — использование strcpy (переполнение буфера)
- `clang-analyzer-security.insecureAPI.strcmp` — небезопасное сравнение строк
- `clang-analyzer-security.insecureAPI.gets` — использование gets
- `clang-analyzer-security.insecureAPI.mkstemp` — создание временных файлов без ограничений

**Типичные ошибки и неопределённое поведение (bugprone):**

- `bugprone-use-after-move` — использование объекта после std::move
- `bugprone-suspicious-memset-usage` — подозрительное использование memset (например, sizeof(указатель))
- `bugprone-copy-constructor-init` — ошибки в списке инициализации копирующего конструктора
- `bugprone-assert-side-effect` — побочные эффекты в assert

**CERT (надёжность и безопасность):**

- `cert-err34-c` — проверка возвращаемого значения (игнорирование кодов ошибок)
- `cert-msc50-cpp` — неиспользование std::rand для критичного к криптографии кода (при необходимости)

**C++ Core Guidelines (опасные приведения и границы):**

- `cppcoreguidelines-pro-bounds-pointer-arithmetic` — арифметика указателей (риск выхода за границы)
- `cppcoreguidelines-pro-type-const-cast` — использование const_cast
- `cppcoreguidelines-pro-type-cstyle-cast` — C-стиль приведения типов

**Избыточность и неиспользуемый код (соответствие уровням контроля):**

- `misc-unused-parameters` — неиспользуемые параметры функций (или `readability-misc-unused-parameters` в новых версиях)

**Пример строки для поля «Доп. проверки clang-tidy» (минимум под Astra/LLVM 6):**

```text
bugprone-use-after-move,bugprone-suspicious-memset-usage,bugprone-copy-constructor-init,cert-err34-c,cppcoreguidelines-pro-bounds-pointer-arithmetic,cppcoreguidelines-pro-type-const-cast,misc-unused-parameters
```

Если в системе установлена более новая версия clang-tidy, можно добавить, например: `clang-analyzer-security.insecureAPI.strcpy`, `clang-analyzer-security.insecureAPI.gets`.

**Важно:** сейчас анализатор использует **один** путь `COMPILE_COMMANDS` за запуск.  
Если у вас два проекта (service и gui), можно:

- либо иметь два разных `LOG_PATH.txt` и переключать их перед запуском анализатора;
- либо вручную менять строку `COMPILE_COMMANDS=...` перед анализом конкретной части.

---

## 4. Методы анализа: `CLANG`, `CLANG_AST`, `CLANG_AST_NO_SENS`

В `LOG_PATH.txt` метод анализа задаётся ключом:

```text
SEARH_METH=...
```

**Метод CLANG** (при заданном `COMPILE_COMMANDS`):

- Выполняет сценарий на базе Clang AST **без сенсоров**: find_files, findConnectionBetweenFilesCpp, findCppClass, clang_ast_runner, NEW_3_F_Line_Seg, NEW_4_Variabels_C, usingVariables, затем clang_runner (диагностика clang-tidy), createReport.
- Если `COMPILE_COMMANDS` не задан — только find_files и clang_runner (диагностика), без отчёта по функциям/переменным.

**Метод CLANG_AST_NO_SENS**:

- То же, что CLANG при заданном COMPILE_COMMANDS, но **без** clang_runner (без диагностики в таблицу `clang_diagnostics`): сразу отчёт после связей и переменных.

**Метод CLANG_AST**:

- Полный сценарий с Clang AST **и сенсорами**: те же этапы, что CLANG_AST_NO_SENS, плюс NEW_5_JSensor_NEW_Variant, create_sensoragramma_table, real_sensor_analyzer, затем createReport.

Ранее метод CLANG был «только find_files + clang_runner»; теперь при наличии COMPILE_COMMANDS в него встроен сценарий из CLANG_AST (без сенсоров) и формирование отчёта.

---

## 5. Что пишет `clang_runner.py` в БД

Создаётся (если ещё нет) таблица:

```sql
CREATE TABLE IF NOT EXISTS clang_diagnostics (
    id SERIAL PRIMARY KEY,
    file_path TEXT,
    line INT,
    column INT,
    severity TEXT,
    check_name TEXT,
    message TEXT
);
```

На каждый диагностический вывод clang/clang-tidy (строки вида
`file:line:col: warning: ... [check-name]`) добавляется запись:

- `file_path` — полный путь к файлу;
- `line` / `column` — номер строки и столбца;
- `severity` — `warning`, `error`, `note`;
- `check_name` — имя проверки (например, `clang-diagnostic-unused-function`, `clang-diagnostic-unused-variable`, `clang-analyzer-deadcode.UnreachableCode`);
- `message` — текст сообщения без служебной части.

При `DROP_TBL=1` в `LOG_PATH.txt` таблица `clang_diagnostics` очищается перед новым запуском анализа.

---

## 6. Как вызывается `clang_runner.py`

При `SEARH_METH=CLANG` и заданном `COMPILE_COMMANDS` в `_Starter.py` выполняется полный сценарий (find_files, связи, классы, clang_ast_runner, сегменты, переменные, usingVariables, затем `clang_runner`, createReport). Если `COMPILE_COMMANDS` не задан — только find_files и `clang_runner`. При `SEARH_METH=CLANG_AST` и `CLANG_AST_NO_SENS` скрипт `clang_runner` не вызывается (диагностика не пишется в `clang_diagnostics`), кроме метода CLANG.

---

## 7. Где смотреть результаты диагностики (в т.ч. доп. проверок)

В `gui_results.py` добавлена новая вкладка (в окне “Просмотр результатов”):

- **“Clang (диагностика)”** — выводит содержимое `clang_diagnostics` в виде таблицы:
  - Файл,
  - Строка,
  - Столбец,
  - Серьёзность,
  - Проверка (check_name),
  - Сообщение.

Итого:

Все проверки (и доп. из CLANG_TIDY_CHECKS) пишутся в одну таблицу; имя проверки — в колонке «Проверка» (check_name). На вкладке есть фильтр по имени проверки и кнопка «Обновить» (перезапрос из БД после завершения анализа). По умолчанию в отчёте и на вкладке **не показываются** записи с `severity = 'note'` и сообщения «file not found» — поэтому число записей в GUI может быть меньше, чем в БД (например, 32 вместо 100). Связей с таблицами файлов/функций нет; записи есть, если выполнялся clang_runner (CLANG или ALL с COMPILE_COMMANDS). Те же данные — в «Отчет» и при экспорте.

---

## 8. Типовой порядок действий для CLANG-анализа

1. Убедиться, что установлен clang/clang-tidy:

   ```bash
   clang --version
   clang-tidy --version
   ```

2. В проекте C++ (service / gui) включить `CMAKE_EXPORT_COMPILE_COMMANDS` и пересобрать:

   ```bash
   cd /home/user/projects/Skif_Service_Cert-1522
   cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B build -S .
   cmake --build build --config Release
   ```

3. В `LOG_PATH.txt` анализатора указать:

   ```text
   PATH_FILE=/home/user/projects/Skif_Service_Cert-1522/...
   COMPILE_COMMANDS=/home/user/projects/Skif_Service_Cert-1522/build/compile_commands.json
   SEARH_METH=CLANG
   ```

4. Запустить анализатор (GUI или CLI). В логах появятся:

   ```text
   file_search_Start
   file_search_End
   clang_analysis_Start
   ...
   clang_analysis_End
   ```

5. В GUI открыть «Результаты → Просмотр результатов» и вкладку «Диагностика кода», чтобы увидеть найденные clang‑проблемы.

---

## 9. Метод CLANG_AST: разбор функций и вызовов через AST Clang

Чтобы **повысить точность** анализа (определения функций и вызовы берутся из AST, а не из regex), используйте метод **CLANG_AST**.

### Что нужно

- Всё то же, что для метода CLANG: **compile_commands.json**, путь в `LOG_PATH.txt` (COMPILE_COMMANDS).
- Дополнительно: **Python-библиотека libclang** для разбора AST.

Установка libclang (Astra Linux / Debian):

- **При сборке exe/deb под Astra с LLVM 6:** версия Python-обёртки должна совпадать с системной libclang, иначе при запуске будет ошибка `undefined symbol: clang_CXXMethod_isDeleted`. Используйте старую обёртку:
  ```bash
  pip3 install libclang==9.0.1
  ```
  затем пересоберите пакет.

- При запуске из исходников (без exe/deb): `pip3 install libclang` или `libclang==9.0.1` под вашу версию LLVM.

**Для собранного exe/deb:** Python-модуль libclang включается в сборку. На машине пользователя должна быть установлена **системная** библиотека libclang.so (Astra: пакет `libclang-6.0-dev`, путь `/usr/lib/llvm-6.0/lib/`). Путь к .so подставляется автоматически; при необходимости задайте в `LOG_PATH.txt`: `CLANG_LIB=/usr/lib/llvm-6.0/lib/libclang.so.1`.

Если в системе установлен Clang из пакетов (например, `libclang-14-dev`), но библиотека в нестандартном месте, укажите путь в `LOG_PATH.txt`:

```text
CLANG_LIB=/usr/lib/llvm-14/lib/libclang.so
```

(подставьте свою версию LLVM и путь к `libclang.so`).

### Как запускать

1. В `LOG_PATH.txt` задайте:
   - `PATH_FILE=...` (корень дерева исходников);
   - `COMPILE_COMMANDS=.../build/compile_commands.json`;
   - `SEARH_METH=CLANG_AST` или `SEARH_METH=CLANG_AST_NO_SENS` (без сенсоров, сразу отчёт).
2. Запустите анализ (GUI или через `_Starter`).

Сценарий CLANG_AST:

- выполняет **find_files**, **findConnectionBetweenFilesCpp**, **findCppClass**;
- затем **clang_ast_runner** — заполняет `ccc_definition_function` и `ccc_use_function_list` из AST Clang (без findFunction/funcToNormal/findUseFunction);
- далее как при ALL: NEW_3_F_Line_Seg, NEW_4_Variabels_C, usingVariables, сенсоры, createReport.

**CLANG_AST_NO_SENS** — тот же сценарий, но без этапов сенсоров (JSensor, сенсограмма, sensor_analyzer); после usingVariables сразу createReport. Диагностика clang-tidy в таблицу не пишется.

**Продолжение с этапа (PIPELINE_FROM):** если анализ прервался или нужно перезапустить только часть пайплайна, в `LOG_PATH.txt` задайте:
```text
PIPELINE_FROM=clang_ast_classes
```
(или другой этап — список этапов **зависит от выбранного метода**: для CLANG_AST это find_files, clang_ast_connect, clang_ast_classes, …; для ALL при уровне 3 — find_files, clang_runner, findConnectionBetweenFilesCpp, …). Тогда выполняются только этот этап и все последующие. Пустое значение — запуск с начала. Работает для **всех** методов (CLANG, CLANG_AST, ALL, FF, и т.д.). В GUI: Настройки → «Продолжить с этапа»; список этапов подставляется по текущим уровню и методу.

**Пропуск этапов (PIPELINE_SKIP):** этапы, которые не нужно выполнять, перечислите через запятую:
```text
PIPELINE_SKIP=clang_runner,NEW_3_F_Line_Seg
```
Имена этапов те же, что в пайплайне выбранного метода. В GUI: Настройки → «Пропустить этапы (PIPELINE_SKIP)».

### Важно

- Пути к файлам в **compile_commands.json** должны совпадать с путями в **ccc_file_list** (те же, что собирает find_files). Обычно это так, если PATH_FILE указывает на корень проекта, а compile_commands — на тот же проект.
- Файлы, которые Clang не смог разобрать (ошибки компиляции, отсутствующие заголовки), не попадут в таблицы функций; отчёт будет только по успешно разобранным файлам.
- Переменные и «неиспользуемые переменные» по-прежнему считаются текущими Python-скриптами (NEW_4_Variabels_C, usingVariables); в будущем их тоже можно перевести на Clang AST.

### Таблицы «использований» (почему много строк)

- **ccc_use_variable_list** — по одной строке на **каждое вхождение** использования переменной в коде (одна и та же переменная на одной строке может встречаться несколько раз в AST, на одной строке кода может быть несколько переменных). Это не дубликаты, а учёт всех использований.
- **ccc_use_function_list** — по одной строке на каждое вхождение вызова; при неоднозначности перегрузки (несколько кандидатов по имени/числу аргументов) в список попадают **все кандидаты**, поэтому один вызов может дать несколько строк с разными `IDfunc`.

### Переменные: Clang и старые таблицы

- **ccc_definition_variable**, **ccc_use_variable_list**, **ccc_not_use_variable_ast** — заполняются **clang_ast_variables** (по AST Clang). Отчёт и вкладка «Неиспользуемые переменные» при наличии этих таблиц используют их.
- **ccc_variables_v** — заполняется старым скриптом **NEW_4_Variabels_C** (regex). Остаётся актуальной при каждом запуске; отчёт при наличии `ccc_definition_variable` предпочитает Clang-таблицы.

### Граф вызовов (GraphAnalyserC++)

При построении графа (окно «Построение графа» / `graph_runner`):

- При заданном **COMPILE_COMMANDS** узлы по умолчанию строятся по **Clang AST** (`find_nodes_clang_cpp`): дерево в том же формате, что и regex (Module.body — плоский список Import, Namespace, ClassDef, FunctionDef; у FunctionDef — body с Call). Учитываются только объявления из **текущего файла** (не из включённых заголовков).
- **Все файлы** из `cpp_files` попадают в граф: файлы из compile_commands разбираются Clang’ом, остальные (и при пустом AST) — regex (`find_nodes_cpp.parse_cpp_file`). Заголовки .h — по флагам .cpp из ccc_connect_list или из той же папки.
- **USE_CLANG_GRAPH=0** в LOG_PATH — принудительно только regex для графа.
- Если Clang недоступен, используется режим «из ccc_*» (при заполненных таблицах) или только regex.

### Скрипты, использующие Clang (краткий обзор)

| Скрипт | Назначение | Зависимости |
|--------|------------|-------------|
| **clang_runner.py** | Запуск clang-tidy, запись в `clang_diagnostics`. | COMPILE_COMMANDS, clang-tidy в PATH. Список файлов: compile_commands или ccc_file_list (CLANG_FILES_FROM). |
| **clang_ast_runner.py** | Заполнение `ccc_definition_function`, `ccc_use_function_list` по AST (libclang). | COMPILE_COMMANDS, libclang, ccc_file_list. Пути в JSON должны совпадать с путями в БД. |
| **clang_ast_variables.py** | Заполнение `ccc_definition_variable`, `ccc_use_variable_list`, представление `ccc_not_use_variable_ast`. | После find_files и clang_ast_runner, COMPILE_COMMANDS, libclang. |
| **find_nodes_clang_cpp.py** | Построение узлов графа (cpp_type_nodes, cpp_parent_child) по Clang AST в формате, совместимом с fill_graph/find_func_cpp. | COMPILE_COMMANDS для части файлов; для остальных и при пустом AST — regex. |

Общие точки отказа: несовпадение путей (LOG_PATH, compile_commands, БД), отсутствие libclang.so или несовместимая версия, файлы не из compile_commands (для них в графе и переменных используется regex/другой источник).

