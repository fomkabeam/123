# -*- coding: utf-8 -*-
import psycopg2 #PostgreSQL
import sqlite3
from _Start_Multy_Java import folder
from find_files import get_file_path as get_list
from NEW_1_ComOrText import QorSlash
from NEW_SUP_info_class_or_func import get_class_info_for_file_id
import re

def create_table_variables_PostgreSQL():
    DT=int(folder['DROP_TBL'])
    if DT == 1:
        conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
        # conn = sqlite3.connect('../result.db')
        cur=conn.cursor()
        cur.execute('''DROP TABLE IF EXISTS ccc_variables_v''')
        cur.execute('''CREATE TABLE ccc_variables_v(
    file_id int,
    class_id int,
    func_id int,
    var_id int,
    GOrL text,
    var_access text,
    var_type text,
    var_name text,
    num_line int,
    line text
    )''')
        conn.commit()
def get_func_info_for_file_id(file_id):
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    # conn = sqlite3.connect('../result.db')
    cur = conn.cursor()
    cur.execute("select idfunc, start_line, end_line from ccc_definition_function where file_id = {0}".format(file_id))
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i)
    return list

def Check_Variables(list_f = get_list()):
    #Variable sintaksis open
    t_modifire_Variabl=re.compile('^(unsigned|signed|new|extern|register)$')
    t_type_Variabl=re.compile('([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_][ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_\*]*)')
    t_name_Variabl=re.compile('[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_]+')
    last_elem=''
    #@Override
    global var_id
    var_id = 0
    #Variable sintaksis close
    chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])
    for file_id, path in enumerate(list_f, start=1):
        GlobalFileClassInfo = get_class_info_for_file_id(file_id)
        name_local_class_id=0
        name_local_class_name=''
        GlobalFileFuncInfo = get_func_info_for_file_id(file_id)
        name_local_func_id=0
##        if file_id > 1:
##            continue
        print(file_id)
        if chek_search_File_ID !=0 and file_id < chek_search_File_ID:
            continue
        GFModifire=0
        GFModifireSTR=''
        GFType=0
        GFTypeSTR=''
        TypeParamMO=0
        GFBack=0
        GFVar=0
        GFVarNAME=''
        GFPrint=0

        param_start=-1
        param_count_S=0
        param_SS=0
        param_lock=-1
        param_count_L=0
        param_LS=0
        param_STR=''


        annotation_MASS=[]
        annotation=0
        annotation_STR=''
        annotation_name=0
        annotation_block=0
        class_access=0
        Next_TRY=0
        initialization=0
        GFType_Long=0#<?<?
        F_Clon=[]
        file = open(path[0], encoding=path[1])
        for str1 in file.readlines():
            F_Clon.append(str1)
        file.close()
        file = open(path[0], encoding=path[1])
        comment_multy_string = 0
        comment_multy_string_backup = 0
        FirstOneOrTwo = 0
        FirstOneOrTwo_backup = 0
        for line_num, line in enumerate(file.readlines(), start=1): #1 строка будет определена под цифрой 1, 2 под 2 ... и т.д. (Это важно запомнить!)
##            if line_num>34:
##                continue
            for GFCI in GlobalFileClassInfo:
                if GFCI[1]<line_num and line_num <GFCI[2]:
                    name_local_class_id = GFCI[0]
                    name_local_class_name = GFCI[3]
            for GFFI in GlobalFileFuncInfo:
                if GFFI[1]<line_num and line_num<GFFI[2]:
                    name_local_func_id = GFFI[0]
##                else:
##                    name_local_func_id=0
            comment_multy_string_backup = comment_multy_string
            FirstOneOrTwo_backup = FirstOneOrTwo
            go_next_str = 0
            life = re.findall('[A-Za-z_0-9]+|[^A-Za-z_0-9]', line)
##            print(life)
            life_Mass = [((a.start(), a.end())) for a in list(re.finditer('[A-Za-z_0-9]+|[^A-Za-z_0-9]', line))]
