# -*- coding: utf-8 -*-
from NEW_1_ComOrText import QorSlash
from find_files import get_file_path as get_list
import re

##def Char_Pos_in_block_or_not(I = 0, HaveOrNotToHaveStrElement = 0, QMasSimbolStrInThisStr = [], have_MC = 0, LHMCBlock = [], line_have_one_str_comment = 0, line_one_str_comment_pos_start = 0):
##    add_IT = 1
##    Add_Y = 1
##    AD_IT = 1
##    if HaveOrNotToHaveStrElement == 1:
##        index_pos=1
##        for index, QMSSITS in enumerate (QMasSimbolStrInThisStr, start=0):
##            if index_pos == 1:
##                if QMSSITS == 1:
##                    if I > QMasSimbolStrInThisStr[index+index_pos][0] and I < QMasSimbolStrInThisStr[index+index_pos][1] :
##                        add_IT = 0
##                if QMSSITS == 2:
##                    if I > QMasSimbolStrInThisStr[index+index_pos][0]:
##                        add_IT = 0
##                if QMSSITS == 3:
##                    if I < QMasSimbolStrInThisStr[index+index_pos][1]:
##                        add_IT = 0
##            if index_pos == 2:
##                index_pos = 1
##                continue
##            else:
##                index_pos += 1
##    if have_MC == 1:
##        index_pos = 1
##        for index, MCElement in enumerate (LHMCBlock, start=0):
##            if index_pos == 1:
##                if MCElement == 1:
##                    if I > LHMCBlock[index+index_pos][0] and I < LHMCBlock[index+index_pos][1]:
##                        Add_Y = 0
##                if MCElement == 2:
##                    if I > LHMCBlock[index+index_pos]:
##                        Add_Y = 0
##                if MCElement == 3:
##                    if I < LHMCBlock[index+index_pos]:
##                        Add_Y = 0
##            if index_pos == 2:
##                index_pos = 1
##                continue
##            else:
##                index_pos+=1
##    if line_have_one_str_comment == 1:
##        if I > line_one_str_comment_pos_start:
##            AD_IT = 0
##    if add_IT != 0 and Add_Y != 0 and AD_IT !=0:
##        return(1)
##    else:
##        return(0)


def borders(num_str, data, name_F , last_chek_pos = 0, comment_multy_string = 0, FirstOneOrTwo = 0):
        Switch_Start_elem=0
        Switch_End_elem=0
        last_simbol=0#-> ;
        ITs_not_class=0
        start_char = '{'
        start_char_in_line =0
        start_pos_char_in_line = 0
        start = 0
        end_char = '}'
        end_char_in_line =0
        end_pos_char_in_line = 0
        end = 0
        for line_num, line in enumerate(data.readlines(), start=1): #1 строка будет определена под цифрой 1, 2 под 2 ... и т.д. (Это важно запомнить!)
##                    #print("HEY")
            if line_num < num_str:
                continue
            #Parser Comment Open
            go_next_str = 0
            life = re.findall('[A-Za-z_0-9]+|[^A-Za-z_0-9]', line)
##                    if line_num >= num_str and line_num <=num_str+2:
##                        #print(life)
            life_Mass = [((a.start(), a.end())) for a in list(re.finditer('[A-Za-z_0-9]+|[^A-Za-z_0-9]', line))]
##                    #print(life)
##                    #print(life_Mass)
            #
            if comment_multy_string == 1:
                GlobalFileSegmentMass = QorSlash(line_num,life,back_comment=1,comment_multy_string=1,FirstCommentOrStr=2)
            elif FirstOneOrTwo == 1:
                GlobalFileSegmentMass = QorSlash(line_num,life,back_comment=0,comment_multy_string = 0,FirstCommentOrStr = 1, back_str = 1, QColl = 1, FirstOneOrTwo = 1)
            elif FirstOneOrTwo == 2:
                GlobalFileSegmentMass = QorSlash(line_num,life,back_comment=0,comment_multy_string = 0,FirstCommentOrStr = 1, back_str = 1, QColl = 1, FirstOneOrTwo = 2)
            else:GlobalFileSegmentMass = QorSlash(line_num,life)
            #print(line_num)
            #print(GlobalFileSegmentMass)
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
##                #print("HEEEEEYYYY")
##                #print(line_one_str_comment_pos_start)
            if GlobalFileSegmentMass[0][3]:
##                #print("GlobalFileSegmentMass[0][3]")
                have_MC = 1
                comment_many_str_massiv = GlobalFileSegmentMass[0][3]
                for CMSM in comment_many_str_massiv:
##                    #print(CMSM)
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
##                        #print('add')
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
##                #print(life)
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
                        continue
                    if QMOE != 0 and elem<=QMOE:
                        continue
                    #
                    if QMTS != 0 and elem>=QMTS:
                        continue
                    if QMTE != 0 and elem<=QMTE:
                        continue
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
                    if name_F == 'class':
                        if i == '{' and start == 0:
                            start+=1
                            start_char_in_line = line_num
                            start_pos_char_in_line = life_Mass[elem-1][1]
                            continue
                        if i == '{' and start != 0:
                            start+=1
                            continue
                        if i =='}' and start != 0:
                            end+=1
                            if (start-end)==0:
                                #print("STEP")
                                return [[start_char_in_line,start_pos_char_in_line],[line_num,life_Mass[elem-1][0]]]
                            continue
                    if name_F == 'func':
                        if elem<=last_chek_pos and line_num == num_str:
                            continue
                        if start == 0 and i == ';':
                            last_simbol=1
                            return [[0,0],[line_num,life_Mass[elem-1][0]]]
                        if i == '{' and start == 0:
                            #print(elem)
                            start+=1
                            start_char_in_line = line_num
                            start_pos_char_in_line = life_Mass[elem-1][1]
                            continue
                        if i == '{' and start != 0:
                            start+=1
                            continue
                        if i =='}' and start != 0:
                            end+=1
                            if (start-end)==0:
                                return [[start_char_in_line,start_pos_char_in_line],[line_num,life_Mass[elem-1][0]]]
                            continue

##                    if name_F=='CASE':
##                        if elem<=last_chek_pos and line_num == num_str:
##                            continue
##                        if t_case.search(i) and :
##                        if start == 0 and i == ';':
##                            last_simbol=1
##                            return [[0,0],[line_num,life_Mass[elem-1][0]]]
##                        if i == '{' and start == 0:
##                            #print(elem)
##                            start+=1
##                            start_char_in_line = line_num
##                            start_pos_char_in_line = life_Mass[elem-1][1]
##                            Switch_Start_elem=elem
##                            continue
##                        if i == '{' and start != 0:
##                            start+=1
##                            continue
##                        if i =='}' and start != 0:
##                            end+=1
##                            if (start-end)==0:
##                                Switch_End_elem=elem
##                                return [[start_char_in_line, start_pos_char_in_line, Switch_Start_elem], [line_num, life_Mass[elem-1][0], Switch_End_elem]]
##                            continue
                    if name_F=='SWITCH':
                        if elem<=last_chek_pos and line_num == num_str:
                            continue
                        if start == 0 and i == ';':
                            #print("NOPE")
                            last_simbol=1
                            return [[0,0],[line_num,life_Mass[elem-1][0],elem]]
                        if i == '{' and start == 0:
                            #print(elem)
                            start+=1
                            start_char_in_line = line_num
                            start_pos_char_in_line = life_Mass[elem-1][1]
                            Switch_Start_elem=elem
                            continue
                        if i == '{' and start != 0:
                            start+=1
                            continue
                        if i =='}' and start != 0:
                            end+=1
                            if (start-end)==0:
                                #print("YEA")
                                Switch_End_elem=elem
                                return [[start_char_in_line, start_pos_char_in_line, Switch_Start_elem], [line_num, life_Mass[elem-1][0], Switch_End_elem]]
                            continue
                    if name_F == 'ELSE_IF' or name_F=='FOR' or name_F == 'ELSE' or name_F == 'IF' or name_F == 'DO' or name_F=='WHILE':# or name_F=='SWITCH':
                        if elem<=last_chek_pos and line_num == num_str:
                            continue
                        if start == 0 and i == ';':
                            last_simbol=1
                            return [[0,0],[line_num,life_Mass[elem-1][0]]]
                        if i == '{' and start == 0:
                            #print(elem)
                            start+=1
                            start_char_in_line = line_num
                            start_pos_char_in_line = life_Mass[elem-1][1]
                            continue
                        if i == '{' and start != 0:
                            start+=1
                            continue
                        if i =='}' and start != 0:
                            end+=1
                            if (start-end)==0:
                                return [[start_char_in_line,start_pos_char_in_line],[line_num,life_Mass[elem-1][0]]]
                            continue
                    #Chek_roll_str_simbol_Close
