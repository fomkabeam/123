# -*- coding: utf-8 -*-
import datetime #Время
import psycopg2 #PostgreSQL
from _Start_Multy_Java import folder
from find_files import get_file_path as get_list
from Find_border_secses_V2 import borders as borders_func
from NEW_1_ComOrText import QorSlash
from NEW_SUP_CHECK_POS import Char_Pos_in_block_or_not
from NEW_SUP_info_class_or_func import get_class_info_for_file_id, get_func_info_for_file_id
from NEW_SAVE_Param_STR import Save_Param_STR
import re


def create_table_line_seg_PostgreSQL():
    DT=int(folder['DROP_TBL'])
    if DT == 1:
        conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
        cur=conn.cursor()
        cur.execute('''DROP TABLE IF EXISTS ccc_Line_Seg''')
        cur.execute('''CREATE TABLE ccc_Line_Seg(
    file_id int,
    parent_class_id int,
    parent_func_id int,
    line_seg_id int,
    name text,
    param_L_S text,
    line_detect int,
    start_line int,
    start_pos int,
    end_line int,
    end_pos int,
    have_block_or_not int,
    L_IF_EL int,
    line text
    )''')
        conn.commit()

def Check_Line_Seg(list_f = get_list()):
    #include line_seg open
    line_seg_detected=0
    num_line_detected=0
    #

    detected_ELSE_IF=0
    t_else=re.compile('^else$')
    detected_ELSE=0
    t_if=re.compile('^if$')
    detected_IF=0
    t_for=re.compile('^for$')
    detected_FOR=0
    t_DO=re.compile('^do$')
    detected_DO=0
    t_while=re.compile('^while$')
    detected_WHILE=0
    t_switch=re.compile('^switch$')
    detected_SWITCH=0
    t_case=re.compile('^case$')
    detected_CASE=0
    question_mark=0
    t_default=re.compile('^default$')
    detected_DEFAULT=0
    #include line_seg close
    global line_seg_id
    line_seg_id=0

    #line_seg sintaksis close
    chek_search_File_ID = int(folder['FILE_ID_IN_TBL_SEARCH'])
    for file_id, path in enumerate(list_f, start=1):
        file_id=path[2]
        L_LS_MASS=[]#L_LS_MASS.pop(i) <- удаление еллемента
        #
##        GlobalFileClassInfo = get_class_info_for_file_id(file_id)
        GlobalFileFuncInfo = get_func_info_for_file_id(file_id)
        name_local_class_id=0
        name_local_func_id=0
