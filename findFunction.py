# -*- coding: utf-8 -*-
import datetime #Время
import psycopg2 #PostgreSQL
from _Start_Multy_Java import folder
from find_files import get_file_path as get_list
from Find_border_secses_V2 import borders as borders_func
from NEW_1_ComOrText import QorSlash
from NEW_SUP_CHECK_POS import Char_Pos_in_block_or_not
from NEW_SUP_info_class_or_func import get_class_info_for_file_id
from NEW_SAVE_Param_STR import Save_Param_STR
import re


def create_table_func_PostgreSQL():
    DT=int(folder['DROP_TBL'])
    if DT == 1:
        conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
        cur=conn.cursor()
        cur.execute('''DROP TABLE IF EXISTS ccc_function_list CASCADE''')
        cur.execute('''CREATE TABLE ccc_function_list(
    file_id int,
    parent_class_id int,
    func_id int,
    CA int,
    annotation text,
    name text,
    param_func text,
    line_detect int,
    start_line int,
    start_pos int,
    end_line int,
    end_pos int,
    modifier_and_return_type text,
    have_block_or_not int,
    line text
    )''')
        conn.commit()
##    conn.close

def update_table_func():
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur=conn.cursor()
    cur.execute('UPDATE ccc_function_list set name=trim(from name)')
    conn.commit()
    conn.close()

def Check_Func(list_f = get_list()):

    #Func sintaksis open
    t_modifire_Func=re.compile('^(friend|virtual|inline|static|explicit|auto|register|extern|thread_local|constexpr|const|signed|unsigned|long|short)$')
    t_type_Func=re.compile('([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_][ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_\*]*)')
    t_name_Func=re.compile('[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_:]+')
    #include line_seg open
    line_seg_detected=0
    #
##    t_else=re.compile('(else)')
##    detected_ELSE=0
##    t_if=re.compile('(if)')
##    detected_IF=0
##    t_for=re.compile('(for)')
##    detected_FOR=0
##    t_DO=re.compile('(do)')
##    detected_DO=0
##    t_while=re.compile('(while)')
##    detected_WHILE=0
##    t_switch=re.compile('(switch)')
##    detected_SWITCH=0
##    t_case=re.compile('(case)')
##    detected_CASE=0
##    t_default=re.compile('(default)')
##    detected_DEFAULT=0
    #
##    t_else_if = re.compile('\s*else\s*if\s*\((.*)') # убрал \) перед '
##    t_if = re.compile('\s*if\s*\((.*)')             # убрал \) перед '
##    t_for = re.compile('\s*for\s*\((.*)')           # убрал \) перед '
##    t_DO_while = re.compile('\s*do\s*{')
##    t_while = re.compile('\s*while\s*\((.*)')       # убрал \) перед '
##    t_switch = re.compile('\s*switch\s*\(')
##    t_else = re.compile('\s*else\s*')
##    t_case = re.compile('\s*case\s*.*\:')
##    t_default = re.compile('\s*default\s*\:')
    #include line_seg close
    #@Override
    t_Override = re.compile('\s*\@Override\s*')
    last_elem=''
    #@Override
    global func_id
    func_id = 0
    #Func sintaksis close
    chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])
    for file_id, path in enumerate(list_f, start=1):
        GlobalFileClassInfo = get_class_info_for_file_id(file_id)
        name_local_class_id=0
        name_local_class_name=''
        print(file_id)
##        if file_id !=1:
##            break
##        if file_id != 63:
##            continue
        if chek_search_File_ID !=0 and file_id < chek_search_File_ID:
            continue
        GFModifire=0
        GFModifireSTR=''
        GFType=0
        GFTypeSTR=''
        TypeParamMO=0
        GFBack=0
        GFFunc=0
        GFFuncNAME=''
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
        #
