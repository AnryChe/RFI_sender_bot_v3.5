from six.moves import configparser
import datetime
import re
import socket
import pandas as pd
import config
import random


class InspectionsData:
    def __init__(self, ins_pos, insp_df):
        self.insp_order_number = insp_df.iloc[ins_pos, 19]
        self.insp_time = insp_df.iloc[ins_pos, 8]
        self.insp_number = insp_df.iloc[ins_pos, 11]
        self.insp_object = insp_df.iloc[ins_pos, 4]
        self.insp_description = insp_df.iloc[ins_pos, 2]
        self.insp_smr = insp_df.iloc[ins_pos, 16]
        self.insp_kiok = insp_df.iloc[ins_pos, 10]
        self.fndt_smr = self.insp_smr.find("+")
        self.fndt_kiok = self.insp_kiok.find("+")
        self.insp_discipline = insp_df.iloc[ins_pos, 1]


def get_discipline_types(ins_df):  # Функция получения списка дисциплин, по которым есть инспекции
    disc_types = ins_df['old_disc'].str.lower().unique()
    return disc_types


def get_df_len(ins_df):  # Функция получения длины дата фрейма для определения количества инспекций
    dframe_len = len(ins_df)
    return dframe_len


def gen_wbs_list(ins_df):  # функция поиска кода WBS в номере чертежа и создание списка WBS
    wbs_list = []
    print('фрейм на конвертировании WBS ')
    for index, row in enumerate(ins_df[' Чертеж']):
        corrected = re.findall('\\d{6}', str(row))
        if corrected:
            wbs_list.append(corrected[0])
        else:
            wbs_list.append('wbs не определен')
    return wbs_list


def gen_disc_list(ins_df):  # Функция создания списка дисциплин на основании спецдисциплины
    disc_list = []
    for sub_discipline in ins_df['Дисциплина']:
        if sub_discipline in str(config.sep_by_disc.values()):
            for k, v in config.sep_by_disc.items():
                if sub_discipline in v:
                    disc_list.append(k)
        else:
            disc_list.append("___ОБЩЕСТРОЙ___")
    return disc_list


def gen_day_time_list(ins_df):  # Функция создания списка дисциплин на основании спецдисциплины
    day_time_list = []
    day_time_start = datetime.time(hour=7, minute=59)
    day_time_end = datetime.time(hour=17, minute=58)
    for i in range(len(ins_df)):
        i_t = pd.to_datetime(ins_df.iloc[i]['Timedate']).time()
        if day_time_start < i_t < day_time_end:
            day_time_list.append('Дневные')
        else:
            day_time_list.append('Ночные')
    return day_time_list


def date_format(insp_df):  # Обрабатываем дату в зависимости от формата, текстового или даты
    print('фрейм на проверке даты')
    index_of_date_column = list(insp_df.columns).index('Дата')
    if str(type(insp_df['Дата'][0])) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>":
        insp_df['Дата'] = insp_df['Дата'].dt.date
        return insp_df
    else:
        print('Формат даты требует корректировки')
        ins_month_f = insp_df['Дата'].str.split(expand=True)
        ins_month_f['short'] = ins_month_f[1].str.slice(stop=3)
        ins_month_f['Дата'] = ins_month_f[0] + ' ' + ins_month_f['short'] + ' ' + ins_month_f[2]
        ins_month_f['Дата'] = pd.to_datetime(ins_month_f['Дата'], format='%d %b %Y')
        ins_date = ins_month_f['Дата']
        insp_df.drop(insp_df.columns[index_of_date_column], axis=1, inplace=True)
        insp_df.insert(loc=index_of_date_column, column='Дата', value=ins_date)
        insp_df['Дата'] = insp_df['Дата'].dt.date
        return insp_df


def time_format(ins_df):
    time_list = []
    print('фрейм на проверке времени')
    for index, row in enumerate(ins_df['Время']):
        for sep in config.sep_list:
            sep_index = config.sep_list.index(sep)
            sub_sep = config.sub_sep_list[sep_index]
            patt = '\\d{1,2}' + sep + '\\d{2}'
            founded_p = re.search(patt, str(row))
            t_format = f'%H{sub_sep}%M'
            if founded_p:
                founded_to_time = datetime.datetime.strptime(founded_p[0], t_format).time()
                time_list.append(founded_to_time)
            else:
                continue
    ins_df = ins_df.drop(['Время'], axis=1)
    ins_df.insert(loc=8, column='Время', value=time_list)
    return ins_df