##        print(file_id)
##        if file_id != 1:
##            break
        print(file_id)
        if chek_search_File_ID !=0 and file_id < chek_search_File_ID:
            continue
        elem_for_DO_WHILE=[]
        chek_while=0#? может переименовать?
        param_start=-1
        param_count_S=0
        param_SS=0
        param_lock=-1
        param_count_L=0
        param_LS=0
        param_STR=''

        integrated_LS=-1
        line_seg_started=0
        line_seg_detected=0

        switch_block=[]
        IN_SWITCH_BLOCK=0

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
            if line.find('#define') != -1 or line.find('# define') != -1 or line.find('#endif') != -1 or line.find('# endif') != -1 or line.find('#ifdef') != -1 or line.find('# ifdef') != -1 or line.find('#else') != -1 or line.find('# else') != -1 or line.find('#') == 0:
                continue
            name_local_class_id=0
            name_local_func_id=0
            for GFFI in GlobalFileFuncInfo:
                if GFFI[2]<line_num and line_num <GFFI[3]:
                    name_local_class_id = GFFI[0]
                    name_local_func_id = GFFI[1]
            comment_multy_string_backup = comment_multy_string
            FirstOneOrTwo_backup = FirstOneOrTwo
            go_next_str = 0
            life = re.findall('[A-Za-z_0-9]+|[^A-Za-z_0-9]', line)
            life_Mass = [((a.start(), a.end())) for a in list(re.finditer('[A-Za-z_0-9]+|[^A-Za-z_0-9]', line))]
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
            #print(GlobalFileSegmentMass)
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
##                    print(i)
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

                    swap=0
                    if switch_block:
                        while(switch_block and swap==0): #Ошибка при конструкции switch (..) \
                            # print('Error: ', end='')
                            if line_num==switch_block[-1][1] and elem>=switch_block[-1][2]:
                                IN_SWITCH_BLOCK=switch_block[-1][0]
                                swap=1
                                # print('1')
                                continue
                            if line_num==switch_block[-1][3] and elem<switch_block[-1][4]:
                                IN_SWITCH_BLOCK=switch_block[-1][0]
                                swap=1
                                # print('2')
                                continue
                            if line_num>switch_block[-1][1] and line_num<switch_block[-1][3]:
                                IN_SWITCH_BLOCK=switch_block[-1][0]
                                swap=1
                                # print('3')
                                continue
                            if line_num==switch_block[-1][3] and elem==switch_block[-1][4]:
                                del switch_block[-1]
                                IN_SWITCH_BLOCK=0
                                # print('4')
                                continue
                            else:
                                IN_SWITCH_BLOCK=switch_block[-1][0]
                                swap=1
                                # print('3')
                                continue

                    if line_seg_detected==1:
                        if detected_SWITCH==1:
                            if i=='(' and param_start==-1:
                                param_start=life_Mass[elem-1][0]
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
                                    param_STR.rstrip(' ')
                                    #
                                    for_bord = open(path[0], encoding=path[1])
                                    print(line_num, line)
                                    border_f = borders_func(line_num, for_bord, 'SWITCH', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                    for_bord.close()
                                    #
                                    if border_f == None:
                                        param_start=-1
                                        param_count_S=0
                                        param_SS=0
                                        param_lock=-1
                                        param_count_L=0
                                        param_LS=0
                                        param_STR=''
                                        detected_SWITCH=0
                                        line_seg_started=0
                                        line_seg_detected=0
                                        num_line_detected=0
                                        continue
                                    line_seg_id+=1
                                    #
                                    # try:
                                    if border_f[0][0] != 0:
                                        HBON=1
                                    else:
                                        HBON=0
                                    #
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'SWITCH', param_STR, num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                    conn.commit()
                                    conn.close()
                                    #
##                                    IN_SWITCH_BLOCK=1
                                    # print(border_f)
                                    switch_block.append((line_seg_id, border_f[0][0], border_f[0][2], border_f[1][0], border_f[1][2]))
##                                    switch_open_block.append((border_f[0][0],border_f[0][2]))
##                                    switch_close_block.append((border_f[1][0]),border_f[1][2]))
                                    #
                                    # except Exception:
                                    #     param_start=-1
                                    #     param_count_S=0
                                    #     param_SS=0
                                    #     param_lock=-1
                                    #     param_count_L=0
                                    #     param_LS=0
                                    #     param_STR=''
                                    #     detected_SWITCH=0
                                    #     line_seg_started=0
                                    #     line_seg_detected=0
                                    #     num_line_detected=0
                                    #     continue

                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_SWITCH=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    continue
                                continue
                            if param_start!=-1:
                                continue
                            else:
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_SWITCH=0
                                line_seg_started=0
                                line_seg_detected=0
                                num_line_detected=0
                        if detected_WHILE==1:
                            if param_lock!=-1:
                                if t_if.search(i) and integrated_LS==-1:
                                    detected_IF=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='IF'
##                                    L_LS_MASS.append('IF')
                                if t_for.search(i) and integrated_LS==-1:
                                    detected_FOR=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='FOR'
##                                    continue
                                if t_DO.search(i) and integrated_LS==-1:
                                    detected_DO=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='DO'
##                                    continue
                                if t_while.search(i) and integrated_LS==-1:
                                    detected_WHILE=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='WHILE'
##                                    continue
                                if t_switch.search(i) and integrated_LS==-1:
                                    detected_SWITCH=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='SWITCH'
##                                    continue
                                if i==';':
##                                    param_lock=life_Mass[elem-1][0]
##                                    param_STR.rstrip(' ')
##                                    line_seg_started=line_num
                                    line_seg_id+=1
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'WHILE', param_STR, line_num, line_seg_started, param_lock, line_num, life_Mass[elem-1][0], -5, 0, line))
                                    conn.commit()
                                    conn.close()
                                    #
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_WHILE=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    line_seg_started=0
                                    continue
                                if integrated_LS!=-1:
                                    line_seg_id+=1
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'WHILE', param_STR, num_line_detected, line_seg_started, param_lock, line_num, integrated_LS, 2, 0, line))
                                    conn.commit()
                                    conn.close()

                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    if integrated_LS_name!='WHILE':
                                        detected_WHILE=0
                                    if integrated_LS_name=='DO':
                                        DO_simbol_last=life_Mass[elem-1][1]
                                    line_seg_started=elem
                                    line_seg_detected=1
                                    num_line_detected=line_num
                                    integrated_LS=-1
                                    line_seg_started=0
                                    continue
                                if integrated_LS==-1:
                                    #
                                    for_bord = open(path[0], encoding=path[1])
                                    print(line_num, line)

                                    border_f = borders_func(line_num, for_bord, 'WHILE', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                    for_bord.close()
                                    if border_f == None:
                                        param_start=-1
                                        param_count_S=0
                                        param_SS=0
                                        param_lock=-1
                                        param_count_L=0
                                        param_LS=0
                                        param_STR=''
                                        detected_WHILE=0
                                        line_seg_started=0
                                        line_seg_detected=0
                                        num_line_detected=0
                                        line_seg_started=0
                                        continue
                                    #
                                    line_seg_id+=1
                                    #
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    # try:
                                    if border_f[0][0] != 0:
                                        HBON=1
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'WHILE', param_STR, line_num, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                    else:
                                        HBON=0
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'WHILE', param_STR, num_line_detected, line_seg_started, param_lock, border_f[1][0], border_f[1][1], HBON, 0, line))
                                    #