##            print(life_Mass)
##            print(life)
##            print(life_Mass)
            #
            if comment_multy_string == 1:
                GlobalFileSegmentMass = QorSlash(line_num,life,back_comment=1,comment_multy_string=1,FirstCommentOrStr=2)
            elif FirstOneOrTwo == 1:
                GlobalFileSegmentMass = QorSlash(line_num,life,back_comment=0,comment_multy_string = 0,FirstCommentOrStr = 1, back_str = 1, QColl = 1, FirstOneOrTwo = 1)
            elif FirstOneOrTwo == 2:
                GlobalFileSegmentMass = QorSlash(line_num,life,back_comment=0,comment_multy_string = 0,FirstCommentOrStr = 1, back_str = 1, QColl = 1, FirstOneOrTwo = 2)
            else:GlobalFileSegmentMass = QorSlash(line_num,life)
##            print(GlobalFileSegmentMass)
            #
            comment_str_massiv = []#GlobalFileSegmentMass[0][2]
            #
            comment_many_str_massiv = []#GlobalFileSegmentMass[0][3]
            #
            QMasOne = []#GlobalFileSegmentMass[0][1]
            line_have_QMO=0
            QMOS=0
            line_have_QMOS=0
            QMOE=0
            line_have_QMOE=0
            #
            QMasTwo = []#GlobalFileSegmentMass[0][0]
            line_have_QMT=0
            QMTS=0
            line_have_QMTS=0
            QMTE=0
            line_have_QMTE=0
            #
            line_have_one_str_comment = 0
            line_one_str_comment_pos_start = 0
            #
            many_comment_in_one_str = 0#?
            LHMCBlock = [] # (a,b,c) a- 1:2:3 - 1=водной строке: 2=только старт в строке , 3=только конец в строке , b - start , c -end
            have_MC = 0#
            line_have_many_comment_start = 0#
            PosMCS=0
            line_have_many_comment_end = 0#
            PosMCE=0
            line_have_many_comment_block = 0#
            CollMCB = 0#
            #
            HaveOrNotToHaveStrElement = 0
            CollHONTHSE = 0
            #
            line_in_many_comment_block = 0 #?
            #
            #Parser Comment Open
            if GlobalFileSegmentMass[0][2]:
                line_have_one_str_comment = 1
                line_one_str_comment_pos_start = GlobalFileSegmentMass[0][2][0]
##                print("HEEEEEYYYY")
##                print(line_one_str_comment_pos_start)
            if GlobalFileSegmentMass[0][3]:
##                print("GlobalFileSegmentMass[0][3]")
                have_MC = 1
                comment_many_str_massiv = GlobalFileSegmentMass[0][3]
                for CMSM in comment_many_str_massiv:
##                    print(CMSM)
                    if CMSM[0] == 2:
                        if line_have_many_comment_block == 0:
                            line_have_many_comment_block = 1
                        CollMCB+=1#? - ?
                        continue
                    if CMSM[0] == 3:
                        line_have_many_comment_end = 1
                        PosMCE=CMSM[2]
                        continue
                    if CMSM[0] == 1:
                        line_have_many_comment_start = 1
                        PosMCS=CMSM[2]
##                        print('add')
                        continue
            #
            if line_have_many_comment_start==1:
                comment_multy_string = 1
            elif line_have_many_comment_end==1:
                comment_multy_string = 0
            elif comment_multy_string == 1:
                go_next_str = 1
            #Parser Comment Close
            if go_next_str == 0:
                #Parser StrSegment Open
                if GlobalFileSegmentMass[0][1]:
                    HaveOrNotToHaveStrElement=1
                    QMasOne = GlobalFileSegmentMass[0][1]
                    for QMO in QMasOne:
                        if QMO[0] == 2 and line_have_QMO==0:
                            line_have_QMO=1
                            continue
                        if QMO[0] == 1:
                            line_have_QMOS=1
                            QMOS=QMO[2]
                            continue
                        if QMO[0] == 3:
                            line_have_QMOE=1
                            QMOE=QMO[2]
                            continue
                if GlobalFileSegmentMass[0][0]:
                    HaveOrNotToHaveStrElement=1
                    QMasTwo = GlobalFileSegmentMass[0][0]
                    for QMT in QMasTwo:
                        if QMT[0] == 2 and line_have_QMT==0:
                            line_have_QMT=1
                            continue
                        if QMT[0] == 1:
                            line_have_QMTS=1
                            QMTS=QMT[2]
                            continue
                        if QMT[0] == 3:
                            line_have_QMTE=1
                            QMTE=QMT[2]
                            continue
                #@
                if line_have_QMOS==1:
                    FirstOneOrTwo = 1
                elif line_have_QMOE==1:
                    FirstOneOrTwo = 0
                elif FirstOneOrTwo == 1:
                    go_next_str = 1
                #
                if go_next_str==1:
                    continue
                #@
                if line_have_QMTS==1:
                    FirstOneOrTwo = 2
                elif line_have_QMTE==1 and line_have_QMOS==0:
                    FirstOneOrTwo = 0
                elif FirstOneOrTwo == 2:
                    go_next_str = 1
                #
                if go_next_str==1:
                    continue
                #Parser StrSegment Close
                #Parser Class Open