##                            if re.search('[!"#$%&()*\'+-/:;=@[\\]^_`|~]',i) and start == 0:#'[!"#$%&()*\'+-./:;=@[\\]^_`|~]'
##                                ITs_not_class = 1
##                            if ITs_not_class == 0:
##                    if i == '{' and start == 0:
##                        start+=1
##                        start_char_in_line = line_num
##                        start_pos_char_in_line = life_Mass[elem-1][1]
##                        continue
##                    if i == '{' and start != 0:
##                            s
##                        start+=1
##                        continue
##                    if i =='}' and start != 0:
##                        end+=1
##                        if (start-end)==0:
##                            return [[start_char_in_line,start_pos_char_in_line],[line_num,life_Mass[elem-1][0]]]
##                        continue
            #Parser StrSegment Close
if __name__=='__main__':
    list_f = get_list()
    for file_id, path in enumerate(list_f, start=1):
        if file_id != 1:
            continue
        for_bord = open(path, 'r')
        border_f = borders(32, for_bord, 'class', 5, 0, 1)
        for_bord.close()
        #print("BLOCK_CLASS")
        #print(border_f)

##                        #
##                        if line_in_many_comment_block == 0:
##                                # Если не виден потенциально опасный участок в строке
##                                if num_line>=num_str and HaveOrNotToHaveStrElement == 0 and line_have_one_str_comment == 0 and have_MC == 0:
##                                        for Pos_char, char in enumerate(STR, start=1):
##                                                if char == '{' and start == 0:
##                                                        start+=1
##                                                        start_char_in_line = num_line
##                                                        start_pos_char_in_line = Pos_char
##                                                        continue
##                                                if char == '{' and start != 0:
##                                                        start+=1
##                                                        continue
##                                                if char =='}' and start != 0:
##                                                        end+=1
##                                                        if (start-end)==0:
##                                                                return [[start_char_in_line,start_pos_char_in_line],[num_line,Pos_char]]
##                                                        continue
##                                # Если имеется потенциально опасный участок в строке
##                                if num_line>=num_str and (HaveOrNotToHaveStrElement != 0 or line_have_one_str_comment != 0 or have_MC != 0):
##                                        for Pos_char, char in enumerate(STR, start=1):
##                                                if char == '{' and start == 0:
##                                                        rezult = Char_Pos_in_block_or_not(Pos_char, HaveOrNotToHaveStrElement, QMasSimbolStrInThisStr, have_MC, LHMCBlock, line_have_one_str_comment, line_one_str_comment_pos_start)
##                                                        if rezult == 1:
##                                                                start+=1
##                                                                start_char_in_line = num_line
##                                                                start_pos_char_in_line = Pos_char
##                                                                continue
##                                                if char == '{' and start != 0:
##                                                        rezult = Char_Pos_in_block_or_not(Pos_char, HaveOrNotToHaveStrElement, QMasSimbolStrInThisStr, have_MC, LHMCBlock, line_have_one_str_comment, line_one_str_comment_pos_start)
##                                                        if rezult == 1:
##                                                                start+=1
##                                                                continue
##                                                if char =='}' and start != 0:
##                                                        rezult = Char_Pos_in_block_or_not(Pos_char, HaveOrNotToHaveStrElement, QMasSimbolStrInThisStr, have_MC, LHMCBlock, line_have_one_str_comment, line_one_str_comment_pos_start)
##                                                        if rezult == 1:
##                                                                end+=1
##                                                                if (start-end)==0:
##                                                                        return [[start_char_in_line,start_pos_char_in_line],[num_line,Pos_char]]
##                                                                continue
