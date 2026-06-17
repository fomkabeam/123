# Сборка .deb для Astra Linux 1.6 (без доступа к исходному коду)

После установки пакета в `/opt/cpp-analyzer/` попадают **только**:
- исполняемый файл `cpp-analyzer`;
- конфигурация `LOG_PATH.txt`.

Исходный код (.py) в пакет **не входит** и на машине пользователя не появляется.

## Требования для сборки

- Astra Linux 1.6 (или совместимая система с Debian/Ubuntu)
- Python 3, pip, пакеты: `python3-tk`, `python3-psycopg2`
- Для сборки: `debhelper`, `pyinstaller` (ставится через pip при сборке)
- Для методов CLANG_AST / CLANG_AST_NO_SENS: перед сборкой установить Python-обёртку libclang. На Astra с LLVM 6 — версия обёртки должна совпадать с системной libclang: `pip3 install libclang==9.0.1` (более новые версии несовместимы с libclang.so из LLVM 6).

## Сборка пакета

1. Установить зависимости для сборки:
   ```bash
   sudo apt-get install debhelper python3 python3-pip python3-tk python3-psycopg2
   pip3 install pyinstaller 'libclang==9.0.1'
   ```

2. В каталоге с проектом (где лежат `debian/`, `gui_main.py`, `cpp_analyzer.spec`):
   ```bash
   dpkg-buildpackage -us -uc -b
   ```

3. Готовый пакет будет в родительском каталоге: `../cpp-analyzer_1.0-1_amd64.deb`.

## Установка на целевую машину

Рекомендуется ставить через **apt**, чтобы подтянулись зависимости (Python, tk, psycopg2, clang-tidy, libclang для методов CLANG_AST):

```bash
sudo apt install ./cpp-analyzer_1.0-1_amd64.deb
```

Если ставите через `dpkg -i`, зависимости не установятся автоматически — их нужно доставить вручную. Список пакетов для чистой системы см. в **DEPENDENCIES.txt** (в корне проекта).

После установки:
- запуск из меню или из терминала: `cpp-analyzer`;
- конфигурация: `/opt/cpp-analyzer/LOG_PATH.txt` (можно редактировать);
- в `/opt/cpp-analyzer/` нет файлов .py — только бинарник и конфиг.

Для методов **CLANG_AST** и **CLANG_AST_NO_SENS** на машине пользователя должна быть установлена системная библиотека libclang: `sudo apt-get install libclang-14-1` (или libclang-11-1). Без неё эти методы выдадут сообщение с указанием установить пакет.

## Примечания

- Сборку нужно выполнять на Astra Linux 1.6 (или той же версии библиотек), чтобы бинарник корректно работал после установки.
- При необходимости замените в `debian/changelog` и `debian/control` данные maintainer и версию.
- Шаблон конфигурации в пакете берётся из `LOG_PATH.txt` в каталоге сборки; при необходимости подготовьте свой шаблон перед сборкой.