##                                    cur.execute("INSERT INTO Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,line)\
##        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
##                                                (file_id, 0, 0, line_seg_id, 'WHILE', param_STR, line_num, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, line))
                                    # except Exception:
                                    #     conn.commit()
                                    #     conn.close()
                                    #     #
                                    #     param_start=-1
                                    #     param_count_S=0
                                    #     param_SS=0
                                    #     param_lock=-1
                                    #     param_count_L=0
                                    #     param_LS=0
                                    #     param_STR=''
                                    #     detected_WHILE=0
                                    #     line_seg_started=0
                                    #     line_seg_detected=0
                                    #     num_line_detected=0
                                    #     line_seg_started=0
                                    #     continue
                                    conn.commit()
                                    conn.close()
                                    #
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_WHILE=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    line_seg_started=0
                                    continue
                            if param_lock==-1:
                                if i=='(' and param_start==-1:
                                    param_start=life_Mass[elem-1][0]
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
                                        param_STR.rstrip(' ')
                                        line_seg_started=line_num
                                        continue
                                    continue
                                if param_start!=-1:
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_WHILE=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                        if detected_FOR==1:
                            if param_lock!=-1:
                                if t_if.search(i) and integrated_LS==-1:
                                    detected_IF=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='IF'
##                                    L_LS_MASS.append('IF')
                                if t_for.search(i) and integrated_LS==-1:
                                    detected_FOR=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='FOR'
##                                    continue
                                if t_DO.search(i) and integrated_LS==-1:
                                    detected_DO=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='DO'
##                                    continue
                                if t_while.search(i) and integrated_LS==-1:
                                    detected_WHILE=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='WHILE'
##                                    continue
                                if t_switch.search(i) and integrated_LS==-1:
                                    detected_SWITCH=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='SWITCH'
##                                    continue
                                if integrated_LS!=-1:
                                    line_seg_id+=1
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'FOR', param_STR, num_line_detected, line_seg_started, param_lock, line_num, integrated_LS, 2, 0, line))
                                    conn.commit()
                                    conn.close()
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    if integrated_LS_name!='FOR':
                                        detected_FOR=0
                                    if integrated_LS_name=='DO':
                                        DO_simbol_last=life_Mass[elem-1][1]
                                    line_seg_started=elem
                                    line_seg_detected=1
                                    num_line_detected=line_num
                                    integrated_LS=-1
                                    line_seg_started=0
                                    continue
                                if integrated_LS==-1:
                                    #
                                    for_bord = open(path[0], encoding=path[1])
                                    print(line_num, line)
                                    border_f = borders_func(line_num, for_bord, 'FOR', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                    for_bord.close()
                                    #
                                    #
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    if border_f == None:
                                        conn.commit()
                                        conn.close()
                                        param_start=-1
                                        param_count_S=0
                                        param_SS=0
                                        param_lock=-1
                                        param_count_L=0
                                        param_LS=0
                                        param_STR=''
                                        detected_FOR=0
                                        line_seg_started=0
                                        line_seg_detected=0
                                        num_line_detected=0
                                        line_seg_started=0
                                        continue
                                    line_seg_id+=1
                                    if border_f[0][0] != 0:
                                        HBON=1
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'FOR', param_STR, num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                    else:
                                        HBON=0
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'FOR', param_STR, num_line_detected, line_seg_started, param_lock, border_f[1][0], border_f[1][1], HBON, 0, line))
                                        #

    ##                                    cur.execute("INSERT INTO Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,line)\
    ##        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
    ##                                                (file_id, 0, 0, line_seg_id, 'FOR', param_STR, line_num, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, line))
                                    conn.commit()
                                    conn.close()
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_FOR=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    line_seg_started=0
                                    continue
                            if param_lock==-1:
                                if i=='(' and param_start==-1:
                                    param_start=life_Mass[elem-1][0]
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
                                        param_STR.rstrip(' ')
                                        line_seg_started=line_num
                                        continue
                                    continue
                                if param_start!=-1:
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_FOR=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                        if detected_IF==1:
                            if param_lock!=-1:
                                if t_if.search(i) and integrated_LS==-1:
                                    detected_IF=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='IF'
##                                    L_LS_MASS.append('IF')
                                if t_for.search(i) and integrated_LS==-1:
                                    detected_FOR=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='FOR'
