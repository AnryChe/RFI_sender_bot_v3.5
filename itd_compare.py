import socket
import numpy as np
import pandas as pd
import config

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)

"""
— or -0 длинное тире
'–' это дефис
ну и - просто минус
"""


def data_from_excel(data_file_name, header_line, zero_col, req_sheet_name):  # Датафрейм из Excel
    if socket.gethostname().lower() == "civil":
        file_name_to_read = 'D:\\02_Dev\\Python Scripts\\Inspector_v4' + f'\\{data_file_name}.xlsx'
    else:
        file_name_to_read = f'{data_file_name}.xlsx'
    print(file_name_to_read)
    with pd.ExcelFile(file_name_to_read) as xls_s:
        if req_sheet_name:
            readed_itd_data_df = pd.read_excel(xls_s, header=[header_line], sheet_name=req_sheet_name)
        else:
            readed_itd_data_df = pd.read_excel(xls_s, header=[header_line], sheet_name=xls_s.sheet_names[-1])
    xls_s.close()
    if data_file_name == 'status':
        print(readed_itd_data_df.head(8))
        itd_data_df = readed_itd_data_df.dropna(subset=[zero_col])
    else:
        itd_data_df = readed_itd_data_df
    return itd_data_df


def data_to_excel(rec_data_df, file_name_to_rec):  # График ночных дежурств
    if socket.gethostname() == "Civil":
        schedule_file_name = config.path + f'\\{file_name_to_rec}.xlsx'
    else:
        schedule_file_name = f'{file_name_to_rec}.xlsx'
    rec_data_df.to_excel(schedule_file_name)


def status_from_file():
    status_df = data_from_excel("status", 6, '№ АКТА').iloc[:, 0:16]
    status_df['№ АКТА'] = (status_df['№ АКТА'].str.replace(' ', '').str.replace('-', '-').str.replace('–', '-')
                           .str.replace('AKT', 'AKT').str.replace('AКТ', 'AKT').str.replace('AKТ', 'AKT')
                           .str.replace('NOC-EE', 'AKT-EE').str.replace('ЕЕ', 'EE').str.replace('№EE', '№AKT-EE'))
    return status_df


def register_from_file():
    register_df = data_from_excel("register", 10, '№ АОСР').astype('str').iloc[1:, 0:13]
    register_df['№ АОСР'] = register_df['№ АОСР'].astype('str').str.replace('-', '-').str.replace('–', '-')
    return register_df


def compare_dfs():
    reg_act_numbers = register_from_file()
    status_df = status_from_file()
    col_names = ['Акт реестра']
    res_df = pd.DataFrame(columns=[col_names])
    register_columns = reg_act_numbers.columns.tolist()
    reformed_df = reg_act_numbers[[register_columns[1], register_columns[6], register_columns[2], register_columns[3], register_columns[4],
                               register_columns[5], register_columns[10], register_columns[11]]]
    reformed_df.loc[:, (register_columns[1])] = reformed_df.loc[:, (register_columns[1])].astype('float').astype('int')

    #reformed_df[reformed_df.columns.tolist()[8]].fillna(' ')
    reformed_df.insert(5, 'ФИО ответственного (ПТО ЕЕ)', '')
    reformed_df.insert(6, 'ФИО проверяющего и подписывающего (WPUE)', '')
    data_to_excel(reformed_df, 'reformed')
    for a_n in reg_act_numbers['№ АОСР']:
        patt = a_n.replace('АКТ-ЕЕ-', '')
        col_count = len(res_df.columns) - 1
        head_str = [a_n]
        for i in range(col_count):
            head_str.append(np.nan)
        res_df.loc[len(res_df)] = head_str
        one_res_df = status_df[status_df['№ АКТА'].str.contains(patt)]
        if one_res_df.empty:
            sub_df_str = ['Совпадений не найдено']
            for i in range(col_count):
                sub_df_str.append(np.nan)
            res_df.loc[len(res_df)] = sub_df_str
        else:
            res_df = pd.concat([res_df, one_res_df], ignore_index=True)

    data_to_excel(res_df, 'compared')


# compare_dfs()