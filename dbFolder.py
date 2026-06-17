# -*- coding: utf-8 -*-
import os
import sys


def Check_LOG_INFO():
    """Чтение LOG_PATH.txt рядом с исполняемым файлом (frozen) или модулем (dev)."""
    DB_INFO = {}
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'LOG_PATH.txt')

    file = open(config_path, 'r')
    record = 0
    str_record_DO = ''
    str_record_PO = ''
    for line in file:
        str_record_DO = ''
        str_record_PO = ''
        for Sim in line:
            if Sim == '=' and record == 0:
                record = 1
                continue
            if record == 0:
                str_record_DO += Sim
            if record == 1:
                str_record_PO += Sim
        DB = str_record_PO.rstrip("\n")
        DB = DB.rstrip("\r")
        # print("{}:{}".format(str_record_DO, DB))
        DB_INFO[str_record_DO] = DB
        record = 0
    return DB_INFO


folder = Check_LOG_INFO()