def schedule_from_excel():
    if socket.gethostname() == "Civil":
        schedule_file_name = config.path + '\\night_schedule.xlsx'
    else:
        schedule_file_name = 'night_schedule.xlsx'
    schedule_df = pd.read_excel(schedule_file_name, header=0, index_col=0)
    return schedule_df


def tn_insert(ins_df):
    tn_list = []
    schedule_df = schedule_from_excel()
    for fio_ind in ins_df['Примечание '].index:
        fio = ins_df['Примечание '][fio_ind]
        if fio.title() in config.tn_name_dict:
            t_fio = fio.title()
            tn_list.append(config.tn_name_dict[t_fio])
        else:
            if ins_df['Время дня'][fio_ind] == 'Ночные':
                cur_date = ins_df['Дата'][fio_ind]
                short_name = (schedule_df[schedule_df[str(cur_date)] == 8].index[0])
                tn_list.append(config.tn_name_dict[short_name])
            else:
                tn_list.append('')
    return tn_list


def reformat_rfi(ins_df):  # Функция переформатирования списка инспекций под задачи статуса RFI
    print('фрейм поступил на переформатирование под статус')
    wbs_list = gen_wbs_list(ins_df)
    disc_list = gen_disc_list(ins_df)

    print(f'Общее количество инспекций: {len(ins_df)}')
    full_df = ins_df[["Дисциплина", "Описание инспекций", "Участок", " Чертеж", "Дата", "Время", "КиОК", "Номер RFI",
                      "Примечание ", "Отдел строительства", '#']]
    full_df.insert(loc=0, column='No    RFI', value='')
    full_df.insert(loc=3, column='WBS', value=wbs_list)
    full_df.insert(loc=6, column='Вид инспекции', value='H')
    full_df.insert(loc=11, column='Номер повторной инспекции', value='')
    full_df.insert(loc=12, column='Статус', value='Отклонено')
    full_df.insert(loc=14, column='sep_by_disc', value=disc_list)

    tdf_df = pd.DataFrame()
    tdf_df['Timedate'] = full_df['Дата'].astype(str) + ' ' + full_df['Время'].astype(str)
    full_df['Timedate'] = tdf_df
    full_df['Timedate'] = pd.to_datetime(full_df['Timedate'], format='%Y-%m-%d %H:%M:%S')

    full_df = full_df.drop(['Время'], axis=1)
    full_df.insert(loc=8, column='Время', value=full_df['Timedate'].dt.strftime('%H:%M'))

    day_time_list = gen_day_time_list(full_df)
    full_df.insert(loc=16, column='Время дня', value=day_time_list)
    tn_list = tn_insert(full_df)
    full_df.insert(loc=9, column='ФИО ТН', value=tn_list)

    full_df.insert(loc=18, column='old_disc', value=full_df['Дисциплина'])

    for key, values in config.rfi_sub_keys.items():  # Приводим дисциплины к требованиям по статусу RFI
        full_df.loc[(full_df['Дисциплина'].str.contains(key)), 'Дисциплина'] = values

    for key in config.civ_sub_keys:  # Меняем название дисциплины для геодезических проверок
        full_df.loc[full_df['old_disc'].str.contains('civil') & full_df['Описание инспекций'].str.contains(key), 'Дисциплина'] = 'CIVIL/SUR'

    full_df.loc[(full_df['Примечание '].str.contains(config.sur_sub_keys[0])), 'Дисциплина'] = 'SUR'  # Чистая геодезия
    full_df['Дисциплина'] = full_df['Дисциплина'].str.upper()
    return full_df


def make_file_from_ref_df(ins_df):
    ins_df = ins_df.drop(['Примечание '], axis=1)
    ins_df = ins_df.drop(['sep_by_disc'], axis=1)
    ins_df = ins_df.drop(['Timedate'], axis=1)
    ins_df = ins_df.drop(['Время дня'], axis=1)
    ins_df = ins_df.drop(['Отдел строительства'], axis=1)
    ins_df = ins_df.drop(['#'], axis=1)
    ins_df = ins_df.drop(['old_disc'], axis=1)
    ins_df.to_excel('reformatted.xlsx')