##        control_param=''
        #

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
            for GFCI in GlobalFileClassInfo:
                if GFCI[1]<line_num and line_num <GFCI[2]:
                    name_local_class_id = GFCI[0]
                    name_local_class_name = GFCI[3]
            comment_multy_string_backup = comment_multy_string
            FirstOneOrTwo_backup = FirstOneOrTwo
            go_next_str = 0
            life = re.findall('[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_:]+|[!"#$%&\\\/()*\'+,-./;<=>?@[\\]^_`{|}~\s]', line)
            life_Mass = [((a.start(), a.end())) for a in list(re.finditer('[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_:]+|[!"#$%&\\\/()*\'+,-./;<=>?@[\\]^_`{|}~\s]', line))]
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
                        if param_start!=-1 and param_lock==-1:
                            param_STR+=i
                        continue
                    if QMOE != 0 and elem<=QMOE:
                        if param_start!=-1 and param_lock==-1:
                            param_STR+=i
                        continue
                    #
                    if QMTS != 0 and elem>=QMTS:
                        if param_start!=-1 and param_lock==-1:
                            param_STR+=i
                        continue
                    if QMTE != 0 and elem<=QMTE:
                        if param_start!=-1 and param_lock==-1:
                            param_STR+=i
                        continue
                    #
                    if param_start!=-1 and param_lock==-1:
                        param_STR+=i+' '
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

                    if GFFunc != 0:
                        if i=='(' and param_start==-1:
                            param_start=life_Mass[elem-1][0]
##                            param_SS=line_num
                            param_count_S+=1
                            param_STR+=i
                            continue
                        if i=='(' and param_start!=-1:
                            param_count_S+=1
                            continue
                        if i==')' and param_start!=-1:
                            param_count_L+=1
                            if param_count_S==param_count_L:
                                param_lock=life_Mass[elem-1][0]
##                                param_LS=line_num
                                param_STR.rstrip(' ')
                                #
                                for_bord = open(path[0], encoding=path[1])
                                print(elem)
    ##                            print(life_Mass[elem-1][0])
                                border_f = borders_func(line_num, for_bord, 'func', elem, comment_multy_string_backup, FirstOneOrTwo_backup)
                                for_bord.close()
                                #
                                print(GFModifireSTR)
                                print(GFTypeSTR)
                                print("Name > {}".format(GFFuncNAME))
                                print(annotation_MASS)#?
                                print(border_f)
                                print(line)
                                #
                                func_id+=1
                                #
##                                param_STR=Save_Param_STR(F_Clon, param_SS, param_start, param_LS, param_lock)
                                if name_local_class_id != 0:
                                    func_par_class = name_local_class_id
                                else:
                                    func_par_class = name_local_class_id
                                try:
                                    if border_f[0][0] != 0:
                                        HBON=1
                                    else:
                                        HBON=0
                                    if annotation_MASS:
                                        if len(annotation_MASS)==1:
                                            annotation_STR=annotation_MASS[0]
                                        elif len(annotation_MASS)>1:
                                            for AM in annotation_MASS:
                                                annotation_STR+=AM+','
                                            annotation_STR=annotation_STR.rstrip(',')
                                    else:
                                        annotation_STR=None
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_function_list (file_id,parent_class_id,func_id,CA,annotation,name,param_func,line_detect,start_line,start_pos,end_line,end_pos,modifier_and_return_type,have_block_or_not,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, func_par_class, func_id, 0, annotation_STR, GFFuncNAME, param_STR, line_num, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], GFModifireSTR+GFTypeSTR, HBON, line))
                                    conn.commit()
                                    conn.close()
                                    #
                                except Exception:
                                    annotation_STR=''
                                    #
                                    GFModifire=0
                                    GFModifireSTR=''
                                    GFType=0
                                    GFTypeSTR=''
                                    TypeParamMO=0
                                    GFBack=0
                                    GFFunc=0
                                    GFFuncNAME=''
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
                                    #
                                    last_elem=i
                                    continue
                                annotation_STR=''
                                #
                                GFModifire=0
                                GFModifireSTR=''
                                GFType=0
                                GFTypeSTR=''
                                TypeParamMO=0
                                GFBack=0
                                GFFunc=0
                                GFFuncNAME=''
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
                                #
                                last_elem=i
                                continue
                            continue
                        if param_start!=-1:
                            continue
                        else:
                            GFModifire=0
                            GFModifireSTR=''
                            GFType=0
                            GFTypeSTR=''
                            TypeParamMO=0
                            GFBack=0
                            GFFunc=0
                            GFFuncNAME=''
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
                    if class_access==1:
                        if i=='(' and param_start==-1:
                            param_start=life_Mass[elem-1][0]
