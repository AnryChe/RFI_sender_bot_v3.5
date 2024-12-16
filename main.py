import datetime
import logging
import asyncio
import pandas as pd
import re
import emoji
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text

# Импортируем конфигурационные данные, токен, дисциплины, группы, свой ID и учетные данные.
import config

# Импортируем класс инспекции, а также функции получения инспекций
from ex_ex import (InspectionsData, get_df_from_file, make_file_from_ref_df, reformat_rfi,
                   create_conf, add_user_to_config, read_conf, del_user_from_config, add_to_my_conf, clean_df,
                   get_random_phrase, make_handbook, get_conf_section)

import locale

locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token=config.inspection_bot_token, parse_mode='HTML', proxy=config.pythonanywhere_proxy)  # proxy='http://proxy.server:3128'

# Диспетчер
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Получаем стартовые данные инспекций
gen_inspections_df = pd.DataFrame()  # refresh_inspections_file()  # генерируем датафрейм с инспекциями

unread_dataframes = {}
readed_dataframes = {}
ready_insp_to_shot = 0
ready_private_insp_to_shot = 0
my_state_var = 0  # переменная состояния для регистрации
mess_time_out = 3  # устанавливаем таймаут для отправки сообщений в группе (не более 20 сообщений в минуту)

allboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
myboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
buttons = ["Подписка", "Отписаться", "Телефон", "Мысль"]
myttons = ["Подписка", "Отписаться", "Телефон", "Номера", "Мысль", "Сотрудник", "Мемка"]
allboard.add(*buttons)
myboard.add(*myttons)

@dp.message_handler(commands=["start"])  # Хэндлер на команду /start
async def start_command(message: types.Message):
    if message.chat.id > 0:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Подписка", "Отписаться", "Телефон", "Мысль"]
        keyboard.add(*buttons)
        if message.chat.id in config.flvb_list:
            await message.answer("Привет! Я бот, который публикует шаблоны инспекций МОФ-3\n"
                                 "Отправь мне файл с инспекциями и я верну обработанный файл \n"
                                 "Также можешь пройти регистрацию для получения шаблонов распределенных инспекций",
                                 reply_markup=keyboard)
        else:
            await message.answer("Привет! Я бот, который публикует шаблоны по дисциплинам инспекций МОФ-3\n"
                                 "Также можете сделать подписку для получения шаблонов распределенных инспекций.")
            await message.answer('<b>Дисклеймер.</b>\nЧат-бот и канал - личная разработка, к деятельности компании Worley не '
                                    'имеет никакого отношения. Автор не несет ответственности за '
                                    'предоставляемую здесь информацию а также правильность распределения инспекций. Касательно исходных данных по инспекциям '
                                    'рекомендую обращаться к ответственным лицам Подрядчика'
                                    'Продолжая использовать бот Вы даете согласие на обработку персональных данных'
                                    'Телеграм установил ограничение по количеству сообщений в минуту для ботов. Имейте ввиду, что сообщения будут приходить с задержкой')
            await asyncio.sleep(10)
            await message.answer("Если Ваша фамилия в списке сотрудников, то после подписки сможете получать инспекции,"
                                 "которые были распределены Вам. \nРекомендуется, если количество инспекций в канале регулярно бывает более 6-8 штук. "
                                 "Выбор в любом случае теперь за Вами.\n"
                                 "Также не стоит пользоваться исключительно информацией в канале или от чат-бота, основной источник - официальная почта.\n"
                                 "Если при распределении инспекций Ваша фамилия не будет вписана (или вписана с ошибкой) в обработанном уведомлении -"
                                 " инспекция в личные сообщения не придет. Найти ее, как и все остальные инспекции можно в канале.\n"
                                 "Если не захотите далее получать шаблоны, отпишитесь от рассылки.")
            await asyncio.sleep(15)
            await message.answer("Помимо появившихся внизу кнопок всегда можете воспользоваться в чате с ботом текстовыми командами: \n/start, Подписка, Отписаться, Телефон.\n"
                                 "Также Вы можете воспользоваться поиском номеров телефонов сотрудников Подрядчика, "
                                 "которые были указаны в уведомлениях об инспекции. Функция доступна для сотрудников компаний АГМК и Worley\n"
                                 "Если Вы сотрудник компаний, но не внесены в список, обратитесь к владельцу бота по ссылке ниже.\n"
                                 "Возможно в какой то момент при появлении новых сотрудников их номера будут отсутствовать, но справочник регулярно обновляется.\n"
                                 "Для поиска после нажатия кнопки Телефон (или просто текстовой команды в чат Телефон) введите несколько букв имени или фамилии.\n"
                                 "Будут выведены все найденные совпадения\n"
                                 "Если закончились аргументы в споре с подрядчиком - воспользуйтесь функцией под названием Мысль, "
                                 "она позволит Вам блеснуть знаниями, что обесценит аргументы подрядчика и даст Вам время на поиск своих аргументов. \n"
                                 "Успехов в использовании, все просьбы и предложения пишите @AndreiChumak\n"
                                 "Кнопки внизу:",
                                 reply_markup=keyboard)
        await bot.send_message(text=f"Пользователь с id {message.chat.id} с ником {message.from_user.username}, именем {message.from_user.full_name} зашел в чат",
                               chat_id=config.group_id_list["my_id"])
        add_user_to_config({message.from_user.full_name: message.chat.id}, 'unregistered_users', 'users_data.ini')
        # await message.answer(f'Твой ID: {message.chat.id}')  # Запрос для получения ID группы и добавления в конфиг


