# -*- coding: utf-8 -*-
import os
import sys
import psycopg2


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
        print("{}:{}".format(str_record_DO, DB))
        DB_INFO[str_record_DO] = DB
        record = 0
    return DB_INFO


folder = Check_LOG_INFO()

def get_file_path():
    KOR = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    CUR=KOR.cursor()
    CUR.execute("select path from ccc_file_list where sourse_or_lib = 'sourse'")
    buff=CUR.fetchall()
    list=[]
    for i in buff:
        list.append(i[0])
    KOR.commit()
    KOR.close()
    return list
def len_files_for_type(typ = 'sourse'):
    KOR = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    CUR=KOR.cursor()
    CUR.execute("select count(*) from ccc_var_use")
    l = CUR.fetchone()
    KOR.commit()
    KOR.close()
    return l[0]
if __name__=='__main__':
    python_path=folder['PATH_PYTHON']
    DEPTH=int(folder['CHECK_DEPTH'])
    if DEPTH==4:
        if folder['SEARH_METH']=='ALL':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Create_report_Start")
            os.system(""+python_path+"Create_Otchet.pyc")
            print("Create_report__End")
        elif folder['SEARH_METH']=='FF_PFS':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Find")
        elif folder['SEARH_METH']=='FF':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("Find")
        elif folder['SEARH_METH']=='PFS':
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Find")
        elif folder['SEARH_METH']=='CO':
            print("Create_report_Start")
            os.system(""+python_path+"Create_Otchet.pyc")
            print("Create_report__End")
            print("Find")
    if DEPTH==2:
        if folder['SEARH_METH']=='CO':
            print("Create_report_Start")
            os.system(""+python_path+"Create_Otchet.pyc")
            print("Create_report__End")
        if folder['SEARH_METH']=='ND':
            print("chek_ND_F_Start")
            os.system(""+python_path+"NEW_Not_Detected_Func.pyc")
            print("chek_ND_F_End")
        if folder['SEARH_METH']=='ALL':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("class_search_Start")
            os.system(""+python_path+"NEW_2_Class.pyc")
            print("class_search_End")
            print("func_search_Start")
            os.system(""+python_path+"NEW_3_Func.pyc")
            print("func_search_End")
            print("Variables_search_Start")
            os.system(""+python_path+"NEW_4_Variables.pyc")
            print("Variables_search_End")
            print("Package_and_Import_search_Start")
            os.system(""+python_path+"NEW_5_Chek_Package_Import.pyc")
            print("Package_and_Import_search_End")
            print("CommunicationFO_and_CommunicationIO_search_Start")
            os.system(""+python_path+"NEW_7_Func_for_Func.pyc")
            print("CommunicationFO_and_CommunicationIO_search_End")
            print("JSensor_ADD_Start")
            os.system(""+python_path+"NEW_6_File_NEW_JSensor.pyc")
            print("JSensor_ADD_End")
            print("Find")
        elif folder['SEARH_METH']=='FF_PFS':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Find")
        elif folder['SEARH_METH']=='FF':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("Find")
        elif folder['SEARH_METH']=='PFS':
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Find")
        elif folder['SEARH_METH']=='C':
            print("class_search_Start")
            os.system(""+python_path+"NEW_2_Class.pyc")
            print("class_search_End")
            print("Find")
        elif folder['SEARH_METH']=='F':
            print("func_search_Start")
            os.system(""+python_path+"NEW_3_Func.pyc")
            print("func_search_End")
            print("Find")
        elif folder['SEARH_METH']=='V':
            print("Variables_search_Start")
            os.system(""+python_path+"NEW_4_Variables.pyc")
            print("Variables_search_End")
            print("Find")
        elif folder['SEARH_METH']=='CPI':
            print("Package_and_Import_search_Start")
            os.system(""+python_path+"NEW_5_Chek_Package_Import.pyc")
            print("Package_and_Import_search_End")
            print("Find")
        elif folder['SEARH_METH']=='ChI':
            print("CommunicationFO_and_CommunicationIO_search_Start")
            os.system(""+python_path+"NEW_7_Func_for_Func.py")
            print("CommunicationFO_and_CommunicationIO_search_End")
            print("Find")
        elif folder['SEARH_METH']=='ADD_JSens':
            print("JSensor_ADD_Start")
            os.system(""+python_path+"NEW_6_File_NEW_JSensor.pyc")
            print("JSensor_ADD_End")
            print("Find")
    if DEPTH==3:
        if folder['SEARH_METH']=='CO':
            print("Create_report_Start")
            os.system(""+python_path+"Create_Otchet.pyc")
            print("Create_report__End")
        if folder['SEARH_METH']=='ND':
            print("chek_ND_F_Start")
            os.system(""+python_path+"NEW_Not_Detected_Func.pyc")
            print("chek_ND_F_End")
        if folder['SEARH_METH']=='ALL':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("class_search_Start")
            os.system(""+python_path+"NEW_2_Class.pyc")
            print("class_search_End")
            print("func_search_Start")
            os.system(""+python_path+"NEW_3_Func.pyc")
            print("func_search_End")
            print("Variables_search_Start")
            os.system(""+python_path+"NEW_4_Variables.pyc")
            print("Variables_search_End")
            print("Package_and_Import_search_Start")
            os.system(""+python_path+"NEW_5_Chek_Package_Import.pyc")
            print("Package_and_Import_search_End")
            print("CommunicationFO_and_CommunicationIO_search_Start")
            os.system(""+python_path+"NEW_7_Func_for_Func.pyc")
            print("CommunicationFO_and_CommunicationIO_search_End")
            print("Find")
        elif folder['SEARH_METH']=='FF_PFS':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Find")
        elif folder['SEARH_METH']=='FF':
            print("file_search_Start")
            os.system(""+python_path+"find_files.pyc")
            print("file_search_End")
            print("Find")
        elif folder['SEARH_METH']=='PFS':
            print("file_sort_Start")
            os.system(""+python_path+"Path_File_Sort.pyc")
            print("file_sort_End")
            print("Find")
        elif folder['SEARH_METH']=='C':
            print("class_search_Start")
            os.system(""+python_path+"NEW_2_Class.pyc")
            print("class_search_End")
            print("Find")
        elif folder['SEARH_METH']=='F':
            print("func_search_Start")
            os.system(""+python_path+"NEW_3_Func.pyc")
            print("func_search_End")
            print("Find")
        elif folder['SEARH_METH']=='V':
            print("Variables_search_Start")
            os.system(""+python_path+"NEW_4_Variables.pyc")
            print("Variables_search_End")
            print("Find")
        elif folder['SEARH_METH']=='CPI':
            print("Package_and_Import_search_Start")
            os.system(""+python_path+"NEW_5_Chek_Package_Import.pyc")
            print("Package_and_Import_search_End")
            print("Find")
        elif folder['SEARH_METH']=='ChI':
            print("CommunicationFO_and_CommunicationIO_search_Start")
            os.system(""+python_path+"NEW_7_Func_for_Func.pyc")
            print("CommunicationFO_and_CommunicationIO_search_End")
            print("Find")

##    print(len_files_for_type())
##    list_f=get_file_path()
##    for path in enumerate(list_f, start=1):
##        print(path)
##    os.system("find_files.py")
##    os.system("Path_File_Sort.py")
##    os.system("NEW_2_Class.py")
##    os.system("NEW_3_Func.py")
##    os.system("NEW_4_Variables.py")
##    os.system("NEW_5_Chek_Package_Import.py")
##    os.system("NEW_7_Func_for_Func.py")
##    os.system("NEW_6_File_NEW_JSensor.py")