##                            param_SS=line_num
                            param_count_S+=1
                            param_STR+=i
                            continue
                        if i=='(' and param_start!=-1:
                            param_count_S+=1
                            continue
                        if i==')' and param_start!=-1:
                            param_count_L+=1
                            if param_count_S==param_count_L:
                                param_lock=life_Mass[elem-1][0]
                                param_LS=line_num
                                param_STR.rstrip(' ')
                                #
                                for_bord = open(path[0], encoding=path[1])
                                print(elem)
                                border_f = borders_func(line_num, for_bord, 'func', elem, comment_multy_string_backup, FirstOneOrTwo_backup)
                                for_bord.close()
                                #
                                print(GFModifireSTR)
                                print(GFTypeSTR)
                                print("Name > {}".format(GFFuncNAME))
                                print(annotation_MASS)#?
                                print(border_f)
                                print(line)
                                #
                                func_id+=1
                                #
                                if name_local_class_id != 0:
                                    func_par_class = name_local_class_id
                                else:
                                    func_par_class = name_local_class_id
                                try:
                                    if border_f[0][0] != 0:
                                        HBON=1
                                    else:
                                        HBON=0
                                    if annotation_MASS:
                                        if len(annotation_MASS)==1:
                                            annotation_STR=annotation_MASS[0]
                                        elif len(annotation_MASS)>1:
                                            for AM in annotation_MASS:
                                                annotation_STR+=AM+','
                                            annotation_STR=annotation_STR.rstrip(',')
                                    else:
                                        annotation_STR=None
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_function_list (file_id,parent_class_id,func_id,CA,annotation,name,param_func,line_detect,start_line,start_pos,end_line,end_pos,modifier_and_return_type,have_block_or_not,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, func_par_class, func_id, 1, annotation_STR, GFTypeSTR, param_STR, line_num, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], GFModifireSTR, HBON, line))
                                    conn.commit()
                                    conn.close()
                                    #
                                except Exception:
                                    annotation_STR=''
                                    #
                                    GFModifire=0
                                    GFModifireSTR=''
                                    GFType=0
                                    GFTypeSTR=''
                                    TypeParamMO=0
                                    GFBack=0
                                    GFFunc=0
                                    GFFuncNAME=''
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
                                    #
                                    last_elem=i
                                    continue
                                annotation_STR=''
                                #
                                GFModifire=0
                                GFModifireSTR=''
                                GFType=0
                                GFTypeSTR=''
                                TypeParamMO=0
                                GFBack=0
                                GFFunc=0
                                GFFuncNAME=''
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
                                #
                                last_elem=i
                                continue
                        if param_start!=-1:
                            continue
                        else:
                            GFModifire=0
                            GFModifireSTR=''
                            GFType=0
                            GFTypeSTR=''
                            TypeParamMO=0
                            GFBack=0
                            GFFunc=0
                            GFFuncNAME=''
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
                    if GFFunc == 0:
                        if annotation_name==1:
                            print(annotation_MASS)
                            if i=='(' and param_start==-1:
                                param_start=life_Mass[elem-1][0]
                                param_count_S+=1
                                param_STR+=i
                                annotation_block=1
                                print('annotation_block')
                                continue
                            elif annotation_block==1:
                                if i=='(' and param_start!=-1:
                                    param_count_S+=1
                                    continue
                                if i==')' and param_start!=-1:
                                    param_count_L+=1
                                    if param_count_S==param_count_L:
                                        param_STR.rstrip(' ')
                                        annotation_MASS[-1]=annotation_MASS[-1]+param_STR
                                        param_STR=''
                                        TypeParamMO=0
                                        param_start=-1
                                        param_count_S=0
                                        param_count_L=0

                                        annotation_block=0
                                        annotation_name=0
                                        continue
                                continue
##                                GFModifire=0
##                                GFModifireSTR=''
##                                GFType=0
##                                GFTypeSTR=''
##                                GFBack=0
##                                GFFunc=0
##                                GFFuncNAME=''
##                                GFPrint=0
##
##                                param_start=-1
##                                param_count_S=0
##                                param_SS=0
##                                param_lock=-1
##                                param_count_L=0
##                                param_LS=0
##                                param_STR=''
##
##                                annotation=0
##                                annotation_STR=''
##                                annotation_name=0
##                                annotation_block=0
##                                class_access=0
                            else:
                                annotation_name=0
                        ######
                        if annotation==1:
                            annotation_MASS.append(i)
                            annotation=0
                            #
                            annotation_name=1
                            #
                            last_elem=i
                            continue
                        if i=='@' and GFType==0 and GFModifire==0:
                            annotation=1
                            #
                            last_elem=i
                            continue
##                        print(i)
##                        print(last_elem)
                        if annotation_MASS or last_elem=='{' or last_elem=='}' or last_elem==';':# or last_elem==')':
                            if t_modifire_Func.search(i) and GFType==0:
