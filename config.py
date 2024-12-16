inspection_bot_token = "your tocken"
path = 'your path'
ai_pyton_dev_ac_key = 'ai tocken'

sep_by_disc = {'___ОБЩЕСТРОЙ___': ['civil', 'coating', 'structural', 'civ/sur', 'sur', 'piping'],
               '___МЕХАНИКА___': ['mechanical', 'mech/sur', 'mec/sur', 'mec/weld'],
               '___ЭЛЕКТРИКА___': ['electrical'], '___АВТОМАТИЗАЦИЯ___': ['instrument', 'instrumentation']}

group_id_list = {"___ОБЩЕСТРОЙ___": 'id', "___МЕХАНИКА___": 'id',
                 "___ЭЛЕКТРИКА___": 'id',
                 "___АВТОМАТИЗАЦИЯ___": 'id', "___ГЕОДЕЗИЯ___": 'id', "my_id": 'your id'}

flvb_list = [id1, id2] 




month_list = {'январь': 'января', 'февраль': 'февраля', 'март': 'марта', 'апрель': 'апреля', 'май': 'мая',
              'июнь': 'июня', 'июль': 'июля', 'август': 'августа', 'сентябрь': 'сентября', 'октябрь': 'октября',
              'ноябрь': 'ноября', 'декабрь': 'декабря'}

rfi_columns = ['#', 'Дата', 'Время', 'Номер RFI', 'Статус инспекций', 'Дисциплина', 'Участок', 'Описание инспекций',
               ' Чертеж', 'Отдел строительства', 'КиОК']

pythonanywhere_proxy = 'http://proxy.server:3128'

civ_sub_keys = ['опалубк', 'анкер']
sur_sub_keys = ['геодез', 'Геодез']
rfi_sub_keys = {'coating': 'CIVIL', 'mechanic': 'MEC', 'electric': 'ELE', 'piping': 'PI', 'instrument': 'IN'}

sep_list = [':', '/', '[.]', ' ']
sub_sep_list = [':', '/', '.', ' ']

tn_name_dict = {'mask': 'Mask I.',
                'jobs': 'Jobs S.'}


