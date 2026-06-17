# -*- coding: utf-8 -*-
import psycopg2 #PostgreSQL
from _Start_Multy_Java import folder
from find_files import get_file_path as get_list
import re
from random import randint
from pasteSensor import getData, pasteSensFunc

def get_func_info_for_file_id(file_id):
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select func_id, name, start_line, start_pos, parent_class_id from ccc_func_v where file_id = %s and have_block_or_not=1"%file_id)
    buff=cur.fetchall()
    conn.close()
    list=[]
    for line in buff:
        list.append((line[0], line[1], line[2], line[3], line[4]))
    return list

def get_LS_info_for_file_id(file_id):#,str_num):
    list=[]
    buff=[]
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not from ccc_Line_seg where file_id = %s order by start_line asc, start_pos desc "%file_id)
##    cur.execute("select line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not from line_seg where file_id = %s order by line_seg_id asc"%file_id)

##    cur.execute("select line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not from line_seg where file_id = (%s) and start_line=(%s) order by start_line asc, start_pos desc "(file_id,str_num))
##    cur.execute("select line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not from line_seg where file_id = %s order by start_line asc "%file_id)

    buff=cur.fetchall()
    conn.close()
    for line in buff:
##        if buff:
##            buff.append((line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7]))
##        else:
##            biff.append((line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7]))
##            continue
##        if line[2]==71 or line[2]==72 or line[2]==73:
##            print(line)
        list.append((line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7]))

    return list


def get_LS_info_for_line(file_id, str_num):#,str_num):
    list=[]
    buff=[]
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("select line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not from ccc_Line_seg where file_id = '{0}' and (start_line = '{1}' or end_line = '{2}') order by line_seg_id asc".format(file_id,str_num,str_num))
    buff=cur.fetchall()
    conn.close()
    for line in buff:
        list.append((line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7]))
    return list

def sloy(list_f = get_list()):
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    t_else=re.compile('else')
    t_if=re.compile('if')
    t_for=re.compile('for')
    t_DO=re.compile('do')
    t_while=re.compile('while')
    t_switch=re.compile('switch')
    t_case=re.compile('case')
    t_default=re.compile('default')

    DEPTH = int(folder['CHECK_DEPTH'])
    # include=' import org.asis.sensor.*; \n'
    # package_str = '^\s*(package)\s+.*\s*;\s*'
    for id_file, path in enumerate(list_f, start=1):
        # if id_file != 248:
        #     continue
        # if id_file>1:
        #     break
        if DEPTH > 2:
            pasteSensFunc([id_file, path], getData(id_file, conn))
            continue
        print(id_file)
        FileNew =[]
        conc_include =''
        
        file = open(path[0], encoding=path[1])
        for strings in file:
            FileNew.append(strings)
        file.close()

        if 'УЦП-ОА' in path[0] or 'самотестирование' in path[0]:
            rav = 'SendMSG({0});'
        elif 'УЦП-П' in path[0]:
            rav = 'Time_a({0});'
        else:
            rav = 'SENSOR({0});'
        # for coll_strings, string in enumerate(FileNew, start=1):
        #     print(string)
        #     # rez=re.search(package_str, string)
        #     if rez!=None:
        #         conc_include=string.rstrip("\n")
        #         print(conc_include)
        #         conc_include=conc_include.rstrip("\r")
        #         print(conc_include)
        #         conc_include+=include
        #         print(conc_include)
        #         FileNew[coll_strings]=conc_include
        #         with open(path,'w') as RedFile:
        #             RedFile.writelines(FileNew)
        #         RedFile.close()
        #         break
        # if DEPTH == 3:
        #     FuncMassForFile=get_func_info_for_file_id(id_file)
        # if DEPTH == 2:
        #     FuncMassForFile=get_func_info_for_file_id(id_file)
##            LSMassForFile=get_LS_info_for_file_id(id_file)