##                print(life)
                for elem, i in enumerate(life,start=1):
                    if re.search('\s',i):
                        continue
                    #Chek_roll_one_comment_Open
                    if line_have_one_str_comment == 1:
                        if elem >= line_one_str_comment_pos_start:
                            continue
                    #Chek_roll_one_comment_Close
                    go_next_elem=0
                    #Chek_roll_many_comment_Open
                    if PosMCS != 0 and elem>=PosMCS:
                        continue
                    if PosMCE != 0 and elem<=PosMCE:
                        continue
                    if line_have_many_comment_block == 1:
                        for CMSM in comment_many_str_massiv:
                            if CMSM[0] == 2 and go_next_elem==0:
                                if CMSM[2]<=elem and elem<=CMSM[3]:
                                    go_next_elem=1
                    if go_next_elem==1:
                        continue
                    #Chek_roll_many_comment_Close
                    #Chek_roll_str_simbol_Open
                    if QMOS != 0 and elem>=QMOS:
##                        if param_start!=-1 and param_lock==-1:
##                            param_STR+=i
                        continue
                    if QMOE != 0 and elem<=QMOE:
##                        if param_start!=-1 and param_lock==-1:
##                            param_STR+=i
                        continue
                    #
                    if QMTS != 0 and elem>=QMTS:
##                        if param_start!=-1 and param_lock==-1:
##                            param_STR+=i
                        continue
                    if QMTE != 0 and elem<=QMTE:
##                        if param_start!=-1 and param_lock==-1:
##                            param_STR+=i
                        continue
                    #
