import logging
import telebot
import json
from difflib import SequenceMatcher

# Телеграм бот FAQ

API_TOKEN = 'TG_BOT_TOKEN'
bot = telebot.TeleBot(API_TOKEN)

# Переменная вызова оператора
rage_count = 0
# юзер айди оператора
operator_user_id = []
# статус пользователя
states = {}
# юзер айди пользователя, попавшего в сеанс к оператору
# qa_chat_id = []
# Установка уровня логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка FAQ данных из json файла
with open('FAQ.json', 'r') as f:
    data = json.load(f)


# вычислиение совпадение строк для вопросов в базе и пользователя
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# изменение статуса чата для создания сеанса с оператором
def to_operator(chat_id):
    global bot, states
    # qa_chat_id
    # qa_chat_id.append(chat_id)
    bot.send_message(chat_id, 'Введите ваш вопрос оператору:')
    states[chat_id] = "wait_question"


# отправка сообщения пользователя оператору
@bot.message_handler(func=lambda message: states.get(message.chat.id) == "wait_question")
def q_to_opertor(message):
    global operator_user_id, states
    # qa_chat_id
    user_message = message.text
    logger.info(
        f"Пользователь {message.from_user.first_name} отправил оператору {operator_user_id} сообщение {user_message}")
    bot.send_message(operator_user_id[0], f"{message.chat.id} {user_message}")


# отправка ответа оператора пользователю
@bot.message_handler(func=lambda message: states.get(message.chat.id) == "wait_answers")
def operator_a_to_user(message):
    # выключение режима оператора
    if message.text == '/oper_stop':
        bot.send_message(operator_user_id[-1], f'Ваше общение с пользователями прекратилось'
                                               f', вы вышли из режима оператора')
        logger.info(
            f"Оператор {message.chat.id} перестал быть оператором")
        states[int(operator_user_id[-1])] = ''
        return
    # проверка полученого user id
    try:
        qa_chat_id = str(message.reply_to_message.text[0:10])
        # int(qa_chat_id)
        if len(qa_chat_id) != 10:
            bot.send_message(operator_user_id[-1], 'Вы не ответили пользователю на сообщение, выберите сообщение'
                                                   'пользователя и напишите ответ')
            return
    except AttributeError:
        bot.send_message(operator_user_id[-1], 'Вы не ответили пользователю на сообщение, выберите сообщение'
                                               'пользователя и напишите ответ')
        return
    except ValueError:
        bot.send_message(operator_user_id[-1], 'Вы ответили на свое же сообщение, выберите сообщение'
                                               'пользователя и напишите ответ')
        return
    # отключение пользователя от сеанса общения с оператором
    if message.text == '/a_stop':
        logger.info(
            f"Оператор {message.chat.id} завершил сеанс с {qa_chat_id}")
        states[int(qa_chat_id)] = ''
        print(states)
        bot.send_message(qa_chat_id, "Ваше общение с оператором прекратилось, оператор завершил сеанс")
        return
    logger.info(
        f"Оператор {message.from_user.first_name} отправил пользователю {qa_chat_id} сообщение {message.text}")
    bot.send_message(qa_chat_id, message.text)


# становление оператором
@bot.message_handler(commands=['operator'])
def start_operator_mode(message):
    global operator_user_id
    logger.info(
        f"Пользователь {message.from_user.first_name} стал оператором")
    operator_user_id.append(message.from_user.id)
    bot.send_message(message.chat.id, '🔑 Вы авторизованы как Оператор поддержки,'
                                      ' ожидайте сообщений пользователей.'
                                      '\nДля отправки ответа выбирайте сообщение пользователя и нажмите ответить'
                                      ', только потом отправляйте ответ')
    states[message.chat.id] = "wait_answers"


# /start приветсвие
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"Пользователь {message.from_user.first_name} начал диалог с ботом.")
    bot.reply_to(message, "Привет! Я бот, который поможет вам найти ответ на ваш вопрос в области кулинарии.")
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    for key, value in data.items():
        keyboard.add(telebot.types.KeyboardButton(key))
    bot.send_message(message.chat.id, 'Введите ваш вопрос для поиска в базе FAQ:', reply_markup=keyboard)