#         Last_char=0
#         for FFFID, FMFF in enumerate(FuncMassForFile, start=1):
#             go_Next=0
# ##            conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
#             cur = conn.cursor()
#             cur.execute("select name_class from classes_v where class_id = '{0}'".format(FMFF[4]))
#             buff=cur.fetchall()
# ##            for chart in FMFF[1]:
# ##                print('{} ,'.format(ord(chart)))
#             for Cl in buff:
#                 print(Cl[0])
#                 print(FMFF[1])
#                 if Cl[0]==FMFF[1]:
#                     print("GO_NEXT")
#                     go_Next=1
#                 else:
#                     print("NORM?")
# ##            conn.close()
#             if go_Next==1:
#                 continue
#             ELEMENT_ADD = 0
#             ADD_end_simbol = 0
#
#             ELEMENT = ' JSensor.writeToDB({},"{}",{});'.format(FMFF[0],FMFF[1],0)
#
#             strr=''
#             strr_end=''
#             SerchMass=[]
#             HBON_Serch=69
#             WHILE_Func_ID=0
#
#             for coll_string, string in enumerate(FileNew, start=1):
#                 if coll_string == FMFF[2]:
#                     for pos_in_line, char in enumerate(string, start=1):
#                         if pos_in_line == FMFF[3] and ELEMENT_ADD!=1:
#                             strr+=char
#                             strr+=ELEMENT
#                             ELEMENT_ADD=1
#                         elif pos_in_line != FMFF[3]:
#                             strr+=char
#                         FileNew[coll_string-1] = strr
#                     strr==''
#             continue


        Last_char=0
        last_HBON=-69
        last_NLS=''
        COLL_HBON=0
        COLL_LIFEL=0
        M_LIFEL=[]
        for coll_string, string in enumerate(FileNew, start=1):
##            if coll_string==102 or coll_string==103 or coll_string==99:
##                print(Last_char)
##                print(last_HBON)
##                print(COLL_HBON)
            index_move=0
            index_move_chek=0
            index_Last_ID=0
            LSMassForFile =[]#get_LS_info_for_line(id_file, coll_string)
            cur = conn.cursor()
            cur.execute("select line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not, l_if_el from ccc_line_seg where file_id = '{0}' and (start_line = '{1}' or end_line = '{1}') order by line_seg_id asc".format(path[2],coll_string))
            buff=cur.fetchall()
            for line in buff:
                LSMassForFile.append((line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8]))
        ##            if coll_string >50 and coll_string < 58:
        ##                print(LSMassForFile)
            N = len(LSMassForFile)
            a = []
            # print(LSMassForFile)
            i = 0
            while i < N - 1:
                j = 0
                while j < N - 1 - i:
                    if LSMassForFile[j][2]==coll_string and LSMassForFile[j+1][2]==coll_string:
                        if LSMassForFile[j][3] > LSMassForFile[j+1][3]:
                            LSMassForFile[j], LSMassForFile[j+1] = LSMassForFile[j+1], LSMassForFile[j]
                    if LSMassForFile[j][2]==coll_string and LSMassForFile[j+1][2]!=coll_string and LSMassForFile[j+1][4]==coll_string:
                        if LSMassForFile[j][3] > LSMassForFile[j+1][5]:
                            LSMassForFile[j], LSMassForFile[j+1] = LSMassForFile[j+1], LSMassForFile[j]
                    if LSMassForFile[j][2]!=coll_string and LSMassForFile[j][4]==coll_string and LSMassForFile[j+1][2]==coll_string:
                        if LSMassForFile[j][5] > LSMassForFile[j+1][3]:
                            LSMassForFile[j], LSMassForFile[j+1] = LSMassForFile[j+1], LSMassForFile[j]
                    if LSMassForFile[j][2]!=coll_string and LSMassForFile[j+1][2]!=coll_string and LSMassForFile[j][4]==coll_string and LSMassForFile[j+1][4]==coll_string:
                        if LSMassForFile[j][5] > LSMassForFile[j+1][5]:
                            LSMassForFile[j], LSMassForFile[j+1] = LSMassForFile[j+1], LSMassForFile[j]
                    j += 1
                i += 1
            # print(LSMassForFile)

            for LSFFID, LSMFF in enumerate(LSMassForFile, start=1):#line_seg_id, name, start_line, start_pos, end_line, end_pos, parent_func_id, have_block_or_not
                if LSMFF:
                    print(LSMFF)
