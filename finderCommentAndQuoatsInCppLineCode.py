# -*- coding: utf-8 -*-
def between(array, findStr, string, index = 0): #Проверка нахождения между элементами массива
    findIndex = string.find(findStr, index)
    index = 0
    if (array) and (array[0][0] != -1):
        for i in array:
            while (i[0] < findIndex) and (i[1] > findIndex) and (findIndex != -1):
                findIndex = string.find(findStr, findIndex + 1)
    return findIndex

def searching(comments, findStr, string, index = 0): #Поиск ключевого слова или символа в строке
    if index == -1:
        index = 0
    findIndex = string.find(findStr, index)
    if findIndex > -1:
        findIndex = between(comments['quotes'], findStr, string, index)
        if findIndex != -1:
            if comments['many_line_comments']:
                if (comments['many_line_comments'][len(comments['many_line_comments']) - 1][1] == -1) and (len(comments['many_line_comments']) > 1):
                    findIndex = between(comments['many_line_comments'][:-1], findStr, string, index)
                elif (comments['many_line_comments'][len(comments['many_line_comments']) - 1][1] == -1) and (len(comments['many_line_comments']) == 1):
                    findIndex = between([[comments['many_line_comments'][0][0], len(string) - 1]], findStr, string, index)
                else:
                    findIndex = between(comments['many_line_comments'], findStr, string, index)
        if findIndex != -1:
            if comments['one_line_comment'] != -1:
                findIndex = between([[comments['one_line_comment'], len(string) - 1]], findStr, string, index)
    return findIndex

def cleaner(comments, string): #Чистит строку от комментариев и кавычек
    temp = []
    if comments['one_line_comment'] != -1:
        string = string[:comments['one_line_comment']]
    if comments['quotes']:
        temp += comments['quotes']
    if comments['many_line_comments']:
        temp += comments['many_line_comments']
    # print('This is temp ', temp)
    if temp:
        if temp[-1][1] == -1:
            string = string[:temp[-1][0]]
            del temp[-1]
        if temp:
            for i in range(len(temp) - 1):
                for j in range(len(temp) - i - 1):
                    if temp[j][0] > temp[j + 1][0]:
                        temp[j], temp[j + 1] = temp[j + 1], temp[j]
            while temp:
                string = string[:temp[-1][0]] + string[temp[-1][1] + 1 + (temp[-1][1] == '/'):]
                del temp[-1]

    if string == '':
        return ''
    flag = False
    if string[0] == ' ':
        flag = True
    temp = string.split()
    if temp:
        string = ''
        for i in range(len(temp) - 1):
            string += temp[i] + ' '
        string += temp[-1]

    if flag:
        return ' ' + string
    return string

def cleanerWithoutQuotes(comments, string): #Очищает строку от комментариев
    flag = False
    for i in comments['many_line_comments']:
        if i[1] != -1:
            string = string[:i[0]] + ' ' + string[i[1]+2:]
        else:
            string = string[:i[0]]
    if comments['one_line_comment'] != -1:
        string = string[:comments['one_line_comment']]

    if string == '':
        return ''
    if string[0] == ' ':
        flag = True
    temp = string.split()
    string = ''
    for i in range(len(temp) - 1):
        string += temp[i] + ' '
    if temp:
        string += temp[-1]

    if flag:
        return ' ' + string
    return string


def findEscapeChar(string, index):#Проверка экранирования символа в данной строке по данному индексу и нахождения между ''
    flag = False
    temp = index
    while string[index - 1] == '\\':
        flag = not flag
        index -= 1
    if temp + 1 < len(string):
        if (string[temp - 1] == '\'') and (string[temp + 1] == '\''):
            flag = True

    return flag


def findComments(string): #Нахождение в строке коменнтариев
    result = {"quotes" : [],
              "many_line_comments": [],
              "one_line_comment" : -1}

    comment = False
    ignore = False
    m_com_flag = [False, -1]
    quote = [False, '$$$', -1]

    for index in range(len(string)):
        if comment:
            comment = False
            if string[index] == '/':
                result['one_line_comment'] = index - 1
                break
            elif string[index] == '*':
                m_com_flag[0] = True
                m_com_flag[1] = index - 1
        elif m_com_flag[0]:
            if index + 1 < len(string):
                if string[index] + string[index + 1] == '*/':
                    result['many_line_comments'].append([m_com_flag[1], index])
                    m_com_flag = [False, -1]
            else:
                result['many_line_comments'].append([m_com_flag[1], -1])
                m_com_flag = [False, -1]
                break
        elif quote[0]:
            if ignore:
                ignore = False
                continue
            elif string[index] == '\\' and index != len(string) - 2 and quote[1] != '`':
                ignore = True
            elif string[index] == quote[1]:
                result['quotes'].append([quote[2], index])
                quote = [False, '$$$', -1]
            elif index == len(string) - 1:
                result['quotes'].append([quote[2], -1])
                quote = [False, '$$$', -1]
        else:
            if string[index] == '/':
                comment = True
            elif string[index] == '"':
                quote = [True, '"', index]
            elif string[index] == '`':
                quote = [True, '`', index]
            elif string[index] == "'":
                quote = [True, "'", index]

    return result
