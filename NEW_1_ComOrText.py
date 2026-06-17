# -*- coding: utf-8 -*-
from _Start_Multy_Java import folder
import psycopg2 #PostgreSQL
import re

def get_file_path(file_id):
    file_id=str(file_id)
    conn = psycopg2.connect(database=folder['DB_NAME'],user=folder['DB_USER'],password=folder['DB_PASS'],host=folder['DB_HOST'],port=folder['DB_PORT'])
    cur = conn.cursor()
    cur.execute("SELECT path FROM ccc_file_list WHERE id_file = %s"%file_id)
    buff=cur.fetchall()
    list=[]
    for i in buff:
        list.append(i[0])
    return list

def QorSlash(Nomer_STR,life,back_comment=0,comment_multy_string = 0,FirstCommentOrStr = 0, back_str = 0, QColl = 0, FirstOneOrTwo = 0):
    #print(life)
    Rezult = []
    comment_str_massiv = []
    comment_many_str_massiv = []
    #
    SlashColl = 0 # колличество /
    SlashPos = 0  # позиция /
    SlashStr = 0  # строка /
##    FirstOneOrTwo = 0 # если первым надена ' = 1 : " = 2
##    FirstCommentOrStr = 0 # если первым найлена '|" = 1 : \\|\* = 2
    QMasOne = [] # массив о '
    QMasTwo = [] # массив о "