##                if LSMFF[1]=='SWITCH':
##                    continue
##                if LSMFF[1]=='WHILE' and LSMFF[7]==-5:
##                    print(LSMFF)
                # ELEMENT = 'SendMSG({0});'
                ELEMENT = rav.format(LSMFF[0])
                print(ELEMENT)
                ELEM_LN=len(ELEMENT)
                if LSMFF[0]== 1:
                    print(index_Last_ID)
                strr=''
                strr_end=''
                ELEMENT_ADD = 0
                ADD_end_simbol = 0
                S_E_OR_ALL=0
                if LSMFF[1]=='SWITCH' and LSMFF[4]==coll_string:
                    last_HBON=LSMFF[7]
                    last_NLS=LSMFF[1]
                    if index_Last_ID==0:
                        for pos_in_line, char in enumerate(string, start=1):
                            if pos_in_line==LSMFF[5]+1 and ADD_end_simbol!=1:
                                strr+=char
                                while Last_char-COLL_HBON-COLL_LIFEL>0:
                                    strr+='}'
                                    index_move+=1
                                    index_Last_ID=LSMFF[0]
                                    Last_char-=1
                                if M_LIFEL and(COLL_LIFEL!=0):
                                    if M_LIFEL[-1]==LSMFF[0]:
                                        strr+='}'
                                        index_move+=1
                                        COLL_LIFEL-=1
                                        Last_char-=1
                                        M_LIFEL.pop(-1)
                                ADD_end_simpol=1
                            elif pos_in_line!=LSMFF[5]+1:
                                strr+=char
                            FileNew[coll_string-1]=strr
                        index_move_chek=index_move
                    elif index_Last_ID!=0:
                        for pos_in_line, char in enumerate(string, start=1):
                            if pos_in_line==LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                strr+=char
                                while Last_char-COLL_HBON-COLL_LIFEL>0:
                                    strr+='}'
                                    index_move+=1
                                    index_Last_ID=LSMFF[0]
                                    Last_char-=1
                                if M_LIFEL and(COLL_LIFEL!=0):
                                    if M_LIFEL[-1]==LSMFF[0]:
                                        strr+='}'
                                        index_move+=1
                                        COLL_LIFEL-=1
                                        Last_char-=1
                                        M_LIFEL.pop(-1)
                                ADD_end_simbol=1
                            elif pos_in_line!=LSMFF[5]+index_move_chek+1:
                                strr+=char
                            FileNew[coll_string-1]=strr
                        index_move_chek=index_move
                    string=FileNew[coll_string-1]
                    continue
                elif LSMFF[1]=='SWITCH':
                    continue
                if LSMFF[2]==coll_string and (LSMFF[1]=='CASE' or LSMFF[1]=='DEFAULT'):
                    last_HBON=LSMFF[7]
                    last_NLS=LSMFF[1]
                    if index_Last_ID==0:
                        for pos_in_line, char in enumerate(string, start=1):
                            if pos_in_line == LSMFF[3]+1 and ELEMENT_ADD!=1:
                                strr+=char
                                strr+=ELEMENT
                                index_move+=ELEM_LN
                                index_Last_ID=LSMFF[0]#
                                ELEMENT_ADD=1
                            elif pos_in_line != LSMFF[3]+1:
                                strr+=char
                            FileNew[coll_string-1] = strr
                        index_move_chek=index_move
                    elif index_Last_ID!=0:
                        for pos_in_line, char in enumerate(string, start=1):
                            if pos_in_line == LSMFF[3]+index_move_chek+1 and ELEMENT_ADD!=1:
                                strr+=char
                                strr+=ELEMENT
                                index_move+=ELEM_LN
                                index_Last_ID=LSMFF[0]#
                                ELEMENT_ADD=1
                            elif pos_in_line != LSMFF[3]+index_move_chek+1:
                                strr+=char
                            FileNew[coll_string-1] = strr
                        index_move_chek=index_move
                    string=FileNew[coll_string-1]
                    continue
                if LSMFF[7]==-1 and LSMFF[4]==coll_string:
                    last_HBON=LSMFF[7]
                    last_NLS=LSMFF[1]