@dp.message_handler(Text(equals="Старт"))  # Хэндлер на команду /start
async def sstart_command(message: types.Message):
    if message.chat.id > 0:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Подписка", "Отписаться", "Телефон", "Мысль"]
        keyboard.add(*buttons)
        if message.chat.id in config.flvb_list:
            await message.answer("Привет! Я бот, который публикует шаблоны инспекций МОФ-3\n"
                                 "Отправь мне файл с инспекциями и я верну обработанный файл \n"
                                 "Также можешь пройти регистрацию для получения шаблонов распределенных инспекций",
                                 reply_markup=keyboard)
        else:
            await message.answer("Привет! Я бот, который публикует шаблоны по дисциплинам инспекций МОФ-3\n"
                                 "Также можете сделать подписку для получения шаблонов распределенных инспекций.")
            await message.answer('<b>Дисклеймер.</b>\nЧат-бот и канал - личная разработка, к деятельности компании Worley не '
                                    'имеет никакого отношения. Автор не несет ответственности за '
                                    'предоставляемую здесь информацию а также правильность распределения инспекций. Касательно исходных данных по инспекциям '
                                    'рекомендую обращаться к ответственным лицам Подрядчика'
                                    'Продолжая использовать бот Вы даете согласие на обработку персональных данных'
                                    'Телеграм установил ограничение по количеству сообщений в минуту для ботов. Имейте ввиду, что сообщения будут приходить с задержкой')
            await asyncio.sleep(10)
            await message.answer("Если Ваша фамилия в списке сотрудников, то после подписки сможете получать инспекции,"
                                 "которые были распределены Вам. \nРекомендуется, если количество инспекций в канале регулярно бывает более 6-8 штук. "
                                 "Выбор в любом случае теперь за Вами.\n"
                                 "Также не стоит пользоваться исключительно информацией в канале или от чат-бота, основной источник - официальная почта.\n"
                                 "Если при распределении инспекций Ваша фамилия не будет вписана (или вписана с ошибкой) в обработанном уведомлении -"
                                 " инспекция в личные сообщения не придет. Найти ее, как и все остальные инспекции можно в канале.\n"
                                 "Если не захотите далее получать шаблоны, отпишитесь от рассылки.")
            await asyncio.sleep(15)
            await message.answer("Помимо появившихся внизу кнопок всегда можете воспользоваться в чате с ботом текстовыми командами: \n/start, Подписка, Отписаться, Телефон.\n"
                                 "Также Вы можете воспользоваться поиском номеров телефонов сотрудников Подрядчика, "
                                 "которые были указаны в уведомлениях об инспекции. Функция доступна для сотрудников компаний АГМК и Worley\n"
                                 "Если Вы сотрудник компаний, но не внесены в список, обратитесь к владельцу бота по ссылке ниже.\n"
                                 "Возможно в какой то момент при появлении новых сотрудников их номера будут отсутствовать, но справочник регулярно обновляется.\n"
                                 "Для поиска после нажатия кнопки Телефон (или просто текстовой команды в чат Телефон) введите несколько букв имени или фамилии.\n"
                                 "Будут выведены все найденные совпадения\n"
                                 "Если закончились аргументы в споре с подрядчиком - воспользуйтесь функцией под названием Мысль, "
                                 "она позволит Вам блеснуть знаниями, что обесценит аргументы подрядчика и даст Вам время на поиск своих аргументов. \n"
                                 "Успехов в использовании, все просьбы и предложения пишите @AndreiChumak\n"
                                 "Кнопки внизу:",
                                 reply_markup=keyboard)
        await bot.send_message(text=f"Пользователь с id {message.chat.id} с ником {message.from_user.username}, именем {message.from_user.full_name} зашел в чат",
                               chat_id=config.group_id_list["my_id"])
        add_user_to_config({message.from_user.full_name: message.chat.id}, 'unregistered_users', 'users_data.ini')
        # await message.answer(f'Твой ID: {message.chat.id}')  # Запрос для получения ID группы и добавления в конфиг


