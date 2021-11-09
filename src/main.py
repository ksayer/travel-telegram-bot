import telebot
from telebot import ExceptionHandler
from decouple import config
from src.botrequests import lowprice
from src.botrequests import highprice
from src.botrequests import bestdeal
from telebot import types
from typing import List
from src.botrequests import history
import configs

RAPIDAPI_KEY = config('RAPIDAPI_KEY')
BOT_TOKEN = config('TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
headers: dict = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': RAPIDAPI_KEY
}


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: types.Message):
    bot.send_message(message.chat.id, "Привет. Я помогу тебе найти отель. Команды:"
                                      "\n/help - помощь по командам бота"
                                      "\n/lowprice - вывод самых дешевых отелей в городе"
                                      "\n/highprice - вывод самых дорогих отелей в городе"
                                      "\n/bestdeal - вывод отелей, наиболее подходящих по цене и расположению от центра"
                                      "\n/history - вывод истории поиска отелей")


@bot.message_handler(commands=['lowprice'])
def send_low_price_hotels(message):
    """
    Спрашиваем у пользователя в какой город он собирается поехать и переходим к функции запроса кол-ва отелей.
    В эту функцию передаем город и команду которую запросил пользователь
    """
    id_user = message.from_user.id
    date_create = history.create_user(id_user, 'lowprice')
    city: types.Message = bot.send_message(message.chat.id, 'Где ищем?')
    bot.register_next_step_handler(city, check_city, date_create)


@bot.message_handler(commands=['highprice'])
def send_high_price_hotels(message):
    """
    Спрашиваем у пользователя в какой город он собирается поехать и переходим к функции запроса кол-ва отелей.
    В эту функцию передаем город и команду которую запросил пользователь
    """
    id_user = message.from_user.id
    date_create = history.create_user(id_user, 'highprice')
    city: types.Message = bot.send_message(message.chat.id, 'Где ищем?')
    bot.register_next_step_handler(city, check_city, date_create)


@bot.message_handler(commands=['bestdeal'])
def send_high_price_hotels(message):
    """
    Спрашиваем у пользователя в какой город он собирается поехать и переходим к функции запроса кол-ва отелей.
    В эту функцию передаем город и команду которую запросил пользователь
    """
    id_user = message.from_user.id
    date_create = history.create_user(id_user, 'bestdeal')
    city: types.Message = bot.send_message(message.chat.id, 'Где ищем?')
    bot.register_next_step_handler(city, check_city, date_create)


@bot.message_handler(commands=['history'])
def send_history(message):
    """
    Выдаем результат последних 3 запросов (история)
    """


def check_city(message: types.Message, date_create):
    """
    Парсим по запрошенному город и предлагаем пользователю выбрать из всех совпадений которые найдены в API
    В cities у нас находится список [[full_city_name, id_city], [full_city_name, id_city], [full_city_name, id_city]..]
    В callback передаваемые данных передаем id города, который выбрал пользователь
    :param message: запрошенный город
    """

    cities_button = types.InlineKeyboardMarkup()
    city = message.text
    cities = lowprice.check_city(city)
    for city in cities:
        data = '|'.join([city[1], date_create])
        history.create_city(city[0], city[1])
        button = types.InlineKeyboardButton(text=city[0], callback_data=data)
        cities_button.add(button)
    bot.send_message(message.chat.id, 'Выберите город:', reply_markup=cities_button)


@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    """
    Ловим нажатие пользователя на кнопку!
    Тут мы записываем окончательный выбор города в БД (id и имя) и переходим к функции кол-ва отелей
    В завимимости от команды пользователя отправляем в следующую функцию
    :return:
    """
    data = call.data.split('|')
    date_create = data[1]
    id_city = data[0]
    city = history.get_city(data[0])
    history.set_city_user(id_city, city, call.message.chat.id, date_create)
    bot.send_message(call.message.chat.id, 'Ты выбрал:\n{}'.format(city))
    if history.get_command(call.message.chat.id, date_create) == 'bestdeal':
        ask_price(call.message.chat.id, date_create)
    else:
        ask_number_hotels(call.message.chat.id, date_create)