##                    if COLL_HBON==0:
##                        continue
                    if index_Last_ID==0:
                        for pos_in_line, char in enumerate(string, start=1):
                            if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                strr+=char
                                if COLL_HBON!=0:
                                    strr+='}'
                                    index_move+=1
                                    index_Last_ID=LSMFF[0]
                                    COLL_HBON-=1
                                    Last_char-=1
                                ADD_end_simbol=1
                            elif pos_in_line != LSMFF[5]+1:
                                strr+=char
                            FileNew[coll_string-1] = strr
                        index_move_chek=index_move
                    elif index_Last_ID!=0:
                        for pos_in_line, char in enumerate(string, start=1):
                            if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                strr+=char
                                if COLL_HBON!=0:
                                    strr+='}'
                                    index_move+=1
                                    index_Last_ID=LSMFF[0]
                                    COLL_HBON-=1
                                    Last_char-=1
                                ADD_end_simbol=1
                            elif pos_in_line != LSMFF[5]+index_move_chek+1:
                                strr+=char
                            FileNew[coll_string-1] = strr
                        index_move_chek=index_move
                    string=FileNew[coll_string-1]
                    continue
                if LSMFF[1]=='WHILE' and LSMFF[7]==-5:
                    last_HBON=0
                    last_NLS=LSMFF[1]
                    if LSMFF[2]==coll_string and LSMFF[4]==coll_string:
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[3]+1 and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+='{'
                                    index_move+=1
                                    strr+=ELEMENT
                                    index_Last_ID=LSMFF[0]
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                    print(LSMFF)
                                    strr+='}'
                                    strr+=char
                                    index_move+=1#add
                                    index_Last_ID=index_Last_ID=LSMFF[0]#поменял 1 на -> index_Last_ID=LSMFF[0]
                                    while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    ADD_end_simbol=1
                                elif pos_in_line != LSMFF[5]+1 and pos_in_line != LSMFF[3]+1:
                                    strr+=char
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[3]+index_move_chek+1 and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+='{'
                                    index_move+=1
                                    strr+=ELEMENT
                                    index_Last_ID=LSMFF[0]
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                    print(LSMFF)
                                    strr+='}'
                                    strr+=char
                                    index_move+=1#add
                                    index_Last_ID=index_Last_ID=LSMFF[0]#povtoril up block
                                    while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    ADD_end_simbol=1
                                if pos_in_line != LSMFF[5]+index_move_chek+1 and pos_in_line != LSMFF[3]+index_move_chek+1:
                                    strr+=char
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    if LSMFF[2]!=coll_string and LSMFF[4]==coll_string:
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                    print(LSMFF)
                                    strr+='}'
                                    strr+=char
                                    index_move+=1#add
                                    index_Last_ID=index_Last_ID=LSMFF[0]#поменял 1 на -> index_Last_ID=LSMFF[0]
                                    while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    ADD_end_simbol=1
                                elif pos_in_line != LSMFF[5]+1:
                                    strr+=char
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                    print(LSMFF)
                                    strr+='}'
                                    strr+=char
                                    index_move+=1#add
                                    index_Last_ID=index_Last_ID=LSMFF[0]#povtoril up block
                                    while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    ADD_end_simbol=1
                                elif pos_in_line != LSMFF[5]+index_move_chek+1:
                                    strr+=char