# Обработка вопроса пользователя
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    global rage_count, operator_user_id
    user_message = message.text
    # максимальная схожесть строк
    max_similarity = 0
    # ответ на вопрос
    response = None
    # список ответов для клавиатуры
    q_list = []
    # cписок строк с намеком вызвать оператора
    operator_call = []
    with open('./operator_calling.txt') as file:
        for line in file:
            operator_call.append(line.rstrip())

    # Похоже ли сообщение пользователя на желание вызвать оператора
    for i in operator_call:
        if similar(user_message, i) > 0.6:
            to_operator(message.chat.id)
            logger.info(
                f"Пользователь {message.from_user.first_name} отправил сообщение похожее на призыв оператора"
                f"\n открылась сессия с оператором")
            return

    # Похоже ли сообщение пользователя на строку "оператор"
    if similar(user_message, 'оператор') > 0.6:
        rage_count = rage_count + 1
        if rage_count == 3:
            to_operator(message.chat.id)
            rage_count = 0
            logger.info(
                f"Пользователь {message.from_user.first_name} {rage_count} отправлял строку \"оператор\" "
                f"\n открылась сессия с оператором")
            return

    # Указал ли пользователь явно, что его вопрос в списке отсуствует
    if user_message == 'Здесь отсуствуют варианты вопросов которые меня интересуют':
        to_operator(message.chat.id)
        logger.info(
            f"Пользователь {message.from_user.first_name} явно указал, что его вопроса нет в списке,"
            f"\n открылась сессия с оператором")
        return

    # Выявление максимальной схожести вопросов пользователя с базой вопросов
    for key, value in data.items():
        similarity = similar(user_message, key)
        if similarity >= max_similarity:
            max_similarity = similarity
            response = value
            print(key, similarity)

    # Если сообщение полностью совпадает - пользователь получает ответ из базы
    if max_similarity > 0.9:
        logger.info(f"Пользователь {message.from_user.first_name} задал вопрос: {user_message}. Ответ: {response}")
        bot.reply_to(message, response)

    # Если есть похожие сообщения (большая вероятность) - пользователь получает список в клавиатуре из похожих вопросов
    elif max_similarity > 0.6:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
        for key, value in data.items():
            if similar(user_message, key) > 0.6:
                q_list.append(telebot.types.KeyboardButton(key))
        q_list.reverse()
        for i in q_list:
            keyboard.add(i)
        # keyboard.reverse()
        keyboard.add('Здесь отсуствуют варианты вопросов которые меня интересуют')
        logger.info(
            f"Пользователь {message.from_user.first_name} задал вопрос: {user_message}. "
            f"Бот предложил варианты ответов повышенной верности кол-во вариантов {len(q_list)}.")
        bot.send_message(message.chat.id, 'Выберите похожее сообщение:', reply_markup=keyboard)

    # Если есть похожие сообщения (меньшая вероятность) - пользователь получает список в клавиатуре из похожих вопросов
    elif max_similarity > 0.4:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
        for key, value in data.items():
            if similar(user_message, key) > 0.4:
                q_list.append(telebot.types.KeyboardButton(key))
        q_list.reverse()

        for i in q_list:
            keyboard.add(i)

        keyboard.add('Здесь отсуствуют варианты вопросов которые меня интересуют')
        logger.info(
            f"Пользователь {message.from_user.first_name} задал вопрос: {user_message}. "
            f"Бот предложил варианты ответов пониженной верности кол-во вариантов {len(q_list)}.")
        bot.send_message(message.chat.id, 'Выберите похожее сообщение:', reply_markup=keyboard)

    else:  # Если нет похожих сообщений
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
        for key, value in data.items():
            keyboard.add(telebot.types.KeyboardButton(key))
        keyboard.add('Здесь отсуствуют варианты вопросов которые меня интересуют')
        logger.info(
            f"Пользователь {message.from_user.first_name} задал вопрос: {user_message}. "
            f"Бот не смог найти ответ, кол-во вариантов {len(q_list)}.")
        bot.send_message(message.chat.id, 'Извините, но я не могу найти ответ на ваш вопрос. Пожалуйста, '
                                          'выберите в списке \"Здесь отсуствуют варианты вопросов которые меня '
                                          'интересуют\".',
                         reply_markup=keyboard)


bot.polling()