def ask_price(id_user, date_create):
    """
    Спрашиваем у пользователя диапазон цен и расстояния от центра.
    message переводим в строку и присваиваем его переменной city, чтобы передать в следующую функцию.
    """
    user_price: types.Message = bot.send_message(id_user, 'Введите диапазон цен (в рублях), '
                                                          'например - "500 2500" ')
    bot.register_next_step_handler(user_price, ask_distance, date_create)


def ask_distance(message: types.Message, date_create):
    """
    Создаем список из диапазона цен (минимум и максимум), записываем в БД
    Спрашиваем у пользователя диапазон дистанции.
    Потом переходим в функцию запроса кол-ва отелей
    :param message: диапазон цен пользователя
    """
    try:
        prices = message.text.split(' ')

        history.set_price(prices, message.chat.id, date_create)
        user_distance: types.Message = bot.send_message(message.chat.id, 'Введите диапазон расстояния от центра '
                                                                         'в километрах, напрмер - "0.5 2"')
        bot.register_next_step_handler(user_distance, check_distance, date_create)
    except (IndexError, SyntaxError, ValueError):
        ask_price(message.chat.id, date_create)


def check_distance(message: types.Message, date_create):
    """
    Проверяем, что ввел пользователь в диапазоне расстояний и записываем в БД. Переходим на запрос кол-ва отелей
    :param message:
    :return:
    """
    try:
        distances = message.text.split(' ')
        history.set_distance(distances, message.chat.id, date_create)
        ask_number_hotels(message.chat.id, date_create)
    except (IndexError, SyntaxError, ValueError):
        user_distance: types.Message = bot.send_message(message.chat.id, 'Введите диапазон расстояния от центра '
                                                                         'в километрах, напрмер - "0.5 2"')
        bot.register_next_step_handler(user_distance, check_distance)


def ask_number_hotels(id_user, date_create):
    """
    Переводим город в строку. И в зависимости от того какая у нас команда, вызывает функцию, которая вернет список
    отелей в городе.
    Спращиваем у пользователя сколько отелей вывести в результате. Переходим к функции вывода результата в которую
    передаем кол-во отелей, список отелей, команду
    :param id_user:
    """

    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                         resize_keyboard=True,
                                         input_field_placeholder='не более 9 отелей')
    keyboard.row('1', '2', '3')
    keyboard.row('4', '5', '6')
    keyboard.row('7', '8', '9')
    count_of_hotels: types.Message = bot.send_message(id_user, 'Сколько отелей вывести в результат?',
                                                      reply_markup=keyboard)
    bot.register_next_step_handler(count_of_hotels, ask_photo, date_create)


def ask_photo(message: types.Message, date_create):
    """
    Проверяем кол-во запрошенное пользователем, если оно больше разрешенного, то принудительно меняем
    Спрашиваем у пользователя, нужны ли ему фотографии.
    Если пользователь введет не число, то его вернет на шаг назад.
    :param message:
    :return:
    """
    try:
        count_of_hotels = int(message.text)
        if count_of_hotels > configs.count_of_hotels:
            count_of_hotels = configs.count_of_hotels
        history.set_count_of_hotels(message.chat.id, count_of_hotels, date_create)
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                             resize_keyboard=True,
                                             input_field_placeholder='да/нет')
        keyboard.row('да', 'нет')
        photo_desire: types.Message = bot.send_message(message.chat.id, 'Хотите увидеть фотографии отелей?',
                                                       reply_markup=keyboard)
        bot.register_next_step_handler(photo_desire, ask_number_photo, date_create)
        types.ReplyKeyboardRemove()
    except ValueError:
        bot.reply_to(message, 'Это должно быть число. Попробуйте еще раз.')
        ask_number_hotels(message.chat.id, date_create)