##                    if param_start!=-1 and param_lock==-1:
##                        continue#???<</Чита? А как он найдёт закрытие параметра, если он делает continue ещё до начала поиска закрытия блока? P.S. Мммм
##                        param_STR+=i+' '
                    #
                    if line_have_QMO == 1:
                        for QMO in QMasOne:
                            if QMO[0] == 2 and go_next_elem==0:
                                if QMO[2]<=elem and elem<=QMO[3]:
                                    go_next_elem=1
                    if go_next_elem==1:
                        continue
                    #
                    if line_have_QMT == 1:
                        for QMT in QMasTwo:
                            if QMT[0] == 2 and go_next_elem==0:
                                if QMT[2]<=elem and elem<=QMT[3]:
                                    go_next_elem=1
                    if go_next_elem==1:
                        continue

                    if GFVar!=0:
                        if (i=='['):
                            TypeParamMO=1
                            GFVarNAME+=i
                            continue
                        if TypeParamMO!=0 and i==']':
                            TypeParamMO=0
                            GFVarNAME+=i
                            continue
                        elif TypeParamMO!=0 and i!=']':
                            continue
                        if initialization==1:
                            if i==';':
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                # conn = sqlite3.connect('../result.db')
                                cur = conn.cursor()
                                var_id+=1
                                if '[' in GFVarNAME:
                                    GFVarNAME = GFVarNAME[:GFVarNAME.find('[')]
                                cur.execute("INSERT INTO ccc_variables_v (file_id,class_id,func_id,var_id,GOrL,var_access,var_type,var_name,num_line,line) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                            (file_id, name_local_class_id, name_local_func_id, var_id, '', GFModifireSTR, GFTypeSTR, GFVarNAME, line_num, line))
                                conn.commit()
                                conn.close()
                                #
                                GFModifire=0
                                GFModifireSTR=''
                                GFType=0
                                GFTypeSTR=''
                                TypeParamMO=0
                                GFBack=0
                                GFVar=0
                                GFVarNAME=''
                                GFPrint=0
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                annotation_MASS=[]
                                annotation=0
                                class_access=0
                                Next_TRY=0
                                initialization=0
                                GFType_Long=0#
                                #
                                last_elem=i
                                continue
                            if i==','and param_start==-1 and param_lock==-1:
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                # conn = sqlite3.connect('../result.db')
                                cur = conn.cursor()
                                var_id+=1
                                if '[' in GFVarNAME:
                                    GFVarNAME = GFVarNAME[:GFVarNAME.find('[')]
                                cur.execute("INSERT INTO ccc_variables_v (file_id,class_id,func_id,var_id,GOrL,var_access,var_type,var_name,num_line,line) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                            (file_id, name_local_class_id, name_local_func_id, var_id, '', GFModifireSTR, GFTypeSTR, GFVarNAME, line_num, line))
                                conn.commit()
                                conn.close()
                                #
##                                print(line)
                                initialization=0
                                Next_TRY=1
                                continue
                            if i=='{' and param_start==-1:
                                param_start=2
                                param_count_S+=1
                                continue
                            if i=='{' and param_start==2:
                                param_count_S+=1
                                continue
                            if i=='}' and param_start==2:
                                param_count_L+=1
                                if param_count_S-param_count_L==0:
                                    param_start=-1
                                    param_count_S=0
                                    param_count_L=0
                                    continue
                                continue
                            #-#
                            if i=='(' and param_start==-1:
##                                print(line)
                                param_start=1
                                param_count_S+=1
                                continue
                            if i=='(' and param_start==1:
                                param_count_S+=1
                                continue
                            if i==')' and param_start==1:
                                param_count_L+=1
                                if param_count_S-param_count_L==0:
                                    param_start=-1
                                    param_count_S=0
                                    param_count_L=0
                                    continue
                                continue
                            continue
                        if i==';':
                            conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                            # conn = sqlite3.connect('../result.db')
                            cur = conn.cursor()
                            var_id+=1
                            if '[' in GFVarNAME:
                                GFVarNAME = GFVarNAME[:GFVarNAME.find('[')]
                            cur.execute("INSERT INTO ccc_variables_v (file_id,class_id,func_id,var_id,GOrL,var_access,var_type,var_name,num_line,line) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                        (file_id, name_local_class_id, name_local_func_id, var_id, '', GFModifireSTR, GFTypeSTR, GFVarNAME, line_num, line))
                            conn.commit()
                            conn.close()
                            #
                            GFModifire=0
                            GFModifireSTR=''
                            GFType=0
                            GFTypeSTR=''
                            TypeParamMO=0
                            GFBack=0
                            GFVar=0
                            GFVarNAME=''
                            GFPrint=0
                            param_start=-1
                            param_count_S=0
                            param_SS=0
                            param_lock=-1
                            param_count_L=0
                            param_LS=0
                            param_STR=''
                            annotation_MASS=[]
                            annotation=0
                            class_access=0
                            Next_TRY=0
                            initialization=0
                            GFType_Long=0#
                            #
                            last_elem=i
                            continue
                        if Next_TRY==1:
                            if t_name_Variabl.search(i) and GFType!=0 and TypeParamMO==0:
                                GFVar=1
                                GFVarNAME=i
                                Next_TRY=0
##                                #conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
##                                cur = conn.cursor()
##                                var_id+=1
##                                cur.execute("INSERT INTO ccc_variables_v (file_id,class_id,func_id,var_id,GOrL,var_access,var_type,var_name,num_line,line) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
##                                            (file_id, name_local_class_id, name_local_func_id, var_id, '', GFModifireSTR, GFTypeSTR, GFVarNAME, line_num, line))
##                                conn.commit()
##                                conn.close()
                                continue
                        if i==','and param_start==-1 and param_lock==-1:
                            conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                            # conn = sqlite3.connect('../result.db')
                            cur = conn.cursor()
                            var_id+=1
                            if '[' in GFVarNAME:
                                GFVarNAME = GFVarNAME[:GFVarNAME.find('[')]
                            cur.execute("INSERT INTO ccc_variables_v (file_id,class_id,func_id,var_id,GOrL,var_access,var_type,var_name,num_line,line) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                        (file_id, name_local_class_id, name_local_func_id, var_id, '', GFModifireSTR, GFTypeSTR, GFVarNAME, line_num, line))
                            conn.commit()
                            conn.close()
                            #
                            Next_TRY=1
                            continue
                        if i=='=':
                            initialization=1
                            continue
                        GFModifire=0
                        GFModifireSTR=''
                        GFType=0
                        GFTypeSTR=''
                        TypeParamMO=0
                        GFBack=0
                        GFVar=0
                        GFVarNAME=''
                        GFPrint=0
                        param_start=-1
                        param_count_S=0
                        param_SS=0
                        param_lock=-1
                        param_count_L=0
                        param_LS=0
                        param_STR=''
                        annotation_MASS=[]
                        annotation=0
                        class_access=0
                        Next_TRY=0
                        initialization=0
                        GFType_Long=0#
                        #
                        last_elem=i
                        continue
                    if GFVar==0:
                        if last_elem=='{' or last_elem=='}' or last_elem==';' or last_elem==':':# or last_elem==')':
                            if t_modifire_Variabl.search(i) and GFType==0:
                                GFType=0
                                GFTypeSTR=''
                                TypeParamMO=0
                                GFBack=0
                                GFVar=0
                                GFVarNAME=''
                                GFPrint=0
                                param_start=-1
                                param_SS=0
                                param_lock=-1
                                param_LS=0
                                param_STR=''
                                GFType_Long=0#????????
                                class_access=0#?del?
                                #
                                GFModifireSTR+=i+' '
                                GFModifire+=1
                                continue

                            if t_type_Variabl.search(i) and GFType==0 and i!='auto' and i!='break' and i!='register' and i!='return'\
                                and i!='unsigned' and i!='union' and i!='volatile' and i!='while' and i!='else' and i!='typedef' and i != 'goto'\
                                and i!='default' and i!='continue' and i!='inline' and i!='case' and i!='for' and i!='if' and i != 'delete'\
                                and i!='enum' and i!='struct' and i!='switch' and i!='extern' and i!='signed' and i!='sizeof' and i != 'const' and i != 'class':
                                GFType+=1
                                GFTypeSTR+=i+' '
                                if i == 'long' or i == 'short':
                                    GFType_Long = 1#?
                                continue

                            if GFType_Long!=0 and (i=='long' or i=='int' or i=='double'):
                                #GFType+=1
                                GFTypeSTR+=i+' '
                                continue
                            if GFType!=0 and i=='*':
                                GFType+=1
                                GFTypeSTR+=i
                                continue
                            if t_name_Variabl.search(i) and GFType!=0:
                                GFVar=1
                                GFVarNAME+=i
##                                #conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
##                                cur = conn.cursor()
##                                var_id+=1
##                                cur.execute("INSERT INTO ccc_variables_v (file_id,class_id,func_id,var_id,GOrL,var_access,var_type,var_name,num_line,line) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
##                                            (file_id, name_local_class_id, name_local_func_id, var_id, '', GFModifireSTR, GFTypeSTR, GFVarNAME, line_num, line))
##                                conn.commit()
##                                conn.close()
                                continue

                            else:
                                GFModifire=0
                                GFModifireSTR=''
                                GFType=0
                                GFTypeSTR=''
                                TypeParamMO=0
                                GFBack=0
                                GFVar=0
                                GFVarNAME=''
                                GFPrint=0
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                annotation_MASS=[]
                                annotation=0
                                class_access=0
                                GFType_Long=0
                                #
                                last_elem=i
                                continue
                        else:
                            GFModifire=0
                            GFModifireSTR=''
                            GFType=0
                            GFTypeSTR=''
                            TypeParamMO=0
                            GFBack=0
                            GFVar=0
                            GFVarNAME=''
                            GFPrint=0
                            param_start=-1
                            param_count_S=0
                            param_SS=0
                            param_lock=-1
                            param_count_L=0
                            param_LS=0
                            param_STR=''
                            annotation_MASS=[]
                            annotation=0
                            class_access=0
                            GFType_Long=0
                            #
                            last_elem=i
                            continue
                    else:last_elem=i


if __name__=='__main__':
    create_table_variables_PostgreSQL()
    Check_Variables()