##                                    index_move_chek=index_move
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    if LSMFF[2]==coll_string and LSMFF[4]!=coll_string:
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[3]+1 and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+='{'
                                    index_move+=1
                                    strr+=ELEMENT
                                    index_Last_ID=LSMFF[0]
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                elif pos_in_line != LSMFF[3]+1:
                                    strr+=char
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[3]+index_move_chek+1 and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+='{'
                                    index_move+=1
                                    strr+=ELEMENT
                                    index_Last_ID=LSMFF[0]
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                elif pos_in_line != LSMFF[3]+index_move_chek+1:
                                    strr+=char
##                                    index_move_chek=index_move
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                if LSMFF[7]==2:
##                    if LSMFF[1]=='FOR' and coll_string==86:
##                        print("IT's this FOOOR")
##                        print(string)
##                        print(Last_char)
##                    if LSMFF[1]=='ELSE':#LSMFF[1]=='DO'or
##                        continue
##                    last_HBON=LSMFF[7]
##                    last_NLS=LSMFF[1]
                    if LSMFF[2]!=coll_string and LSMFF[4]==coll_string and LSMFF[1]=='DO':
##                        if last_HBON==2:
##                            COLL_HBON+=1
                        last_HBON=LSMFF[7]
                        last_NLS=LSMFF[1]
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[5]+1 and ADD_end_simbol!=1:
                                    strr+='}'
                                    index_move+=1
                                    strr+=char
                                    index_Last_ID=LSMFF[0]
                                    ADD_end_simbol=1
                                elif pos_in_line!=LSMFF[5]+1:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                    strr+='}'
                                    index_move+=1
                                    strr+=char
                                    index_Last_ID=LSMFF[0]
                                    ADD_end_simbol=1
                                elif pos_in_line!=LSMFF[5]+index_move_chek+1:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    if LSMFF[2]==coll_string and LSMFF[4]==coll_string and LSMFF[1]=='DO':
                        if last_HBON==2 and last_NLS!='DO':
                            COLL_HBON+=1
                        last_HBON=LSMFF[7]
                        last_NLS=LSMFF[1]
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[3] and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+='{'
                                    index_move+=1
                                    strr+=ELEMENT
                                    index_Last_ID=LSMFF[0]
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                    strr+='}'
                                    index_move+=1
##                                    Last_char-=1#??
##                                    COLL_HBON-=1#??
                                    strr+=char
                                    index_Last_ID=LSMFF[0]
                                    ADD_end_simbol=1
                                    if M_LIFEL and (COLL_LIFEL!=0):
                                        if M_LIFEL[-1]==LSMFF[0]:
                                            strr+='}'
                                            index_move+=1
                                            COLL_LIFEL-=1
                                            Last_char-=1
                                            M_LIFEL.pop(-1)
                                elif pos_in_line != LSMFF[3] and pos_in_line != LSMFF[5]+1:
                                    strr+=char
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line == LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+='{'
                                    index_move+=1
##                                    Last_char-=1#??
##                                    COLL_HBON-=1#??
                                    strr+=ELEMENT
                                    index_Last_ID=LSMFF[0]
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                    strr+='}'
                                    index_move+=1
                                    strr+=char
                                    index_Last_ID=LSMFF[0]
                                    ADD_end_simbol=1
                                    if M_LIFEL and (COLL_LIFEL!=0):
                                        if M_LIFEL[-1]==LSMFF[0]:
                                            strr+='}'
                                            index_move+=1
                                            COLL_LIFEL-=1
                                            Last_char-=1
                                            M_LIFEL.pop(-1)
                                elif pos_in_line != LSMFF[3]+index_move_chek and pos_in_line != LSMFF[5]+index_move_chek+1:
                                    strr+=char
    ##                                    index_move_chek=index_move
                                FileNew[coll_string-1] = strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    if LSMFF[2]==coll_string:# and LSMFF[4]==coll_string:
                        if last_HBON==2 and LSMFF[1]=='DO' and last_NLS!='DO':
                            COLL_HBON+=1
                        if last_HBON==2 and LSMFF[1]=='IF' and LSMFF[8]!=0: #!
                            M_LIFEL.append(LSMFF[8])                        #!
                            COLL_LIFEL+=1                                   #!
                        last_HBON=LSMFF[7]
                        last_NLS=LSMFF[1]
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='DO':
                                    if pos_in_line==LSMFF[3] and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