def ask_number_photo(message: types.Message, date_create):
    """
    Проверяем хочет ли пользователь увидеть фотографии. Есди нет, то переходим к выводу результата без переменной photo,
     если да - то передаем в ту же функцию photo = True

    :param user: объект пользователь
    :param message: ответ на "хотите увидеть фотографии?"
    """

    if message.text.lower() == 'нет':
        history.set_photo(message.chat.id, False, date_create)
        history.set_count_of_photo(message.chat.id, 0, date_create)
        show_result(message.chat.id, date_create)
    elif message.text.lower() == 'да':
        history.set_photo(message.chat.id, True, date_create)
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                             resize_keyboard=True,
                                             input_field_placeholder='не более 6 фотографий')
        keyboard.row('1', '2', '3')
        keyboard.row('4', '5', '6')
        number_photo: types.Message = bot.reply_to(message, 'Сколько?', reply_markup=keyboard)
        bot.register_next_step_handler(number_photo, check_count_of_photo, date_create)
    else:
        photo_desire: types.Message = bot.reply_to(message, 'Введите "да" или "нет"')
        bot.register_next_step_handler(photo_desire, ask_number_photo, date_create)


def check_count_of_photo(message: types.Message, date_create):
    count_of_photo = message.text

    if (count_of_photo.isdigit() and history.get_photo(message.chat.id, date_create)) or \
            (count_of_photo == 'нет' and not history.get_photo(message.chat.id, date_create)):
        if count_of_photo.isdigit() and int(count_of_photo) > configs.count_of_photo:
            count_of_photo = configs.count_of_photo
        history.set_count_of_photo(message.chat.id, count_of_photo, date_create)
        bot.send_message(message.chat.id, 'Обзваниваю отели. Подождите, пожалуйста',
                         reply_markup=types.ReplyKeyboardRemove())
        show_result(message.chat.id, date_create)
    else:
        number_photo: types.Message = bot.reply_to(message, 'Введите число!')
        bot.register_next_step_handler(number_photo, check_count_of_photo, date_create)


def show_result(id_user, date_create):
    """
    Если нужны фотографии и пользователь ввел число на вопрос "сколько?" - то выводим результат, если он ввел не число
    то ему придет еще один запрос на кол-во фотографий, пока он не введет число.
    Если пользователь ввел кол-во фотографий больше допустимого - принудительно меняем это число

    :param message: если фотографии нужны тот тут кол-во фоторгафий, если они не нужны тот тут "нет"
    """
    if history.get_command(id_user, date_create) == 'lowprice':
        lowprice.get_hotels_info(id_user, date_create)
    elif history.get_command(id_user, date_create) == 'highprice':
        highprice.get_hotels_info(id_user, date_create)
    else:
        bestdeal.get_hotels_info(id_user, date_create)
    hotels = history.get_hotels(id_user, date_create)
    for hotel in hotels:
        media_group = history.create_media_group(hotel['photo'])
        if history.get_photo(id_user, date_create):
            bot.send_media_group(id_user, media_group)

        link_booking = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='Забронировать номер', url=hotel['booking'])
        link_booking.add(button)

        bot.send_message(id_user, 'Название отеля: {name}\n'
                                  'Адрес: {address}\n'
                                  'Расстояние до центра: {dist}\n'
                                  'Цена: {price}'.format(name=hotel['name'],
                                                         address=hotel['addres'],
                                                         dist=hotel['distance_to_center'],
                                                         price=hotel['price']),
                         reply_markup=link_booking)
    bot.send_message(id_user, 'Найдено отелей: {}'.format(len(hotels)))


@bot.message_handler(func=lambda message: True)
def dont_understand(message: types.Message):
    bot.reply_to(message, "Я вас не понимаю, введите /help для помощи")


# def main():
#     try:
#         bot.polling(none_stop=True)
#     except Exception:
#         main()
#
#
# if __name__ == '__main__':
#     main()

bot.infinity_polling()