##    QColl = 0
    QStrOpen = 0
    QOpenPos = 0
    #
    comment_one_string = 0
    comment_one_string_start_STR=0
    comment_one_string_start_POS=0
    #
    #?>>>>>>comment_multy_string = 0
    comment_multy_string_start_STR=0
    comment_multy_string_start_POS=0
    #
    swap_pos=0
    #
    for elem, i in enumerate(life, start=1):
        if comment_one_string == 0:
            if swap_pos!=0:
                swap_pos-=1
                continue
            if i == '\\' and SlashColl == 0 and FirstCommentOrStr!=2:# and FirstCommentOrStr!=2:
                SlashColl +=1
                SlashStr = Nomer_STR#?
                SlashPos = elem
                continue
            if i == '\\' and SlashColl !=0 and FirstCommentOrStr!=2:# and FirstCommentOrStr!=2:
                if ((elem-SlashPos)==1):# and (Nomer_STR == SlashStr):
                    SlashColl+=1
                    SlashPos = elem
                    if SlashColl ==2:
                        SlashColl=0
                        SlashPos =0
                    continue
                else:
                    SlashColl = 1
                    SlashStr = Nomer_STR#?
                    SlashPos = elem
                    continue
            if i == '/' and FirstCommentOrStr == 0:
                try:
                    if life[elem] == '/':
                        FirstCommentOrStr = 2
                        comment_one_string = 1
                        comment_str_massiv.append(elem)
                        continue
                    if life[elem] == '*':
                        FirstCommentOrStr = 2
                        comment_multy_string = 1
                        comment_multy_string_start_POS=elem
                        comment_many_str_massiv.append((1,Nomer_STR,elem))
                        swap_pos=1
                        continue
                except Exception:
                    pass
            if i =='*' and comment_multy_string == 1:
                try:
                    if life[elem] == '/':
                        try:
                            if life[elem+1] =='/' and life[elem+2] =='*':
                                swap_pos=3
                                continue
                        except Exception:
                            pass
                        swap_pos=1
                        if back_comment==0:
                            comment_many_str_massiv[-1]=(2,Nomer_STR,comment_multy_string_start_POS,elem+1)
                        else:
                            comment_many_str_massiv.append((3,Nomer_STR,elem+1))
                            back_comment=0
                        FirstCommentOrStr = 0
                        comment_multy_string = 0
                        comment_multy_string_start_POS=0
                        continue
                    else:
                        continue
                except Exception:
                    pass
            #@ "<-detect
            if i == '"' and SlashColl == 0 and QColl == 0 and FirstOneOrTwo==0 and FirstCommentOrStr == 0:
                FirstOneOrTwo = 2
                FirstCommentOrStr = 1
                QColl+=1
                QOpenPos=elem
                QMasTwo.append((1,Nomer_STR,elem))
                continue
            if i == '"' and SlashColl != 0 and QColl == 0 and FirstOneOrTwo==0 and FirstCommentOrStr == 0:
                if (elem-SlashPos)==1:
                    SlashColl=0
                    SlashPos =0
                    continue
                FirstOneOrTwo = 2
                FirstCommentOrStr = 1
                QColl+=1
                QOpenPos=elem
                QMasTwo.append((1,Nomer_STR,elem))
                #
                SlashColl=0
                SlashPos =0
                continue
            elif i == '"' and SlashColl == 0 and QColl != 0 and FirstOneOrTwo==2 and FirstCommentOrStr == 1:
                #print('1')
                if back_str==0:
                    QMasTwo[-1]=(2,Nomer_STR,QOpenPos,elem)
                else:
                    QMasTwo.append((3,Nomer_STR,elem))
                    back_str=0
                FirstOneOrTwo = 0
                FirstCommentOrStr = 0
                QColl=0
                QOpenPos=0
                continue
            elif i == '"' and SlashColl != 0 and QColl != 0 and FirstOneOrTwo==2 and FirstCommentOrStr == 1:
                #print(SlashPos)
                #print(elem)
                if (elem-SlashPos)==1:
                    SlashColl=0
                    SlashPos =0
                    continue
                if back_str==0:
                    QMasTwo[-1]=(2,Nomer_STR,QOpenPos,elem)
                else:
                    QMasTwo.append((3,Nomer_STR,elem))
                    back_str=0
                FirstOneOrTwo = 0
                FirstCommentOrStr = 0
                QColl=0
                QOpenPos=0
                #
                SlashColl=0
                SlashPos =0
                continue
            #@ '<-detect
            if i == "'" and SlashColl == 0 and QColl == 0 and FirstOneOrTwo==0 and FirstCommentOrStr==0:
                FirstOneOrTwo = 1
                FirstCommentOrStr = 1
                QColl+=1
                QOpenPos=elem
                QMasOne.append((1,Nomer_STR,elem))
                continue
            elif i == "'" and SlashColl != 0 and QColl == 0 and FirstOneOrTwo==0 and FirstCommentOrStr==0:
                if (elem-SlashPos)==1:
                    SlashColl=0
                    SlashPos =0
                    continue
                FirstOneOrTwo = 1
                FirstCommentOrStr = 1
                QColl+=1
                QOpenPos=elem
                QMasOne.append((1,Nomer_STR,elem))
                #
                SlashColl=0
                SlashPos =0
                continue
            elif i == "'" and SlashColl == 0 and QColl != 0 and FirstOneOrTwo==1 and FirstCommentOrStr==1:
                if back_str==0:
                    QMasOne[-1]=(2,Nomer_STR,QOpenPos,elem)
                else:
                    QMasOne.append((3,Nomer_STR,elem))
                    back_str=0
                FirstOneOrTwo = 0
                FirstCommentOrStr = 0
                QColl=0
                QOpenPos=0
                continue
            elif i == "'" and SlashColl != 0 and QColl != 0 and FirstOneOrTwo==1 and FirstCommentOrStr==1:
                if (elem-SlashPos)==1:
                    SlashColl=0
                    SlashPos =0
                    continue
                if back_str==0:
                    QMasOne[-1]=(2,Nomer_STR,QOpenPos,elem)
                else:
                    QMasOne.append((3,Nomer_STR,elem))
                    back_str=0
                FirstOneOrTwo = 0
                FirstCommentOrStr = 0
                QColl=0
                QOpenPos=0
                #
                SlashColl=0
                SlashPos =0
                continue

    Rezult.append((QMasTwo,QMasOne,comment_str_massiv,comment_many_str_massiv))
    return Rezult

def test():#QorSlash(Nomer_STR,life,back_comment=0,comment_multy_string = 0,FirstCommentOrStr = 0, back_str = 0, QColl = 0, FirstOneOrTwo = 0):
    line_num=587
    life = ['*','/','default',':','false']
##    life = ['public', '/', '*', '/', 'Text1', '*', '/', 'class', '/', '*', 'Text2', ',', 'Text3', '*', '/', 'Text2', ',', 'Text3', 'AnotherBarActivity', 'extends', 'DemoBase', '"', 'implements', '"', '\'','\\','\\','\\','OnSeekBarChangeListener','OnSeekBarChangeListener','OnSeekBarChangeListener', '\'', 'OnSeekBarChangeListener', '/', '/', '{']
    Mass = QorSlash(line_num,life,back_comment=1,comment_multy_string=1,FirstCommentOrStr=2)
    #print("Massiv \" = {}".format(Mass[0][0]))
    #print("Massiv \' = {}".format(Mass[0][1]))
    #print("CommentOneM = {}".format(Mass[0][2]))
    #print("CommentMannyM = {}".format(Mass[0][3]))
##    mar=Mass[0][3]
##    #print(mar[0][0])
##if __name__=='__main__':
##    test()