##                                    continue
                                if t_DO.search(i) and integrated_LS==-1:
                                    detected_DO=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='DO'
##                                    continue
                                if t_while.search(i) and integrated_LS==-1:
                                    detected_WHILE=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='WHILE'
##                                    continue
                                if t_switch.search(i) and integrated_LS==-1:
                                    detected_SWITCH=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='SWITCH'
##                                    continue
                                if integrated_LS!=-1:
                                    line_seg_id+=1
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'IF', param_STR, num_line_detected, line_seg_started, param_lock, line_num, integrated_LS, 2, 0, line))
                                    conn.commit()
                                    conn.close()
                                    L_LS_MASS.append(('IF',line_seg_id,2))
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    if integrated_LS_name!='IF':
                                        detected_IF=0
                                    if integrated_LS_name=='DO':
                                        DO_simbol_last=life_Mass[elem-1][1]
                                    line_seg_started=elem
                                    line_seg_detected=1
                                    num_line_detected=line_num
                                    integrated_LS=-1
                                    line_seg_started=0
                                    continue
                                if integrated_LS==-1:
                                    #
                                    for_bord = open(path[0], encoding=path[1])
                                    print(line_num, line)
                                    border_f = borders_func(line_num, for_bord, 'IF', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                    for_bord.close()
                                    #

                                    #
                                    if border_f == None:
                                        param_start=-1
                                        param_count_S=0
                                        param_SS=0
                                        param_lock=-1
                                        param_count_L=0
                                        param_LS=0
                                        param_STR=''
                                        detected_IF=0
                                        line_seg_started=0
                                        line_seg_detected=0
                                        num_line_detected=0
                                        line_seg_started=0
                                        continue
                                    line_seg_id+=1
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    if border_f[0][0] != 0:
                                        HBON=1
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,L_IF_EL,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'IF', param_STR, num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                        L_LS_MASS.append(('IF',line_seg_id,1))
                                    else:
                                        HBON=0
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'IF', param_STR, num_line_detected, line_seg_started, param_lock, border_f[1][0], border_f[1][1], HBON, 0, line))
                                        L_LS_MASS.append(('IF',line_seg_id,0))
                                    conn.commit()
                                    conn.close()
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_IF=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    line_seg_started=0
                                    continue
                            if param_lock==-1:
                                if i=='(' and param_start==-1:
                                    param_start=life_Mass[elem-1][0]
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
                                        param_STR.rstrip(' ')
                                        line_seg_started=line_num
                                        continue
                                    continue
                                if param_start!=-1:
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_IF=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                        if detected_ELSE_IF==1:
                            if param_lock!=-1:
                                if t_if.search(i) and integrated_LS==-1:
                                    detected_IF=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='IF'
##                                    L_LS_MASS.append('IF')
                                if t_for.search(i) and integrated_LS==-1:
                                    detected_FOR=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='FOR'
##                                    continue
                                if t_DO.search(i) and integrated_LS==-1:
                                    detected_DO=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='DO'
##                                    continue
                                if t_while.search(i) and integrated_LS==-1:
                                    detected_WHILE=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='WHILE'
##                                    continue
                                if t_switch.search(i) and integrated_LS==-1:
                                    detected_SWITCH=1
                                    integrated_LS=life_Mass[elem-1][0]
                                    integrated_LS_name='SWITCH'
##                                    continue
                                if integrated_LS!=-1:
                                    if L_LS_MASS:
                                        line_seg_id+=1
                                        conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                        cur = conn.cursor()
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, L_LS_MASS[-1][1], line_seg_id, 'ELSE_IF', param_STR, num_line_detected, line_seg_started, param_lock, line_num, integrated_LS, 2, 0, line))
    ##                                    L_LS_MASS.append(('ELSE_IF',line_seg_id,2))
                                        conn.commit()
                                        conn.close()
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_ELSE_IF=0
                                    if integrated_LS_name=='DO':
                                        DO_simbol_last=life_Mass[elem-1][1]
                                    line_seg_started=elem
                                    line_seg_detected=1
                                    num_line_detected=line_num
                                    integrated_LS=-1
                                    line_seg_started=0
                                    continue
                                if integrated_LS==-1:
                                    #
                                    for_bord = open(path[0], encoding=path[1])
                                    print(line_num, line)
                                    # print("else_if")
                                    # print(line_seg_started)
                                    border_f = borders_func(line_num, for_bord, 'ELSE_IF', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                    for_bord.close()
                                    #

                                    #
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    try:
                                        if border_f[0][0] != 0:
                                            line_seg_id+=1
                                            HBON=1
                                            cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, L_LS_MASS[-1][1], line_seg_id, 'ELSE_IF', param_STR, num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
    ##                                        L_LS_MASS.append(('ELSE_IF',line_seg_id,1))
                                        else:
                                            line_seg_id+=1
                                            HBON=0
                                            cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, L_LS_MASS[-1][1], line_seg_id, 'ELSE_IF', param_STR, num_line_detected, line_seg_started, param_lock, border_f[1][0], border_f[1][1], HBON, 0, line))
                                    except Exception:
                                        conn.commit()
                                        conn.close()
                                        param_start=-1
                                        param_count_S=0
                                        param_SS=0
                                        param_lock=-1
                                        param_count_L=0
                                        param_LS=0
                                        param_STR=''
                                        detected_ELSE_IF=0
                                        line_seg_started=0
                                        line_seg_detected=0
                                        num_line_detected=0
                                        continue
                                    conn.commit()
                                    conn.close()
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_ELSE_IF=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    continue
                            if param_lock==-1:
                                if i=='(' and param_start==-1:
                                    param_start=life_Mass[elem-1][0]
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
                                        param_STR.rstrip(' ')
                                        line_seg_started=line_num
                                        continue
                                    continue
                                if param_start!=-1:
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_ELSE_IF=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0

                        if detected_ELSE==1:
                            if t_if.search(i):
                                detected_ELSE=0
                                detected_ELSE_IF=1
                                line_seg_started=elem
                                num_line_detected=line_num
