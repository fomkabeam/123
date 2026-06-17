# Сравнение граф-анализаторов: пайплайн на Clang (GraphAnalyserC++) и вариант на regex

## 1. Полная работа нашего граф-анализатора (текущий пайплайн)

1. **Сканирование файлов**  
   `find_files_cpp`: обход каталога проекта, запись путей в `cpp_files`. Прогресс каждые 500 файлов.

2. **Узлы (источник дерева)**  
   Таблицы `cpp_type_nodes` и `cpp_parent_child` заполняются в таком приоритете:
   - если в БД уже есть данные из анализа (таблица `ccc_definition_function`) → **fill_nodes_from_ccc** (узлы из ccc_* без повторного парсинга);
   - иначе → **fill_nodes_from_clang** (парсинг через libclang, запись в ccc_* и в cpp_type_nodes/cpp_parent_child);
   - при неудаче → снова fill_nodes_from_ccc;
   - если узлов всё ещё нет → **find_nodes_cpp.find_nodes** (заглушка: только пустой Module по каждому файлу).

   **Важно:** при работе через Clang/ccc в дерево попадает **полное AST Clang**: каждый узел (DeclRefExpr, CallExpr, body, name, func, arguments, индексы 0,1,2,…). В результате **очень много узлов на файл** (сотни–тысячи на большой файл).

3. **Граф в памяти**  
   `create_graph_cpp.fill_graph`: один большой запрос к `cpp_parent_child` + `cpp_type_nodes`, построение NetworkX MultiDiGraph. Узлы — объекты (file_id, node_id, name, block_id), рёбра — поля дерева (body, 0, 1, name, func, …).

4. **Области видимости**  
   `set_block_id_cpp`: создание таблиц блоков, обход графа (Module → body → …), присвоение block_id, вложенность блоков.

5. **Функции и вызовы**  
   `find_func_cpp`: поиск определений функций (FunctionDef) и вызовов (Call), связывание Call → FunctionDef, обновление графа/БД.

6. **Экспорт в .gv / PDF**  
   `create_graph_cpp.create_full_graph`:
   - **Полный граф и graph_calls** рисуются в **едином читаемом стиле**: rankdir LR, margin 0.02, белый фон, чёрный текст, красные рёбра (синие — Call→FunctionDef). Подписи узлов — через _node_display_label (для FunctionDef/Call — имя функции из AST, иначе тип узла). Полный граф сохраняется в `graph_full_original.gv` (и опционально в PDF).
   - **Граф вызовов (graph_calls):** только FunctionDef и Call; опции фильтрации (std::, boost::, Qt::; скрытие «служебных» по порогу); тот же стиль LR, белый фон, синие рёбра.

Итог: по умолчанию данные из **Clang** (точный анализ), а **выход** — единый читаемый вид (LR, margin 0.02, красные/синие рёбра). Опционально можно включить «Упрощённый анализ (regex)» — тогда узлы строятся по regex (меньше узлов, без Clang).

---

## 2. Вариант на regex (упрощённый анализ, без Clang)

1. **Файлы**  
   То же: `find_files_cpp`, таблица `cpp_files`.

2. **Узлы — только regex, без Clang**  
   **find_nodes_cpp** с функцией **parse_cpp_file**:
   - читает файл построчно;
   - убирает комментарии;
   - находит только: `#include` → Import (path, names), `namespace X {` → Namespace, `class/struct X` → ClassDef, функцию по regex (имя + аргументы) → FunctionDef (name, args, body), вызов по regex (слово + `(`) → Call (func), с исключением ключевых слов (if, for, return, …).

   В дерево попадают только **высокоуровневые узлы**: Module, body, индексы списков, Import, path, names, Namespace, ClassDef, FunctionDef, name, args, body, Call, func. **Нет** полного AST: нет каждого выражения, каждого дочернего узла компилятора. В результате **узлов на файл в разы меньше** (десятки–сотни, а не тысячи).

3. **Граф в памяти**  
   То же: `fill_graph` по `cpp_parent_child` и `cpp_type_nodes` → NetworkX. Структура та же, но узлов меньше.

4. **Области видимости**  
   `set_block_id_cpp`, `nesting_blocks` — та же идея (шаги 5, 6, 7).

5. **Функции и вызовы**  
   `find_func_cpp` — то же: поиск FunctionDef/Call, связи Call→FunctionDef.

6. **Экспорт в .gv / PDF**  
   **create_full_graph** (regex-вариант):
   - один Digraph, **все узлы** gr с `label=str(i.name)` (Module, body, main, fopen, …);
   - **все рёбра**: Call→FunctionDef синие, остальные красные;
   - атрибуты: `rankdir='LR'`, `margin='0.02'`, `bgcolor='white'`, общие nodeattrs/edgeattrs (чёрный текст, белая заливка, красные рёбра по умолчанию).

Итог: при regex-источнике граф строится из **упрощённого дерева** → мало узлов → полный граф остаётся читаемым даже на больших проектах.

---

## 3. Главное отличие

| Этап              | Regex-вариант              | Пайплайн на Clang (по умолчанию)      |
|-------------------|----------------------------|---------------------------------------|
| Источник узлов    | **Regex-парсер** (include, namespace, class, функция, вызов) | **Clang AST** (полное дерево разбора) или ccc_* |
| Размер дерева     | Десятки–сотни узлов на файл | Сотни–тысячи узлов на файл            |
| Стиль вывода     | LR, margin 0.02, red/blue  | Тот же: LR, margin 0.02, red/blue (единый стиль) |
| Точность анализа | Ниже (regex)               | Выше (Clang)                          |

Разница в **источнике данных** (regex vs Clang). Выход (PDF) теперь в **едином читаемом виде** для обоих вариантов; по умолчанию используется Clang для более точного анализа.

---

## 4. Единый стиль вывода и опция «Упрощённый анализ (regex)»

- **Полный граф и graph_calls** рисуются в **одном стиле**: LR, margin 0.02, белый фон, красные/синие рёбра, читаемые подписи (для FunctionDef/Call — имя из AST). Такой вид вывода используется всегда, независимо от источника узлов.
- **По умолчанию** узлы строятся из **Clang/ccc** (точный анализ); граф может быть большим, но оформление единое и читаемое.
- В GUI есть опция **«Упрощённый анализ (regex)»**: при включении узлы заполняются regex-парсером (`find_nodes_regex_cpp`), без Clang — меньше узлов на файл. Стиль PDF тот же (LR, margin 0.02, red/blue).

Файлы:
- `GraphAnalyserC++/create_graph_cpp.py` — один стиль для полного графа и graph_calls (LR, margin 0.02, _node_display_label для подписей).
- `GraphAnalyserC++/find_nodes_regex_cpp.py` — regex-парсер при включённом «Упрощённый анализ (regex)».
- `graph_runner.py` — параметр `use_regex_nodes`; при True вызывается `find_nodes_regex_cpp.find_nodes`.
- `gui_graph.py` — чекбокс «Упрощённый анализ (regex) — меньше узлов, без Clang (по умолчанию: Clang, точный анализ)».