##                                        Last_char+=1#?
                                        index_Last_ID=LSMFF[0]
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                                elif LSMFF[1]=='ELSE':
                                    if pos_in_line==LSMFF[3]and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        Last_char+=1
                                        index_move+=ELEM_LN
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                                else:
                                    if pos_in_line==LSMFF[3]+1 and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        Last_char+=1
                                        index_Last_ID=LSMFF[0]
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='DO':
                                    if pos_in_line == LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
##                                        Last_char+=1
                                        index_Last_ID=LSMFF[0]
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        ELEMENT_ADD=1
                                    elif pos_in_line != LSMFF[3]+index_move_chek:
                                        strr+=char
                                    FileNew[coll_string-1] = strr
                                else:
                                    if pos_in_line==LSMFF[3]+index_move_chek+1 and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        Last_char+=1
                                        index_Last_ID=LSMFF[0]
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]+index_move_chek+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                if LSMFF[7]==1:
                    if last_HBON==2 and LSMFF[1]=='DO' and last_NLS!='DO':
                        COLL_HBON+=1
                    if last_HBON==2 and LSMFF[1]=='IF' and LSMFF[8]!=0: #!
                        M_LIFEL.append(LSMFF[8])                        #!
                        COLL_LIFEL+=1                                   #!
                    last_HBON=LSMFF[7]
                    last_NLS=LSMFF[1]
                    if LSMFF[2]==coll_string and LSMFF[4]==coll_string:#??> and LSMFF[4]==coll_string:
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[3] and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+=ELEMENT
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                    index_Last_ID=LSMFF[0]
                                if pos_in_line==LSMFF[5]and ADD_end_simbol!=1:
                                    strr+=char
                                    while Last_char-COLL_HBON-COLL_LIFEL>0:
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    if M_LIFEL and (COLL_LIFEL!=0):
                                        if M_LIFEL[-1]==LSMFF[0]:
                                            strr+='}'
                                            index_move+=1
                                            COLL_LIFEL-=1
                                            Last_char-=1
                                            M_LIFEL.pop(-1)
                                    ADD_end_simbol=1
                                elif pos_in_line!=LSMFF[3]and pos_in_line!=LSMFF[5]:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+=ELEMENT
                                    index_move+=ELEM_LN
                                    ELEMENT_ADD=1
                                    index_Last_ID=LSMFF[0]
                                if pos_in_line==LSMFF[5]+index_move_chek and ADD_end_simbol!=1:
                                    strr+=char
                                    while Last_char-COLL_HBON-COLL_LIFEL>0:
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    if M_LIFEL and (COLL_LIFEL!=0):
                                        if M_LIFEL[-1]==LSMFF[0]:
                                            strr+='}'
                                            index_move+=1
                                            COLL_LIFEL-=1
                                            Last_char-=1
                                            M_LIFEL.pop(-1)
                                    ADD_end_simbol=1
                                elif pos_in_line!=LSMFF[3]+index_move_chek and pos_in_line!=LSMFF[5]+index_move_chek:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    if LSMFF[2]==coll_string and LSMFF[4]!=coll_string:
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[3]and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+=ELEMENT
                                    index_move+=ELEM_LN
                                    index_Last_ID=LSMFF[0]
                                    ELEMENT_ADD=1
                                elif pos_in_line!=LSMFF[3]:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                    strr+=char
                                    strr+=ELEMENT
                                    index_move+=ELEM_LN
                                    index_Last_ID=LSMFF[0]
                                    ELEMENT_ADD=1
                                elif pos_in_line!=LSMFF[3]+index_move_chek:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    if LSMFF[2]!=coll_string and LSMFF[4]==coll_string:
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[5]+1 and ADD_end_simbol!=1:
                                    strr+=char
                                    while Last_char-COLL_HBON-COLL_LIFEL>0:
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    if M_LIFEL and(COLL_LIFEL!=0):
                                        if M_LIFEL[-1]==LSMFF[0]:
                                            strr+='}'
                                            index_move+=1
                                            COLL_LIFEL-=1
                                            Last_char-=1
                                            M_LIFEL.pop(-1)
                                    ADD_end_simpol=1
                                elif pos_in_line!=LSMFF[5]+1:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if pos_in_line==LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                    strr+=char
                                    while Last_char-COLL_HBON-COLL_LIFEL>0:
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        Last_char-=1
                                    if M_LIFEL and(COLL_LIFEL!=0):
                                        if M_LIFEL[-1]==LSMFF[0]:
                                            strr+='}'
                                            index_move+=1
                                            COLL_LIFEL-=1
                                            Last_char-=1
                                            M_LIFEL.pop(-1)
                                    ADD_end_simbol=1
                                elif pos_in_line!=LSMFF[5]+index_move_chek+1:
                                    strr+=char
                                FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                if LSMFF[7]==0:
                    if last_HBON==2 and LSMFF[1]=='DO' and last_NLS!='DO':
                        COLL_HBON+=1
                    if last_HBON==2 and LSMFF[1]=='IF' and LSMFF[8]!=0: #!
                        M_LIFEL.append(LSMFF[8])                        #!
                        COLL_LIFEL+=1                                   #!
                    last_HBON=LSMFF[7]
                    last_NLS=LSMFF[1]
                    if LSMFF[2]==coll_string and LSMFF[4]==coll_string:
                        S_E_OR_ALL=3
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='ELSE':
                                    if pos_in_line==LSMFF[3]and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    if pos_in_line==LSMFF[5]+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and(COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line != LSMFF[3] and pos_in_line != LSMFF[5]+1:
                                        strr+=char
                                    FileNew[coll_string-1] = strr
                                elif LSMFF[1]=='DO':
                                    if pos_in_line == LSMFF[3] and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                        strr+='}'
                                        index_move+=1
                                        strr+=char
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        ADD_end_simbol=1
                                    elif pos_in_line != LSMFF[3] and pos_in_line != LSMFF[5]+1:
                                        strr+=char
                                    FileNew[coll_string-1] = strr
                                else:
                                    if pos_in_line==LSMFF[3]+1 and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    if pos_in_line==LSMFF[5]+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0:
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and (COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line!=LSMFF[3]+1and pos_in_line!=LSMFF[5]+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='ELSE':
                                    if pos_in_line == LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and (COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line != LSMFF[3]+index_move_chek and pos_in_line != LSMFF[5]+index_move_chek+1:
                                        strr+=char
##                                    index_move_chek=index_move
                                    FileNew[coll_string-1] = strr
                                elif LSMFF[1]=='DO':
                                    if pos_in_line == LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                        strr+='}'
                                        index_move+=1
                                        strr+=char
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        ADD_end_simbol=1
                                    elif pos_in_line != LSMFF[3]+index_move_chek and pos_in_line != LSMFF[5]+index_move_chek+1:
                                        strr+=char
##                                    index_move_chek=index_move
                                    FileNew[coll_string-1] = strr
                                else:
                                    if pos_in_line==LSMFF[3]+index_move_chek+1 and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    if pos_in_line==LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0:
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and(COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line!=LSMFF[3]+index_move_chek+1 and pos_in_line!=LSMFF[5]+index_move_chek+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    elif LSMFF[2]==coll_string and LSMFF[4]!=coll_string:
                        S_E_OR_ALL=1
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='ELSE' or LSMFF[1]=='DO':
                                    if pos_in_line==LSMFF[3] and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                                else:
                                    if pos_in_line==LSMFF[3]+1 and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='ELSE' or LSMFF[1]=='DO':
                                    if pos_in_line == LSMFF[3]+index_move_chek and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Last_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    elif pos_in_line != LSMFF[3]+index_move_chek:
                                        strr+=char
                                    FileNew[coll_string-1] = strr
                                else:
                                    if pos_in_line==LSMFF[3]+index_move_chek+1 and ELEMENT_ADD!=1:
                                        strr+=char
                                        strr+='{'
                                        index_move+=1
                                        strr+=ELEMENT
                                        index_move+=ELEM_LN
                                        index_Lat_ID=LSMFF[0]
                                        ELEMENT_ADD=1
                                    elif pos_in_line!=LSMFF[3]+index_move_chek+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue
                    elif LSMFF[2]!=coll_string and LSMFF[4]==coll_string:
                        S_E_OR_ALL=2
                        if index_Last_ID==0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='ELSE':
                                    if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and (COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    if pos_in_line != LSMFF[5]+1:
                                        strr+=char
                                    FileNew[coll_string-1] = strr
                                elif LSMFF[1]=='DO':
                                    if pos_in_line == LSMFF[5]+1 and ADD_end_simbol!=1:
                                        strr+='}'
                                        index_move+=1
                                        strr+=char
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        ADD_end_simbol=1
                                    if pos_in_line != LSMFF[5]+1:
                                        strr+=char
                                    FileNew[coll_string-1] = strr
                                else:
                                    if pos_in_line==LSMFF[5]+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0:
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and(COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line!=LSMFF[5]+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        elif index_Last_ID!=0:
                            for pos_in_line, char in enumerate(string, start=1):
                                if LSMFF[1]=='ELSE':
                                    if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and (COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line != LSMFF[5]+index_move_chek+1:
                                        strr+=char
##                                    index_move_chek=index_move
                                    FileNew[coll_string-1] = strr
                                elif LSMFF[1]=='DO':
                                    if pos_in_line == LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                        strr+='}'
                                        strr+=char
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0: #@@@ #COLL_LIFEL!
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        ADD_end_simbol=1
                                    elif pos_in_line != LSMFF[5]+index_move_chek+1:
                                        strr+=char
##                                    index_move_chek=index_move
                                    FileNew[coll_string-1] = strr
                                else:
                                    if pos_in_line==LSMFF[5]+index_move_chek+1 and ADD_end_simbol!=1:
                                        strr+=char
                                        strr+='}'
                                        index_move+=1
                                        index_Last_ID=LSMFF[0]
                                        while Last_char-COLL_HBON-COLL_LIFEL>0:
                                            strr+='}'
                                            index_move+=1
                                            Last_char-=1
                                        if M_LIFEL and(COLL_LIFEL!=0):
                                            if M_LIFEL[-1]==LSMFF[0]:
                                                strr+='}'
                                                index_move+=1
                                                COLL_LIFEL-=1
                                                Last_char-=1
                                                M_LIFEL.pop(-1)
                                        ADD_end_simbol=1
                                    elif pos_in_line!=LSMFF[5]+index_move_chek+1:
                                        strr+=char
                                    FileNew[coll_string-1]=strr
                            index_move_chek=index_move
                        string=FileNew[coll_string-1]
                        continue

        print('Paste in\t{0}: {1}'.format(id_file, path))
        with open(path[0], 'w') as RedFile:
            RedFile.writelines(FileNew)
        pasteSensFunc([id_file, path], getData(id_file, conn))
    conn.close()
if __name__=='__main__':
     sloy()