@dp.message_handler(content_types=["document"])  # Хэндлер на отправку дока в чат. Переформатирует документ для статуса
async def receive_command(message: types.Message):
    keyboard_1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    my_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons_1 = ["Раздача каналам", "Раздача лично", "Старт", "Телефон", "Мысль"]
    my_buttons = ['Раздача каналам', "Раздача лично", "/timeout", "Телефон", "Сотрудник", "Номера", "Мысль", "Мемка"]
    keyboard_1.add(*buttons_1)
    my_keyboard.add(*my_buttons)
    if message.chat.id in config.flvb_list:  # Является ли пользователь админом, от которого можно принять файл?
        rec_file_id = message.document.file_id
        rec_file_name = message.document.file_name
        file = await bot.download_file_by_id(rec_file_id)
        global gen_inspections_df
        set_from_file = get_df_from_file(file)
        if set_from_file['mess']:  # Проверяем, загрузился ли файл инспекций и соответствует ли он требуемому формату
            await message.answer('В отправленном файле ошибка, проверьте соответствие форматирования и заполнения '
                                 'колонок файла образцу', reply_markup=types.ReplyKeyboardRemove())
            await bot.send_message(text=set_from_file['mess'], chat_id=config.group_id_list["my_id"])
        else:
            gen_inspections_df = reformat_rfi(set_from_file['gen_in_df'])
            await message.answer(f"\nПолучил файл: <b>{rec_file_name}</b>, сейчас обработаю.\n",
                                 reply_markup=keyboard_1)
            if message.chat.id != int(config.group_id_list["my_id"]):  # Если отправил не я - шлем себе уведомление
                await bot.send_message(text=f"Пользователь с id {message.chat.id} {message.from_user.username} "
                                            f"отправил файл {rec_file_name} на переформатирование",
                                       chat_id=config.group_id_list["my_id"])
            make_file_from_ref_df(gen_inspections_df)
            await asyncio.sleep(0.25)

            await message.reply_document(open('reformatted.xlsx', 'rb'), caption='Переформатированный файл для статуса')
            ref_doc = open('reformatted.xlsx', 'rb')
            if message.chat.id != int(config.group_id_list["my_id"]):
                await bot.send_document(chat_id=config.group_id_list["my_id"], document=ref_doc,
                                        caption='Переформатированный файл для статуса')

            global ready_insp_to_shot
            ready_insp_to_shot = 1
            global ready_private_insp_to_shot
            ready_private_insp_to_shot = 1

            await message.answer(f"Заряжены инспекции из файла <b>{rec_file_name}</b>\n Для запуска раздачи "
                                 f"в каналы и лично нажмите "
                                 f"на кнопку Раздать каналам\nЕсли нужно раздать только распределенные инспекции "
                                 f"выберите Раздача лично\n"
                                 f"Если по какой то причине не получили файл для статуса "
                                 f"инспекций - проверьте файл на соответствие шаблона файла ранее присланным  или "
                                 f"обратитесь к админу @AndreiChumak", reply_markup=keyboard_1)
            await bot.send_message(text="дави кнопки\n", chat_id=config.group_id_list["my_id"],
                                   reply_markup=my_keyboard)

            # insp_date = gen_inspections_df.iloc[0, 1] # иногда дату присылают в виде даты, а не текста)))
    else:  # Если пользователь не админ - шлем его, и отправляем себе всю информацию о нем
        await message.answer("Привет! Обратись к админу этого канала для получения детальной информации! @AndreiChumak")
        await bot.send_message(text=f"Пользователь с id {message.chat.id}, {message.from_user.username}, "
                                    f"{message.from_user.full_name} попытка отправки файла",
                               chat_id=config.group_id_list["my_id"])