##                                L_LS_MASS.pop()
##                                L_LS_MASS.append('ELSE_IF')
                                continue
                            if t_for.search(i) and integrated_LS==-1:
                                detected_FOR=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='FOR'
##                                    continue
                            if t_DO.search(i) and integrated_LS==-1:
                                detected_DO=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='DO'
##                                    continue
                            if t_while.search(i) and integrated_LS==-1:
                                detected_WHILE=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='WHILE'
##                                    continue
                            if t_switch.search(i) and integrated_LS==-1:
                                detected_SWITCH=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='SWITCH'
##                                    continue
                            if integrated_LS!=-1:
                                if L_LS_MASS:
                                    line_seg_id+=1
                                    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                    cur = conn.cursor()
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, L_LS_MASS[-1][1], line_seg_id, 'ELSE', '', num_line_detected, num_line_detected, else_simbol_last, line_num, integrated_LS, 2, 0, line))
                                    conn.commit()
                                    conn.close()
                                    L_LS_MASS.pop(-1)
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_ELSE=0
                                if integrated_LS_name=='DO':
                                    DO_simbol_last=life_Mass[elem-1][1]
                                line_seg_started=elem
                                line_seg_detected=1
                                num_line_detected=line_num
                                integrated_LS=-1
                                line_seg_started=0
                                else_simbol_last=0#?
                                continue
                            if integrated_LS==-1:
                                #
                                for_bord = open(path[0], encoding=path[1])
                                print(line_num, line)
                                border_f = borders_func(line_num, for_bord, 'ELSE', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                for_bord.close()
                                #


                                if border_f == None:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_ELSE=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    else_simbol_last=0#?
                                    continue
                                #
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                cur = conn.cursor()
                                if L_LS_MASS:
                                    line_seg_id+=1
                                    if border_f[0][0] != 0:
                                        HBON=1
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, L_LS_MASS[-1][1], line_seg_id, 'ELSE', '', num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                        L_LS_MASS.pop(-1)
                                    else:
                                        HBON=0
                                        cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                    (file_id, name_local_class_id, L_LS_MASS[-1][1], line_seg_id, 'ELSE', '', num_line_detected, num_line_detected, else_simbol_last, border_f[1][0], border_f[1][1], HBON, 0, line))
                                        L_LS_MASS.pop(-1)
                                conn.commit()
                                conn.close()
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_ELSE=0
                                line_seg_started=0
                                line_seg_detected=0
                                num_line_detected=0
                                else_simbol_last=0#?
                                continue
##                            else:
                            detected_ELSE=0
                            line_seg_started=0
                            line_seg_detected=0
                            num_line_detected=0
                        if detected_DO==1:

                            if t_if.search(i) and integrated_LS==-1:
                                detected_IF=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='IF'
##                                L_LS_MASS.append('IF')
                            if t_for.search(i) and integrated_LS==-1:
                                detected_FOR=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='FOR'
##                                    continue
                            if t_DO.search(i) and integrated_LS==-1:
                                #
                                detected_DO=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='DO'
##                                    continue
                            if t_while.search(i) and integrated_LS==-1:
                                detected_WHILE=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='WHILE'
##                                    continue
                            if t_switch.search(i) and integrated_LS==-1:
                                detected_SWITCH=1
                                integrated_LS=life_Mass[elem-1][0]
                                integrated_LS_name='SWITCH'