##                                if annotation_MASS:
##                                    control_param='annotation'
##                                elif last_elem=='{' or last_elem=='}' or last_elem==';':# or last_elem==')':
##                                    control_param=last_elem
                                GFType=0
                                GFTypeSTR=''
                                TypeParamMO=0
                                GFBack=0
                                GFFunc=0
                                GFFuncNAME=''
                                GFPrint=0
                                param_start=-1
                                param_SS=0
                                param_lock=-1
                                param_LS=0
                                param_STR=''
    ##                            annotation_MASS=[]
    ##                            annotation=0
                                class_access=0
                                #
                                GFModifireSTR+=i+' '
                                GFModifire+=1
                                continue

                            if t_type_Func.search(i) and GFType==0 and i!='break' and i!='case' and i!='class' and i!='const' and i!='continue' and i!='default' and i!='do' and i!='else' and i!='enum'\
                                and i!='for' and i!='goto' and i!='if' and i!='new' and i != 'delete'\
                                 and i!='private' and i!='protected' and i!='public' and i!='return' and i!='static' and i!='switch'\
                                  and i!='this' and i!='while' and i!='true' and i!='false' and i!='null' and i != 'foreach' and i != 'friend' and i != 'virtual' and i != 'inline' and i != 'static' and i != 'explicit' and i != 'auto' and i != 'register' and i != 'extern' and i != 'thread_local' and i != 'constexpr':
                                GFType+=1
                                GFTypeSTR+=i+' '
                                if annotation_MASS:
                                    control_param='annotation'
                                elif last_elem=='{' or last_elem=='}' or last_elem==';' or last_elem==')':
                                    control_param=last_elem
                                continue
                            if GFType!=0 and GFFunc==0 and (i=='[' or i=='<'):
                                if i=='[':
                                    TypeParamMO=1
                                elif i=='<':
                                    maxONE=1
                                    TypeParamMO=2
                                GFTypeSTR+=i
                                continue
                            if GFType!=0 and TypeParamMO!=0 and (i==']' or i=='>'):
                                if TypeParamMO==1 and i==']':
                                    TypeParamMO=0
                                    GFTypeSTR+=i
                                    continue
                                elif TypeParamMO==2 and i=='>':
                                    maxONE=0
                                    TypeParamMO=0
                                    GFTypeSTR+=i
                                    continue
##                                continue
                            elif GFType!=0 and TypeParamMO==2 and t_name_Func.search(i) and maxONE==1:
                                maxONE=0
                                GFTypeSTR+=i
                                continue
##                            if GFType!=0 and TypeParamMO==2:
##                                continue
                            if t_name_Func.search(i) and GFType!=0 and TypeParamMO==0:
                                GFFunc=1
                                GFFuncNAME+=i
                                #
                                last_elem=i
                                continue
                            if i=='(' and param_start==-1 and GFFunc==0 and GFType!=0:
                                try:
                                    if re.search('\s*('+name_local_class_name+')\s*',GFTypeSTR):
                                        class_access=1
                                        param_start=life_Mass[elem-1][0]
    ##                                    param_SS=line_num
                                        param_count_S+=1
                                        param_STR+=i
                                        continue
                                    else:
                                        GFModifire=0
                                        GFModifireSTR=''
                                        GFType=0
                                        GFTypeSTR=''
                                        TypeParamMO=0
                                        GFBack=0
                                        GFFunc=0
                                        GFFuncNAME=''
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
                                        #
                                        last_elem=i
                                        continue
                                except Exception:
                                    GFModifire=0
                                    GFModifireSTR=''
                                    GFType=0
                                    GFTypeSTR=''
                                    TypeParamMO=0
                                    GFBack=0
                                    GFFunc=0
                                    GFFuncNAME=''
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
                                GFFunc=0
                                GFFuncNAME=''
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
                            GFFunc=0
                            GFFuncNAME=''
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
                            #
                            last_elem=i
                            continue
                    else:last_elem=i

    print(func_id)
def Drop_table_func_PostgreSQL():
    DT=int(folder['DROP_TBL'])
    if DT == 1:
        conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
        cur=conn.cursor()
        cur.execute('''DROP TABLE IF EXISTS ccc_function_list CASCADE''')
        conn.commit()
if __name__=='__main__':
##    Drop_table_func_PostgreSQL()
    create_table_func_PostgreSQL()
    Check_Func()
    update_table_func()
