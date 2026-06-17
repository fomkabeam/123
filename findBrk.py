# -*- coding: utf-8 -*-
def findBrk(comments, string, brk, sum = 0, index = 0): #Скрипт ищет скобки и возвращает массив типа [0,[[1,2],[5,7]]]
    if brk == '(' or brk == ')' or brk == '()':                                      #Где 0 - полученная сумма в конце
        start = '('                                     #[[1,2],[5,7]] - массив всех найденых блоков в строке
        end = ')'                                       #если в это массиве -1 то
    elif brk == '{' or brk == '}' or brk == '{}':                                    #начало или конец этого блока находятся в другой строке
        start = '{'                                     #в массиве соотвествующие индексы в строке, нумерация с 0
        end = '}'

    result = [0, []]
    array  = [] #Формирование массива идексов

    if start not in string and end not in string:
        return result

    if comments['quotes']:
        for i in comments['quotes']:
            array.append(i)
    if comments['many_line_comments']:
        for i in comments['many_line_comments']:
            if i[1] != -1:
                array.append(i)
            else:
                string = string[:i[0]]
    if comments['one_line_comment'] != -1:
        string = string[:comments['one_line_comment']]

    if array:
        for i in range(len(array)): #Сортировка пузырьком
            for j in range(0, len(array)-i-1):
                if array[j][0] > array[j+1][0] :
                    array[j], array[j+1] = array[j+1], array[j]

        arr = []
        for i in range(len(array)): #Конец формирования
            if i == 0:
                if array[i][0] != 0:
                    arr += list(range(array[i][0]))
                if len(array) == 1:
                    arr += list(range(array[i][1] + 1, len(string)))
            elif i == len(array) - 1:
                arr += list(range(array[i-1][1] + 1, array[i][0]))
                if array[i][1] < len(string) - 1:
                    arr += list(range(array[i][1] + 1, len(string)))
            else:
                arr += list(range(array[i-1][1] + 1, array[i][0]))
        while arr[0] < index:
            del arr[0]
        del array
    else:
        arr = list(range(len(string)))

    startIndex = -1
    endIndex = -1

    # print(arr)
    indx = 0
    while (sum == 0) and (indx < len(arr)): #Первое вхождение
        if string[arr[indx]] == start:
            sum += 1
            startIndex = arr[indx]
        elif string[arr[indx]] == end:
            sum -= 1
        indx += 1

    if sum == 0:
        return result

    while indx < len(arr): #Происк скобок
        if string[arr[indx]] == start:
            sum += 1
        elif string[arr[indx]] == end:
            sum -= 1
        if sum == 0:
            endIndex = arr[indx]
            result[1].append([startIndex, endIndex]) #Запись конца и начала, -1 в случае нахождения начала или конца в другой строке

            startIndex = -1
            endIndex = -1
            indx += 1
            while (sum == 0) and (indx < len(arr)):
                if string[arr[indx]] == start:
                    sum += 1
                    startIndex = arr[indx]
                elif string[arr[indx]] == end:
                    sum -= 1
                indx += 1
            continue
        indx += 1

    result[0] = sum
    return result
