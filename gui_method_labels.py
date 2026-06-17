# -*- coding: utf-8 -*-
"""
Человекочитаемые подписи методов анализа в комбобоксах GUI.
В конфиге и пайплайне по-прежнему используются короткие коды (SEARH_METH=F и т.д.).
"""

# Методы на regex/эвристиках (fallback) — помечаем в интерфейсе.
LEGACY_METHOD_CODES = frozenset({"ND", "C", "F", "V", "CPI", "ChI", "ADD_JSens"})

_SUFFIX = " — эвристика"

# Отдельные подписи без суффикса «эвристика» (у LS при наличии CC контур может быть AST).
_METHOD_LABELS = {
    "LS": "LS — сегменты строк",
    "CLANG": "CLANG — диагностика (clang-tidy)",
    "CLANG_AST": "CLANG_AST — полный анализ (AST)",
    "CLANG_AST_NO_SENS": "CLANG_AST_NO_SENS — AST без сенсоров",
}


def method_display(code):
    """Код из LOG_PATH.txt → строка для отображения в Combobox."""
    code = (code or "").strip()
    if not code:
        return code
    if code in _METHOD_LABELS:
        return _METHOD_LABELS[code]
    if code in LEGACY_METHOD_CODES:
        return code + _SUFFIX
    return code


def method_from_display(display):
    """Строка из Combobox → код для SEARH_METH и _Starter."""
    display = (display or "").strip()
    if not display:
        return display
    for cod, lab in _METHOD_LABELS.items():
        if display == lab:
            return cod
    if display.endswith(_SUFFIX):
        return display[: -len(_SUFFIX)].strip()
    return display