##                                    continue
                            if integrated_LS!=-1:
                                line_seg_id+=1
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                cur = conn.cursor()
                                cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                            (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'DO', '', num_line_detected, num_line_detected, DO_simbol_last, line_num, integrated_LS, 2, 0, line))

                                line_seg_id+=1

                                conn.commit()

                                cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                            (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'WHILE', '', 0, 0, 0, 0, 0, -1, 0, ''))
                                conn.commit()
                                conn.close()
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                if integrated_LS_name!='DO':
                                    detected_DO=0
                                if integrated_LS_name=='DO':
                                    DO_simbol_last=life_Mass[elem-1][1]
                                elem_for_DO_WHILE.append(line_seg_id)#?
                                line_seg_started=elem
                                line_seg_detected=1
                                num_line_detected=line_num
                                integrated_LS=-1
                                line_seg_started=0
                                continue
                            if integrated_LS==-1:
                                #
                                for_bord = open(path[0], encoding=path[1])
                                print(line_num, line)
                                border_f = borders_func(line_num, for_bord, 'DO', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                for_bord.close()
                                #

                                #
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                cur = conn.cursor()
                                if border_f == None:
                                    conn.commit()
                                    conn.close()

                                    elem_for_DO_WHILE.append(line_seg_id)
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_DO=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    DO_simbol_last=0#?
                                line_seg_id+=1
                                if border_f[0][0] != 0:
                                    HBON=1
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'DO', '', num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, 0, line))
                                else:
                                    HBON=0
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'DO', '', num_line_detected, num_line_detected, DO_simbol_last, border_f[1][0], border_f[1][1], HBON, 0, line))
                                    #

        ##                            cur.execute("INSERT INTO Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,line)\
        ##VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
        ##                                        (file_id, 0, 0, line_seg_id, 'DO', '', num_line_detected, border_f[0][0], border_f[0][1], border_f[1][0], border_f[1][1], HBON, line))
                                line_seg_id+=1

                                conn.commit()

                                cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                            (file_id, name_local_class_id, name_local_func_id, line_seg_id, 'WHILE', '', 0, 0, 0, 0, 0, -1, 0, ''))
                                conn.commit()
                                conn.close()

                                elem_for_DO_WHILE.append(line_seg_id)
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_DO=0
                                line_seg_started=0
                                line_seg_detected=0
                                num_line_detected=0
                                DO_simbol_last=0#?
                                continue
##                            else:
##                            detected_DO=0
##                            line_seg_started=0
##                            line_seg_detected=0
##                            num_line_detected=0
##                        continue #detected_DEFAULT
                        if detected_DEFAULT==1:
                            if param_lock!=-1:
                                HBON=0
                                if i=='{':
                                    param_lock=life_Mass[elem-1][0]
                                    line_seg_started=line_num
                                    HBON=1
                                #
                                line_seg_id+=1
                                #
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                cur = conn.cursor()
                                if HBON==1:
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, -1, IN_SWITCH_BLOCK, line_seg_id, 'DEFAULT', param_STR, num_line_detected, line_seg_started, param_lock, 0, 0, -2, 0, line))
                                else:
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, -1, IN_SWITCH_BLOCK, line_seg_id, 'DEFAULT', param_STR, num_line_detected, line_seg_started, param_lock, 0, 0, 0, 0, line))
                                conn.commit()
                                conn.close()
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_DEFAULT=0
                                line_seg_started=0
                                line_seg_detected=0
                                num_line_detected=0
                                line_seg_started=0#? Необходимо ли добавиль обнуление параметра в else блока param_lock==-1 ?
##                                continue#?
                            else:
                                if i==':':
                                    try:
                                        if ':' in life[elem:]:
                                            continue
                                    except Exception:
                                        pass
                                    param_lock=life_Mass[elem-1][0]
##                                    param_STR.rstrip(' ')
##                                    param_STR.rstrip(':')
                                    line_seg_started=line_num
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_DEFAULT=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    #
                        if detected_CASE==1:
                            if param_lock!=-1:
                                HBON=0
                                if i=='{':
                                    param_lock=life_Mass[elem-1][0]
                                    line_seg_started=line_num
                                    HBON=1
                                #
                                line_seg_id+=1
                                #
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                cur = conn.cursor()
                                if HBON==1:
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, -1, IN_SWITCH_BLOCK, line_seg_id, 'CASE', param_STR, num_line_detected, line_seg_started, param_lock, 0, 0, -2, 0, line))
                                else:
                                    cur.execute("INSERT INTO ccc_Line_Seg (file_id,parent_class_id,parent_func_id,line_seg_id,name,param_L_S,line_detect,start_line,start_pos,end_line,end_pos,have_block_or_not,l_if_el,line)\
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",\
                                                (file_id, -1, IN_SWITCH_BLOCK, line_seg_id, 'CASE', param_STR, num_line_detected, line_seg_started, param_lock, 0, 0, 0, 0, line))
                                conn.commit()
                                conn.close()
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_CASE=0
                                line_seg_started=0
                                line_seg_detected=0
                                num_line_detected=0
                                question_mark=0
                                line_seg_started=0#? Необходимо ли добавиль обнуление параметра в else блока param_lock==-1 ?
