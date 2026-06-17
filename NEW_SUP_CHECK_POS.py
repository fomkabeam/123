def Char_Pos_in_block_or_not(I = 0, HaveOrNotToHaveStrElement = 0, QMasSimbolStrInThisStr = [], have_MC = 0, LHMCBlock = [], line_have_one_str_comment = 0, line_one_str_comment_pos_start = 0):
    add_IT = 1
    Add_Y = 1
    AD_IT = 1
    if HaveOrNotToHaveStrElement == 1:
        index_pos=1
        for index, QMSSITS in enumerate (QMasSimbolStrInThisStr, start=0):
            if index_pos == 1:
                if QMSSITS == 1:
                    if I > QMasSimbolStrInThisStr[index+index_pos][0] and I < QMasSimbolStrInThisStr[index+index_pos][1] :
                        add_IT = 0
                if QMSSITS == 2:
                    if I > QMasSimbolStrInThisStr[index+index_pos][0]:
                        add_IT = 0
                if QMSSITS == 3:
                    if I < QMasSimbolStrInThisStr[index+index_pos][1]:
                        add_IT = 0
            if index_pos == 2:
                index_pos = 1
                continue
            else:
                index_pos += 1
    if have_MC == 1:
        index_pos = 1
        for index, MCElement in enumerate (LHMCBlock, start=0):
            if index_pos == 1:
                if MCElement == 1:
                    if I > LHMCBlock[index+index_pos][0] and I < LHMCBlock[index+index_pos][1]:
                        Add_Y = 0
                if MCElement == 2:
                    if I > LHMCBlock[index+index_pos]:
                        Add_Y = 0
                if MCElement == 3:
                    if I < LHMCBlock[index+index_pos]:
                        Add_Y = 0
            if index_pos == 2:
                index_pos = 1
                continue
            else:
                index_pos+=1
    if line_have_one_str_comment == 1:
        if I > line_one_str_comment_pos_start:
            AD_IT = 0
    if add_IT != 0 and Add_Y != 0 and AD_IT !=0:
        return(1)
    else:
        return(0)