@dp.message_handler(Text(equals="Раздача каналам"))  # Хэндлер на Рассылку по каналам шаблонов инспекций
async def inspect_command(message):
    keyboard_1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons_1 = ["Старт", "Телефон", "Мысль"]
    keyboard_1.add(*buttons_1)
    global ready_insp_to_shot
    if ready_insp_to_shot == 1:
        await message.answer('Запустил  раздачу', reply_markup=types.ReplyKeyboardRemove())
        ready_insp_to_shot = 0
        sur_ins = False
        clean_canceled = clean_df(gen_inspections_df, "Примечание ", "аннулир")
        clean_edited = clean_df(clean_canceled, "Примечание ", "изменен")
        clean_to_sign = clean_df(clean_edited, "Примечание ", "подпис")
        #clean_to_sign = clean_df(clean_edited, "Примечание ", "согласов")
        for uniq_discipline in clean_to_sign['sep_by_disc'].unique():
            disc_inspections_df = clean_to_sign[clean_to_sign['sep_by_disc'] == uniq_discipline]
            for uniq_date in disc_inspections_df['Дата'].unique():
                date_gen_inspections_df = disc_inspections_df[disc_inspections_df['Дата'] == uniq_date]
                for uniq_day_time in date_gen_inspections_df['Время дня'].unique():
                    if uniq_day_time == "Ночные":
                        emo_set = emoji.emojize(":crescent_moon:")
                    if uniq_day_time == "Дневные":
                        emo_set = emoji.emojize(":sun:")
                    dt_inspections_df = date_gen_inspections_df[date_gen_inspections_df['Время дня'] == uniq_day_time]
                    await bot.send_message(text=f'{emo_set}{emo_set}{emo_set}{emo_set}{emo_set}{emo_set}{emo_set}',
                                           chat_id=config.group_id_list[uniq_discipline])  # Выдаем дату инспекций
                    await asyncio.sleep(mess_time_out / 2)
                    await bot.send_message(text=f'<b>{uniq_day_time} инспекции на '
                                                f'{datetime.datetime.strftime(uniq_date, "%d %m %Y")}</b>',
                                           chat_id=config.group_id_list[uniq_discipline])  # Выдаем дату инспекций
                    await asyncio.sleep(mess_time_out * 1,5)
                    if dt_inspections_df['Дисциплина'].str.contains('SUR').any():
                        sur_ins = True
                        await bot.send_message(text=f'<b>{uniq_day_time} геодезические проверки на '
                                                    f'{datetime.datetime.strftime(uniq_date, "%d %m %Y")}</b>',
                                               chat_id=config.group_id_list['___ГЕОДЕЗИЯ___'])
                    for discipline in dt_inspections_df['old_disc'].unique():  # Добавляем фреймы инспекций в словарь
                        # не прочтенных инспекций
                        index_dropped_df = dt_inspections_df[
                            dt_inspections_df['old_disc'].str.lower() == discipline].reset_index()
                        del index_dropped_df['index']
                        unread_dataframes[discipline] = index_dropped_df

                        cur_df_len = len(unread_dataframes[discipline])  # длина текущего фрейма вида работ
                        await bot.send_message(text=f'<b>{discipline.upper()} : {cur_df_len} инсп.</b>',
                                               chat_id=config.group_id_list[uniq_discipline])  # заголовок вида работ
                        # с их количеством
                        await asyncio.sleep(mess_time_out)
                        await message_sender(cur_df_len, unread_dataframes[discipline], uniq_discipline,
                                             'Инспекция')  # запускаем
                        # функцию шаблонов RFI
                        if unread_dataframes[discipline]['Дисциплина'].str.contains('SUR').any():
                            sur_ins = True
                            survey_df = unread_dataframes[discipline][
                                unread_dataframes[discipline]['Дисциплина'].str.contains('SUR')]
                            sur_df_len = len(survey_df)
                            await bot.send_message(text=f'<b>{discipline.upper()} : {sur_df_len} инсп.</b>',
                                                   chat_id=config.group_id_list['___ГЕОДЕЗИЯ___'])

                            await message_sender(sur_df_len, survey_df, '___ГЕОДЕЗИЯ___',
                                                 'Геодезическая проверка к инспекции')  # запускаем
                        readed_dataframes[discipline] = unread_dataframes[
                            discipline]  # переносим отправленные инспекции из нечитанных в прочитанные
                        unread_dataframes.pop(discipline, None)
                        await asyncio.sleep(mess_time_out)
            emo_sub_set = emoji.emojize(":information:")
            await bot.send_message(text=f'{emo_sub_set}Дисклеймер и инструкция по ссылке (рекомендуется к прочтению, просмотр по команде Старт):\n@mof3inspector_bot \nBe careful on inspections!',
                                   chat_id=config.group_id_list[uniq_discipline])
            if sur_ins:
                await bot.send_message(text=f'{emo_sub_set}Дисклеймер и инструкция по ссылке (рекомендуется к прочтению, просмотр по команде Старт):\n@mof3inspector_bot \nBe careful on inspections!',
                                       chat_id=config.group_id_list['___ГЕОДЕЗИЯ___'])
            sur_ins = False
            await asyncio.sleep(mess_time_out)

        await private_inspect_command(message)
        now = datetime.datetime.now(pytz.timezone('Asia/Tashkent'))

        if message.chat.id != int(config.group_id_list["my_id"]):
            await message.answer(text=f"<b>Раздача окончена в {datetime.datetime.strftime(now, '%H:%M  %d %m %Y')}</b>\n",
                            reply_markup=keyboard_1)
        await bot.send_message(text=f"<b>Раздача окончена в {datetime.datetime.strftime(now, '%H:%M  %d %m %Y')}</b>\n",
                               chat_id=config.group_id_list["my_id"],
                               reply_markup=keyboard_1)
        print(f'Раздача окончена в {now}')  # семафорим себе в консоль об окончании раздачи.
    else:
        await bot.send_message(text="<b>Заряженные инспекции розданы!</b>",
                               chat_id=config.group_id_list["___ОБЩЕСТРОЙ___"])
    await clear_shotgun()