##                                continue#?
                            if param_lock==-1:
                                if i=='?':
                                    question_mark+=1
                                if i==':' and param_start!=-1:
                                    if question_mark!=0:
                                        question_mark-=1
                                        continue
                                    try:
                                        if ':' == life[elem] or ':' == life[elem - 2]:
                                            continue
                                    except Exception:
                                        pass
                                    param_lock=life_Mass[elem-1][0]
                                    param_STR.rstrip(' ')
##                                    param_STR.rstrip(':')
                                    line_seg_started=line_num
                                    continue
                                if param_start!=-1:
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_CASE=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    question_mark=0
                    if line_seg_detected==0:
                        if t_else.search(i):
##                            L_LS_MASS.append('ELSE')
                            print("i see ELSE ^_^")
                            detected_ELSE=1
                            line_seg_started=elem
                            else_simbol_last=life_Mass[elem-1][1]#?
                            line_seg_detected=1
                            num_line_detected=line_num
                            continue
                        if t_if.search(i):
##                            L_LS_MASS.append('IF')
                            print("i see IF ^_^")
                            detected_IF=1
                            line_seg_started=elem
                            line_seg_detected=1
                            num_line_detected=line_num
                            continue
                        if t_for.search(i):
                            detected_FOR=1
                            print("i see FOR ^_^")
                            line_seg_started=elem
                            line_seg_detected=1
                            num_line_detected=line_num
                            continue
                        if t_DO.search(i):
                            detected_DO=1
                            print("i see DO ^_^")
                            line_seg_started=elem
                            DO_simbol_last=life_Mass[elem-1][1]#?
                            line_seg_detected=1
                            num_line_detected=line_num
                            continue
                        if t_while.search(i) and not elem_for_DO_WHILE:
                            detected_WHILE=1
                            print("i see WHILE ^_^")
                            line_seg_started=elem
                            line_seg_detected=1
                            num_line_detected=line_num#?
                            continue
                        if t_while.search(i) and elem_for_DO_WHILE:
##                            print("AHAHAHAHA")
##                            print(param_lock)
                            while_start = life_Mass[elem-1][0]
                            chek_while=1
                            num_line_detected=line_num
                            continue
                        if chek_while==1:
                            if param_lock!=-1:
                                #
                                for_bord = open(path[0], encoding=path[1])
                                print(line_num, line)
                                border_f = borders_func(line_num, for_bord, 'WHILE', elem-1, comment_multy_string_backup, FirstOneOrTwo_backup)
                                for_bord.close()
                                #
                                conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
                                cur = conn.cursor()
                                try:
                                    cur.execute("UPDATE ccc_Line_Seg SET param_L_S=%s, line_detect=%s, start_line=%s, start_pos=%s, end_line=%s, end_pos=%s, line=%s where line_seg_id = %s",\
                                                (param_STR, num_line_detected, num_line_detected, while_start, border_f[1][0], border_f[1][1], line, elem_for_DO_WHILE[-1]))
                                #
                                except Exception:
                                    conn.commit()
                                conn.commit()
                                cur.execute("UPDATE ccc_Line_Seg SET end_line=%s, end_pos=%s where line_seg_id = %s",\
                                            (num_line_detected, while_start, elem_for_DO_WHILE[-1]-1))
                                #
                                conn.commit()
                                conn.close()
                                #
                                del elem_for_DO_WHILE[-1]
                                #
                                param_start=-1
                                param_count_S=0
                                param_SS=0
                                param_lock=-1
                                param_count_L=0
                                param_LS=0
                                param_STR=''
                                detected_WHILE=0
                                line_seg_started=0
                                line_seg_detected=0
                                num_line_detected=0
                                line_seg_started=0
                                chek_while=0
                                continue
                            if param_lock==-1:
                                if i=='(' and param_start==-1:
                                    param_start=life_Mass[elem-1][0]
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
                                        param_STR.rstrip(' ')
                                        line_seg_started=line_num
                                        continue
                                    continue
                                if param_start!=-1:
                                    continue
                                else:
                                    param_start=-1
                                    param_count_S=0
                                    param_SS=0
                                    param_lock=-1
                                    param_count_L=0
                                    param_LS=0
                                    param_STR=''
                                    detected_WHILE=0
                                    line_seg_started=0
                                    line_seg_detected=0
                                    num_line_detected=0
                                    chek_while=0
                        if t_switch.search(i):
                            detected_SWITCH=1
                            print("i see SWITCH ^_^")
                            line_seg_started=elem
                            line_seg_detected=1
                            num_line_detected=line_num
                            continue
                        if t_case.search(i):
                            detected_CASE=1
                            line_seg_started=elem
                            line_seg_detected=1
                            #
                            num_line_detected=line_num
                            param_start=life_Mass[elem-1][0]
                            continue
                        if t_default.search(i):
                            detected_DEFAULT=1
                            line_seg_started=elem
                            line_seg_detected=1
                            num_line_detected=line_num
                            continue

        conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
        cur=conn.cursor()
        cur.execute("select line_seg_id from ccc_line_seg where file_id = %s and name='IF'"%file_id)
        buff_p=cur.fetchall()
        # print(buff_p)
        for i in buff_p:
##            print(file_id)
##            print(i[0])
            cur.execute("select line_seg_id from ccc_line_seg where file_id = '{0}' and parent_func_id='{1}' and (name='ELSE_IF'or name='ELSE')".format(file_id,i[0]))
            buff_ch=cur.fetchall()
            if buff_ch:
                # print(buff_ch)
                cur.execute("UPDATE ccc_Line_Seg SET L_IF_EL=%s where line_seg_id = %s",\
                                            (buff_ch[-1], i[0]))
        conn.commit()
        conn.close()

##        while(L_LS_MASS):#+=-1 или -=1?
##            MASS_CHILD_FOR_IF=[]
##            star_greep=0
##            koll_not_parent=0
##            COLL_EM=len(L_LS_MASS)
##            COLL_EM=COLL_EM-COLL_EM-COLL_EM
##            sprol=-1
##            while(sprol>COLL_EM):
##                if start_greep==1:
##                    if koll_not_parent!=0:
##                        if L_LS_MASS[sprol][0]=='ELSE':
##                            koll_not_parent+=1
##                            sprol+=-1
##                            continue
##                        if L_LS_MASS[sprol][0]=='IF':
##                            koll_not_parent-=1
##                        sprol+=-1
##                        continue
##                    if koll_not_parent==0:
##                        if L_LS_MASS[sprol][0]=='ELSE':
##                            koll_not_parent+=1
##                        if L_LS_MASS[sprol][0]=='ELSE_IF':
##                            MASS_CHILD_FOR_IF.append(L_LS_MASS[sprol][1])
##                            sprol+=-1
##                            continue
##                        if L_LS_MASS[sprol][0]=='IF':
##                            #...
##                            sprol+=-1
##                            continue
##                        sprol+=-1
##                        continue
##                if start_greep==0:
##                    if L_LS_MASS[sprol][0]=='IF':
##                        sprol+=-1
##                        continue
##                    if L_LS_MASS[sprol][0]=='ELSE':
##                        MASS_CHILD_FOR_IF.append(L_LS_MASS[sprol][1])
##                        start_greep=1
##                    if L_LS_MASS[sprol][0]=='ELSE_IF':
##                        MASS_CHILD_FOR_IF.append(L_LS_MASS[sprol][1])
##                        start_greep=1
##                sprol+=-1
##
##
##        for EM ,LLS in enumerate(L_LS_MASS,start=0):#L_LS_MASS.pop(i) <- удаление еллемента



def update_tabel_LS(par,identificatio):
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur=conn.cursor()
    cur.execute("UPDATE ccc_Line_Seg SET have_block_or_not='%s' where line_seg_id = '%s'",(par,identificatio))

##    cur.execute("select * from Line_Seg order by line_seg_id ")
##    buff=cur.fetchall()
##    list=[]
##    for i in buff:
##        list.append(i)

    conn.commit()
    conn.close()

##    return list

##    file_id int,
##    parent_class_id int,
##    parent_func_id int,
##    line_seg_id int,
##    name text,
##    param_L_S text,
##    line_detect int,
##    start_line int,
##    start_pos int,
##    end_line int,
##    end_pos int,
##    have_block_or_not int,
##    line text



##def create_table_ND():#db=DEFAULT_DB):
##    #conn = sqlite3.connect(db)
##    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
##    cur = conn.cursor()
##    cur.execute("select * from func_v where name not in (select name from func_v_test)")# and file_id not in (select file_id from func_v_test)")# and line_detect not in (select line_detect from func_v_test)")
##    buff=cur.fetchall()
##    list=[]
##    for i in buff:
##        list.append(i)
##        print(i)
##    return list
##    conn.close()

if __name__=='__main__':
    create_table_line_seg_PostgreSQL()
    Check_Line_Seg()
##    Mass=create_table_ND()
##    if Mass:
##        for M in Mass:
##            print(M)
##    update_tabel_LS(25,4)
