def Save_Param_STR(F_Clon,param_SS,param_start,param_LS,param_lock,param_STR=''):
    scrol_conc_str=0
    if param_SS==param_LS:
        param_STR=F_Clon[param_SS-1][param_start:param_lock+1]
    elif param_LS-param_SS==1:
        param_STR=F_Clon[param_SS-1][param_start:]
        param_STR+=F_Clon[param_LS-1][:param_lock+1]
    elif param_LS-param_SS>1:
        count_conc_str=param_LS-param_SS
        param_STR=F_Clon[param_SS-1][param_start:]
        while scrol_conc_str!=count_conc_str:
            if param_SS+scrol_conc_str+1!=param_LS:
                param_STR+=F_Clon[param_SS+scrol_conc_str]
            else:
                param_STR+=F_Clon[param_LS-1][:param_lock+1]
            scrol_conc_str+=1
    return param_STR