def get_df_from_file(file):
    try:
        inspections_file = pd.read_excel(file, header=4)
        gen_in_df = inspections_file.iloc[:, 0:12]
        print('get_df_from_file успешно получила и начала обработку файла')
        gen_in_df.dropna(subset=['Номер RFI'], inplace=True)
        gen_in_df['#'] = gen_in_df['#'].fillna(value=0)
        gen_in_df['#'] = gen_in_df['#'].astype(int)
        gen_in_df = gen_in_df.fillna(value='NA')
        gen_in_df['Примечание '] = gen_in_df['Примечание '].str.lower()
        gen_in_df['Дисциплина'] = gen_in_df['Дисциплина'].str.lower()
        try:
            gen_in_df = date_format(gen_in_df)
            try:
                gen_in_df = time_format(gen_in_df)
                ret_set = {'gen_in_df': gen_in_df, 'mess': ''}
                return ret_set
            except Exception as e:
                ret_set = {'df': None, 'mess': f'Ошибка формата в графе Время, исправьте в исходном файле, Except: {e}'}
                return ret_set
        except Exception as e:
            ret_set = {'gen_in_df': None, 'mess': f'Ошибка формата в графе Дата, исправьте в исходном файле, '
                                                  f'Except: {e}'}
            return ret_set
    except Exception as e:
        ret_set = {'df': None, 'mess': f'В отправленном файле ошибка:  \n{e}, проверьте расширение файла .xlsx и '
                                       f'список столбцов (в т.ч. на соответствие названий предыдущим файлам,  '
                                       f'Except: {e}'}
        return ret_set


def clean_df(gen_df, marker_column, del_mark):
    if gen_df[marker_column].str.contains(del_mark).any():
        dropped_str = gen_df[gen_df[marker_column].str.contains(del_mark)][marker_column]
        cleaned_df = gen_df.drop(dropped_str.index, axis=0)
        return cleaned_df
    else:
        return gen_df


def create_conf(my_conf_dict, my_conf_name, my_config_file):
    my_config = configparser.ConfigParser()
    my_config[my_conf_name] = my_conf_dict
    with open(my_config_file, 'w') as configfile:
        my_config.write(configfile)


def add_to_my_conf(section_name, my_config_file):
    my_config = configparser.ConfigParser()
    my_config.read(my_config_file)
    my_config.add_section(section_name)
    with open(my_config_file, 'w') as configfile:
        my_config.write(configfile)


def get_conf_section(my_config_file):
    my_config = configparser.ConfigParser()
    my_config.read(my_config_file)
    return my_config.sections()


def read_conf(my_conf_name, my_config_file):
    my_config = configparser.ConfigParser()
    my_config.read(my_config_file)
    config_readed_list = {}
    for users_key in my_config[my_conf_name].keys():
        config_readed_list[users_key] = my_config.get(my_conf_name, users_key)
    return config_readed_list


def add_user_to_config(conf_username_dict, my_conf_name, my_config_file):
    my_config = configparser.ConfigParser()
    my_config.read(my_config_file)
    try:
        for user_key, user_name in conf_username_dict.items():
            my_config[my_conf_name][user_key] = str(user_name)
    except:
        pass
    with open(my_config_file, 'w') as configfile:
        my_config.write(configfile)


def del_user_from_config(conf_username_key, my_conf_name, my_config_file):
    my_config = configparser.ConfigParser()
    my_config.read(my_config_file)
    for user_key in conf_username_key:
        for s_key in my_config[my_conf_name]:
            print(s_key)
        my_config.remove_option(my_conf_name, user_key)
        print(my_config.has_section(my_conf_name))
        for s_key in my_config[my_conf_name]:
            print(s_key)
    with open(my_config_file, 'w') as configfile:
        my_config.write(configfile)


def get_random_phrase():
    with open("Runs.txt", 'r', encoding='cp1251') as random_text:
        phrase_list = []
        for i in random_text:
            phrase_list.append(i)
        return random.choice(phrase_list)


# create_conf(config.tn_name_dict, 'registered_users',  'users_data.ini')


def make_handbook(data_series):
    the_handbook = {}
    phone_pattern = '\+\d{12}|\+\d{0,}\s\d{0,}\s\d{0,}\s\d{0,}\s\d{0,}'
    name_pattern = '\S{0,}'
    sub_name_pattern = '\s\S{0,}'
    for data_base in data_series:
        phone = re.search(phone_pattern, data_base)
        if phone:
            surname = re.search(name_pattern, data_base)[0]
            sub_surname = re.search(sub_name_pattern, data_base)[0].replace(' ', '')
            the_handbook[surname] = phone[0].replace(' ', '')
            the_handbook[sub_surname] = phone[0].replace(' ', '')
    return the_handbook