async def message_sender(cur_df_len, inspections_df, discipline, sub_text):  # функция шаблонов RFI

    for current_inspection in range(cur_df_len):  # Перебираем строки в датафрейме текущего вида работ
        message_inspections = InspectionsData(current_inspection, inspections_df)  # Экз. класса инспекции
        # на основании экземпляра класса инспекции отправляем в группу шаблон ответа по инспекции:
        time_mess = f'<b>{message_inspections.insp_order_number}.</b> Время: <u>{message_inspections.insp_time}</u>'
        await bot.send_message(text=time_mess, chat_id=config.group_id_list[discipline])
        await asyncio.sleep(mess_time_out)
        insp_mess = (f'{sub_text} {message_inspections.insp_number[message_inspections.insp_number.rfind("-") + 1:]}.\n'
                     f'<i>{message_inspections.insp_object}.</i>\n{message_inspections.insp_description}.\n'
                     f'\nСМР {message_inspections.insp_smr[0:message_inspections.fndt_smr - 1]}, '
                     f'КиОК {message_inspections.insp_kiok[0:message_inspections.fndt_kiok - 1]}')
        await bot.send_message(text=insp_mess, chat_id=config.group_id_list[discipline])
        await asyncio.sleep(mess_time_out)


@dp.message_handler(Text(equals="Раздача лично"))  # Хэндлер на Рассылку по каналам шаблонов инспекций
async def private_inspect_command(message):
    global ready_private_insp_to_shot
    if ready_private_insp_to_shot == 1:
        ready_private_insp_to_shot = 0
        if message.chat.id in config.flvb_list:
            await message.answer('Запустил  раздачу в личку', reply_markup=types.ReplyKeyboardRemove())
            await asyncio.sleep(2)
            if message.chat.id != 5709783583:
                await bot.send_message(text='Запустил  раздачу в личку', chat_id=5709783583)
            clean_canceled = clean_df(gen_inspections_df, "Примечание ", "аннулир")
            clean_edited = clean_df(clean_canceled, "Примечание ", "изменен")
            clean_to_sign = clean_df(clean_edited, "Примечание ", "подпис")
            cur_df_len = len(clean_to_sign)
            await private_message_sender(cur_df_len, clean_to_sign, 'Инспекция')
    else:
        await message.answer("Раздача инспекций в личку уже запущена. Дождитесь окончания раздачи, затем можно будет зарядить инспекции вновь")


async def private_message_sender(cur_df_len, inspections_df, sub_text):  # функция шаблонов RFI
    keyboard_1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons_1 = ["Старт", "Телефон", "Мысль"]
    keyboard_1.add(*buttons_1)
    reg_users_list = read_conf('registered_users', 'users_data.ini')
    sent_counter = 0
    inspections_df = inspections_df.reset_index()
    del inspections_df['index']
    last_msg_id = None
    for current_inspection in range(cur_df_len):  # Перебираем строки в датафрейме текущего вида работ
        message_inspections = InspectionsData(current_inspection, inspections_df)  # Экз. класса инспекции
        # на основании экземпляра класса инспекции отправляем в группу шаблон ответа по инспекции:
        time_mess = f'<b>{message_inspections.insp_order_number}.</b> Время: <u>{message_inspections.insp_time}</u>'
        insp_mess = (f'{sub_text} {message_inspections.insp_number[message_inspections.insp_number.rfind("-") + 1:]}.\n'
                     f'<i>{message_inspections.insp_object}.</i>\n{message_inspections.insp_description}.\n'
                     f'\nСМР {message_inspections.insp_smr[0:message_inspections.fndt_smr - 1]}, '
                     f'КиОК {message_inspections.insp_kiok[0:message_inspections.fndt_kiok - 1]}')

        if inspections_df['Примечание '][current_inspection] in str(reg_users_list.keys()):
            if last_msg_id:
                await bot.delete_message(config.group_id_list['my_id'], last_msg_id)
                print('deleted')
            inspector_name = inspections_df['Примечание '][current_inspection]
            await bot.send_message(text=time_mess, chat_id=reg_users_list[inspector_name])
            # await asyncio.sleep(mess_time_out)
            await bot.send_message(text=insp_mess, chat_id=reg_users_list[inspector_name])
            sent_counter += 1
            print(f'Роздано {sent_counter}')
            info_msg = await bot.send_message(text=f'Отправлено {sent_counter}-я инспекция {message_inspections.insp_number[message_inspections.insp_number.rfind("-") + 1:]}', chat_id=config.group_id_list['my_id'])
            last_msg_id = info_msg.message_id

    await asyncio.sleep(mess_time_out)
    print('Все роздано')
    if last_msg_id:
        await bot.delete_message(config.group_id_list['my_id'], last_msg_id)
    await bot.send_message(text=f'Отправлено в личку {sent_counter} инспекций', chat_id=config.group_id_list['my_id'], reply_markup=keyboard_1)
    await bot.send_message(text=f'Отправлено в личку {sent_counter} инспекций', chat_id=5709783583, reply_markup=keyboard_1)


async def clear_shotgun():  # очищаем переменную статуса инспекций, чтобы другой пользователь не начал повторную раздачу
    global ready_insp_to_shot
    ready_insp_to_shot = 0


@dp.message_handler(Text(equals="Подписка"))  # Хэндлер на команду /start
async def reg_user_id(message: types.Message):
    if message.chat.id > 0:
        global my_state_var
        print(my_state_var)
        if my_state_var == 0:
            my_state_var = 1
            await message.answer("    Для регистрации введите Вашу <b>фамилию</b> на русском языке (без инициалов).\n"
                                 "    После успешной регистрации Вы будете получать инспекции, закрепленные за Вами "
                                 "(за исключением случаев, когда раздача будет производиться до распределения инспекций, "
                                 "например, утренние инспекции в вечерней раздаче). \n"
                                 "    По результатам тестирования возможно позднее будет добавлена дополнительная раздача."
                                 " Пока контроль за полнотой списка инспекций - за Вами! Претензии не принимаются. Только пожелания\n",
                                 reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer("Регистрация в процессе, если хотите начать заново, нажмите /reg.\nДля завершения "
                                 "начатой регистрации введите фамилию на русском языке (без инициалов)."
                                 " Если возникли другие трудности, обратитесь к владельцу бота")
            my_state_var = 0
        await asyncio.sleep(2)
        await bot.send_message(text=f"Пользователь с id {message.chat.id} с ником {message.from_user.username}, именем {message.from_user.full_name} зашел в чат для подписки",
                               chat_id=config.group_id_list["my_id"])


@dp.message_handler(Text(equals="Отписаться"))  # Хэндлер на команду /start
async def unreg_user_id(message: types.Message):
    global my_state_var
    print(my_state_var)
    if my_state_var == 0:
        await message.answer("    Для удаления регистрации введите Вашу <b>фамилию</b> на русском языке.\n"
                             "    После успешной регистрации Вы будете получать инспекции, закрепленные за Вами "
                             "(за исключением случаев, когда раздача будет производиться до распределения инспекций, "
                             "например, утренние инспекции в вечерней раздаче). \n"
                             "    По результатам тестирования возможно позднее будет добавлена дополнительная раздача."
                             " Пока контроль за полнотой списка инспекций - за Вами\n")
        my_state_var = 5
    else:
        await message.answer("Удаление регистрации в процессе, если хотите начать заново, нажмите /reg.\n"
                             "Для завершения начатой регистрации введите фамилию на русском языке (без инициалов)."
                             " Если возникли другие трудности, обратитесь к владельцу бота")
        my_state_var = 0
    await bot.send_message(text=f"Пользователь с id {message.chat.id} зашел в чат",
                           chat_id=config.group_id_list["my_id"])


@dp.message_handler(commands=["timeout"])  # Хэндлер на команду /start
async def set_message_timeout(message: types.Message):
    my_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    my_buttons = ["Раздача каналам", "Раздача лично" "/timeout"]
    my_keyboard.add(*my_buttons)
    await message.answer("Введите таймаут в сек\n", reply_markup=my_keyboard)
    global my_state_var
    my_state_var = 10


@dp.message_handler(commands=["help"])  # Хэндлер на команду /start
async def user_help(message: types.Message):
    await message.answer("Для получения инспекций по фамилии необходимо подписаться на рассылку. \n"
                         "по подписке Вам могут приходить не все инспекции. Только те, которые распределены.\n"
                         "в начале, в тестовом режиме это будут послеобеденные и ночные инспекции"
                         "для начала работы можете нажать на /start или отправить в чат слово Подписка")



@dp.message_handler(commands=["setup"])  # Хэндлер на команду /start
async def my_ini_setup(message: types.Message):
    if message.chat.id in config.flvb_list:
        try:
            read_conf('company_users', 'users_data.ini')
            await message.answer('стартовый список существует')
        except KeyError:
            create_conf(config.tn_name_dict, 'company_users', 'users_data.ini')
            add_to_my_conf('registered_users', 'users_data.ini')
            add_to_my_conf('unregistered_users', 'users_data.ini')
            await message.answer('стартовый список сотрудников компании создан')



@dp.message_handler(Text(equals="Сотрудник"))  # Хэндлер на команду /start
async def add_company_user(message: types.Message):
    if message.chat.id == int(config.group_id_list["my_id"]):
        global my_state_var
        print(my_state_var)
        if my_state_var == 0:
            my_state_var = 11
            await message.answer("    Для регистрации сотрудника введите <b>фамилию</b> на русском языке с инициалами.\n",
                                 reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer("Регистрация в процессе.")
            my_state_var = 0
        await asyncio.sleep(2)


@dp.message_handler(Text(equals="Список"))  # Хэндлер для получения списка сотрудников
async def list_return(message):
    if message.chat.id in config.flvb_list:
        reg_sett = read_conf('registered_users', 'users_data.ini')
        await message.answer("зарегистрированные сотрудники:\n")
        for i in dict(sorted(reg_sett.items())).keys():
            await message.answer(i.title())


@dp.message_handler(Text(equals="Мысль"))  # Хэндлер на случайную фразу
async def get_idea(message):
    if message.chat.id == int(config.group_id_list["my_id"]):
        keyboard = myboard
        print('my')
    else:
        keyboard = allboard
    await message.answer(get_random_phrase(), reply_markup=keyboard)


@dp.message_handler(commands=["memsetup"])  # Хэндлер на команду /start
async def mem_ini_setup(message: types.Message):
    if message.chat.id == int(config.group_id_list["my_id"]):
        try:
            read_conf('own_mem', 'my_data.ini')
            await message.answer('памятный список существует')
        except KeyError:
            create_conf({'test':'one'}, 'own_mem', 'my_data.ini')
            add_to_my_conf('my_notes', 'my_data.ini')
            add_to_my_conf('my_links', 'my_data.ini')
            await message.answer('стартовый список памяток создан')


@dp.message_handler(Text(equals="Мемка"))  # Хэндлер на команду /start
async def choise_mem_section(message: types.Message):
    if message.chat.id == int(config.group_id_list["my_id"]):
        global my_state_var
        my_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        my_buttons = []
        sections = get_conf_section('my_data.ini')
        for section in sections:
            my_buttons.append(section)
        my_keyboard.add(*my_buttons)
        if my_state_var == 0:
            my_state_var = 41
            await message.answer("Выберите секцию записок\n",
                                 reply_markup=my_keyboard)
    else:
        await message.answer("Функция недоступна\n",
                                 reply_markup=types.ReplyKeyboardRemove())


async def add_my_mem(message: types.Message):
    global my_state_var
    if my_state_var == 0:
            get_conf_section('my_data.ini')
            my_state_var = 44
            await message.answer("Введите название заметки\n",
                                 reply_markup=types.ReplyKeyboardRemove())



@dp.message_handler(Text(equals="Старт сбора"))  # Хэндлер на создание конфига с телефонами
async def make_ee_handbook(message):
    add_to_my_conf('phone_numbers', 'users_data.ini')
    await message.answer('Config phone_numbers added')


@dp.message_handler(Text(equals="Номера"))  # Хэндлер на добавку номеров телефонов
async def add_ee_handbook(message):
    try:
        kiok_data = gen_inspections_df['КиОК']
        kiok_dict = make_handbook(kiok_data)
        print(kiok_dict)
        add_user_to_config(kiok_dict, 'phone_numbers', 'users_data.ini')
        smr_data = gen_inspections_df['Отдел строительства']
        smr_dict = make_handbook(smr_data)
        add_user_to_config(smr_dict, 'phone_numbers', 'users_data.ini')
        await message.answer('Phone numbers updated')
    except:
        pass


@dp.message_handler(Text(equals="Телефон"))  # Хэндлер на поиск телефонов
async def find_phone_number(message):
    if message.chat.id > 0:
        registered_users_dict = read_conf('registered_users', 'users_data.ini')
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Подписка", "Отписаться"]
        keyboard.add(*buttons)
        if str(message.chat.id) in registered_users_dict.values():
            global my_state_var
            await message.answer('Введите фамилию сотрудника для поиска номера телефона: ')
            my_state_var = 21
        else:
            await message.answer("Вы не подписаны\n"
                                 "Телефонная книга доступна только подписанным пользователям"
                                 "Пройдите процедуру подписки",
                                 reply_markup=keyboard)


@dp.message_handler()  # Хэндлер на текстовый ввод
async def message_processor(message: types.Message):
    global my_state_var
    if message.chat.id == int(config.group_id_list["my_id"]):
        keyboard = myboard
        print('my')
    else:
        keyboard = allboard
    if my_state_var == 1:
        await message.answer("Сейчас проверю фамилию на наличие в списке сотрудников\n")
        my_state_var = 2
        if read_conf('company_users', 'users_data.ini').get(message.text.lower()):
            await message.answer("Вы в списке сотрудников, регистрирую\n")
            await bot.send_message(text=f"Пользователь {message.text} с id {message.chat.id} подписался на рассылку",
                                   chat_id=config.group_id_list["my_id"])
            add_user_to_config({message.text: message.chat.id}, 'registered_users', 'users_data.ini')
            await message.answer("Подписка оформлена. После того, как Ваша фамилия появится в списке "
                                 "распределенных инспекций, пришлю Вам сюда шаблоны Ваших инспекций\n"
                                 "Рекомендую отключить звук уведомлений для этого чата",
                                 reply_markup=keyboard)
            my_state_var = 0
        elif config.tn_name_dict.get(message.text.title()):
            await message.answer("Вы в списке сотрудников, регистрирую\n")
            await bot.send_message(text=f"Пользователь {message.text} с id {message.chat.id} подписался на рассылку",
                                   chat_id=config.group_id_list["my_id"])
            add_user_to_config({message.text: message.chat.id}, 'registered_users', 'users_data.ini')
            await message.answer("Подписка оформлена. После того, как Ваша фамилия появится в списке "
                                 "распределенных инспекций, пришлю Вам сюда шаблоны Ваших инспекций\n"
                                 "Рекомендую отключить звук уведомлений для этого чата",
                                 reply_markup=keyboard)
            my_state_var = 0
        else:
            print(read_conf('company_users', 'users_data.ini').get(message.text.lower()))
            await message.answer("Вашу фамилию не нашел в списке  сотрудников, повторите процедуру подписки, проверив "
                                 "верность ввода фамилий, или обратитесь в владельцу бота для проверки списка\n",
                                 reply_markup=keyboard)
            my_state_var = 0
    elif my_state_var == 5:
        await message.answer("Сейчас проверю фамилию на наличие в списке подписанных сотрудников\n")
        my_state_var = 2
        my_sett = read_conf('registered_users', 'users_data.ini')
        if my_sett.get(message.text.lower()):
            await message.answer("Ваша подписка удалена\n", reply_markup=keyboard)
            del_user_from_config(message.text, 'registered_users', 'users_data.ini')
            my_state_var = 0
        else:
            print(read_conf('registered_users', 'users_data.ini').keys())
            await message.answer('Вы не подписаны. Либо /unreg заново и проверьте правильность ввода фамилии')
    elif my_state_var == 10:
        global mess_time_out
        try:
            int(message.text)
            mess_time_out = int(message.text)
            await message.answer(f"Установлен таймаут {mess_time_out} сек\n")
            my_state_var = 0
        except ValueError:
            await message.answer("Введено некорректное значение, введите целое число секунд\n")
    elif my_state_var == 11:
        user_full_name = message.text
        user_short_name = user_full_name.split(sep=' ')[0]
        add_user_to_config({user_short_name: user_full_name}, 'company_users', 'users_data.ini')
        await message.answer(f"Добавлен сотрудник {user_full_name}\n",
                             reply_markup=keyboard)
        my_state_var = 0
    elif my_state_var == 21:
        phone_numbers_dict = read_conf('phone_numbers', 'users_data.ini')
        if re.search(message.text.lower(), str(list(phone_numbers_dict.keys()))):
            for employers_name, employers_phone in phone_numbers_dict.items():
                if re.search(message.text.lower(), employers_name):
                    await message.answer(f'{employers_name.title()}: {employers_phone}')
                    await asyncio.sleep(1)
        else:
            await message.answer('По такой фамилии сотрудник не найден', reply_markup=keyboard)
        my_state_var = 0
    elif my_state_var == 41:
        global mem_section
        mem_section = message.text
        await message.answer('Введите название заметки', reply_markup=types.ReplyKeyboardRemove())
        my_state_var = 44
    elif my_state_var == 44:
        global mem_name
        mem_name = message.text
        await message.answer('Введите заметку', reply_markup=types.ReplyKeyboardRemove())
        my_state_var = 45
    elif my_state_var == 45:
        mem_text = message.text
        add_user_to_config({mem_name: mem_text}, mem_section, 'my_data.ini')
        await message.answer(f"Добавлена заметка {mem_name}\n",
                             reply_markup=keyboard)
        my_state_var = 0

    elif my_state_var == 0:
        pass
    else:
        my_state_var = 0


if __name__ == "__main__":
    try:
        executor.start_polling(dp)
    except (Exception,):
        print('_____task is running_____')