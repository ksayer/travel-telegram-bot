import sqlite3
import datetime
import re
from typing import List
from telebot import types

from src import configs

connect = sqlite3.connect('database.db', check_same_thread=False)
cursor = connect.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users("
               "id_user INTEGER NOT NULL,"
               "command TEXT,"
               "date_create TEXT,"
               "city TEXT,"
               "id_city INTEGER,"
               "count_of_hotels INTEGER,"
               "photo bool,"
               "count_of_photo INTEGER,"
               "top_price TEXT,"
               "lower_price TEXT,"
               "top_dist TEXT,"
               "lower_dist TEXT,"
               "hotels TEXT, "
               "completed INTEGER,"
               "check_in TEXT,"
               "check_out TEXT,"
               "days TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS cities(id_city TEXT, city TEXT)")


def create_user(id_user: int, command: str) -> str:
    """
    Создаем запись в БД.
    :param id_user: id пользователя
    :param command: комманда введенная пользователем
    """
    datetime_now: datetime.datetime = datetime.datetime.now()
    date: str = datetime_now.strftime('%H:%M:%S - %d.%m.%Y')
    sql: str = "INSERT INTO users(id_user, command, date_create) VALUES(?, ?, ?)"

    cursor.execute(sql, (id_user, command, date))
    connect.commit()

    return date


def get_command(id_user: int, date_create: str) -> str:
    """
    Возвращаем из БД команду пользователя
    :return: str команда
    """
    cursor.execute("SELECT command FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    command: tuple[str] = cursor.fetchone()

    return command[0]


def create_city(city: str, id_city: str) -> None:
    """
    Создаем запись в таблице cities. Если такой город уже есть в БД, то ничего не делаем
    :param city: название города
    :param id_city: id города
    """
    cursor.execute("SELECT id_city FROM cities WHERE id_city=?", (id_city,))
    if not cursor.fetchone():
        sql: str = "INSERT INTO cities(id_city, city) VALUES(?, ?)"
        cursor.execute(sql, (id_city, city))
        connect.commit()


def get_city(id_city: str) -> str:
    """
    По id Города возвращаем из базы его полное название
    :return: название города
    """
    cursor.execute("SELECT city FROM cities WHERE id_city=?", (id_city,))
    city: tuple[str] = cursor.fetchone()

    return city[0]


def set_count_of_hotels(id_user: int, count_of_hotels: int, date_create: str) -> None:
    """
    Записываем в БД кол-во отелей пользователя
    """
    sql: str = "UPDATE users SET count_of_hotels=? WHERE id_user=? and date_create=?"
    cursor.execute(sql, (count_of_hotels, id_user, date_create))
    connect.commit()


def set_photo(id_user: int, photo: bool, date_create: str) -> None:
    """
    Записываем в БД нужны ли пользователю фотографии
    """
    sql: str = "UPDATE users SET photo=? WHERE id_user=? and date_create=?"
    cursor.execute(sql, (photo, id_user, date_create))
    connect.commit()


def set_count_of_photo(id_user: int, count_of_photo: [int, str], date_create: str) -> None:
    """
    Записываем в БД сколько фотографий нужно пользователю
    """
    if count_of_photo == 'нет':
        count_of_photo = 0
    sql: str = "UPDATE users SET count_of_photo=? WHERE id_user=? and date_create=?"
    cursor.execute(sql, (count_of_photo, id_user, date_create))
    connect.commit()


def set_city_user(id_city: str, city: str, id_user: int, date_create: str) -> None:
    """
    Записываем в таблицу users город и id города
    """
    sql: str = "UPDATE users SET id_city=?, city=? WHERE id_user=? and date_create=?"
    cursor.execute(sql, (id_city, city, id_user, date_create))
    connect.commit()


def get_count_of_photo(id_user: int, date_create: str) -> int:
    """
    По id пользователя кол-во фотографий
    :return: str команда
    """
    cursor.execute("SELECT count_of_photo FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    count_of_photo: tuple[int] = cursor.fetchone()

    return count_of_photo[0]


def get_count_of_hotels(id_user: int, date_create: str) -> int:
    """
    По id пользователя кол-во отелей
    :return: str команда
    """
    cursor.execute("SELECT count_of_hotels FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    count_of_hotels: tuple[int] = cursor.fetchone()

    return count_of_hotels[0]


def get_id_city_user(id_user: int, date_create: str) -> int:
    """
    По id пользователя id города
    :return: str команда
    """
    cursor.execute("SELECT id_city FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    id_city: tuple[int] = cursor.fetchone()

    return id_city[0]


def get_photo(id_user: int, date_create: str) -> bool:
    """
    По id пользователя нужно фото или нет
    :return: str команда
    """
    cursor.execute("SELECT photo FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    photo: tuple[bool] = cursor.fetchone()

    return photo[0]


def set_price(prices: List[str], id_user: int, date_create: str) -> None:
    """
    Записываем в БД нижнюю и верхнюю цены. Если пользователь ввел не 2 числа - выдаем исключение
    Если пользователь - камень, поменяем местами цены

    :param date_create: Дата ввода команды
    :param prices: цены в списке, 0 - нижняя, 1 - верхняя
    :param id_user: id пользователя
    """
    if len(prices) > 2:
        raise ValueError

    lower_price = abs(int(float(re.sub(',', '.', prices[0]))))
    top_price = abs(int(float(re.sub(',', '.', prices[1]))))

    if lower_price > top_price:
        lower_price, top_price = top_price, lower_price

    sql = "UPDATE users SET lower_price=?, top_price=? WHERE id_user=? and date_create=?"
    cursor.execute(sql, (lower_price, top_price, id_user, date_create))
    connect.commit()


def set_distance(distances: List[str], id_user: int, date_create: str) -> None:
    """
    Записываем в БД нижнюю и верхнюю цены. Если пользователь ввел не 2 числа - выдаем исключение
    Если пользователь - камень, поменяем местами расстояния
    :param date_create: Дата ввода команды
    :param id_user: id пользователя
    :param distances: расстояния в списке, 0 - нижнее, 1 - верхнее
    """
    if len(distances) > 2:
        raise ValueError

    lower_distance: float = abs(float(re.sub(',', '.', distances[0])))
    top_distance: float = abs(float(re.sub(',', '.', distances[1])))

    if lower_distance > top_distance:
        lower_distance, top_distance = top_distance, lower_distance

    sql: str = "UPDATE users SET lower_dist=?, top_dist=? WHERE id_user=? and date_create=?"
    cursor.execute(sql, (lower_distance, top_distance, id_user, date_create))
    connect.commit()


def get_price(id_user: int, date_create: str) -> tuple[int]:
    """
    По id пользователя возвращаем кортеж из границ цен
    """
    cursor.execute("SELECT lower_price, top_price FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    prices: tuple[int] = cursor.fetchone()

    return prices


def get_distance(id_user: int, date_create: str) -> tuple[int]:
    """
    По id пользователя возвращаем кортеж из границ дистанции от центра
    """
    cursor.execute("SELECT lower_dist, top_dist FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    distances: tuple[int] = cursor.fetchone()

    return distances


def set_hotels(id_user: int, hotels: List[dict], date_create: str) -> None:
    """
    Записываем в БД все отели которые нашли по этой команде (преобразуем список в строку, чтобы записать в БД)
    """
    hotels = str(hotels)
    cursor.execute("UPDATE users SET hotels=? WHERE id_user=? and date_create=?", (hotels, id_user, date_create))
    cursor.execute("UPDATE users SET completed=? WHERE id_user=? and date_create=?", ('1', id_user, date_create))
    connect.commit()


def get_hotels(id_user: int, date_create: str) -> List[dict]:
    """
    По id пользователя и date_create возвращаем отели, которые были найдены
    """
    cursor.execute("SELECT hotels FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    hotels: tuple[str] = cursor.fetchone()
    hotels: List = eval(hotels[0])
    return hotels


def create_media_group(photos: List[str]) -> List[types.InputMediaPhoto]:
    """
    Возвращаем список объектов фотографий для бота из списка строк
    :param photos: Список адресов с фотографиями
    """
    media_group: List = []
    for photo in photos:
        media_group.append(types.InputMediaPhoto(photo))

    return media_group


def send_history(id_user: int) -> [List, bool]:
    """
    Возвращаем историю пользователя. Делаем запрос необходимых данных, делаем срез только последних number_stories(файл
    configs.py) историй. Список отелей хранится строкой, поэтому при помощи функции eval преобразуем в список только
    отели(индекс 2), если список пустой, то вылетит исключение TypeError. В конец записи единицц запроса истории
    добавляем голое время запроса(276 строка), чтобы можно было в будущем использовать его для повторного вывода
    результата
    """
    sql: str = "SELECT command, date_create, hotels, city, completed FROM users WHERE id_user=?"
    cursor.execute(sql, (id_user,))
    history: List[tuple] = cursor.fetchall()

    if len(history) == 0:
        return False
    history: List[tuple] = history[-configs.number_stories:]
    text_for_send: List = []
    for story in history:
        if not story[4]:
            continue
        command: str = 'Команда: {}'.format(story[0])
        date_create: str = 'Время: {}'.format(story[1])
        city: str = 'Город: {}'.format(story[3])
        text: List[str] = [command, '\n', date_create, '\n', city, '\n']
        try:
            for hotel in eval(story[2]):
                name_hotel: str = ''.join([hotel['name'], '\n'])
                text.append(name_hotel)
        except TypeError:
            text.append('Отелей не найдено')
        text.append(story[1])
        text_for_send.append(text)

    return text_for_send


def delete_last_story(id_user: int) -> None:
    """
    Удаляем запись в БД, Сначала вытаскиаем все записи, потом берем последнюю в списке - она же будет последней по
    времени. Берем время, создаем запрос на удаление и удаляем
    """

    sql = "SELECT date_create FROM users WHERE id_user=?"
    cursor.execute(sql, (id_user,))

    date_tuple = cursor.fetchall()
    date_create = date_tuple[-1][0]

    sql_delete = "DELETE FROM users WHERE id_user=? and date_create=?"
    cursor.execute(sql_delete, (id_user, date_create))

    connect.commit()


def check_completed(id_user: int) -> [None, bool]:
    """
    Проверяем пройдена ли вся цепочка вопросов в последнем запросе пользователя. Сначала берем все записи пользователя,
    потом берем последнюю запись из этого списка и из кортежа тащим первый элемент[0}
    """

    sql = "SELECT completed FROM users WHERE id_user=?"
    cursor.execute(sql, (id_user,))

    city_tuple = cursor.fetchall()
    city_create = city_tuple[-1][0]

    if city_create:
        return True
    return False


def set_dates(id_user: int, date_create: str, dates: str):
    """
    Записываем в БД даты заезда и выезда из отеля.
    :param date_create: Дата ввода команды
    :param id_user: id пользователя
    :param dates: Дата въезда и дата выезда
    """
    try:
        full_pattern = r'(\d{4}[.,/\;:-]\d{2}[.,/\;:-]\d{2}) +(\d{4}[.,/\;:-]\d{2}[.,/\;:-]\d{2})'
        pattern_for_one_date = r'[.,/\;:]'
        check_full_string = re.search(full_pattern, dates)
        today = datetime.date.today()
        if check_full_string:
            check_in = check_full_string[1]
            check_out = check_full_string[2]
            check_in = re.sub(pattern_for_one_date, '-', check_in)
            check_out = re.sub(pattern_for_one_date, '-', check_out)
            date_check_in = datetime.datetime.strptime(check_in, '%Y-%m-%d')
            date_check_out = datetime.datetime.strptime(check_out, '%Y-%m-%d')
            days = (date_check_out - date_check_in).days
            if date_check_in > date_check_out:
                return 'Введите сперва дату заезда, а потом дату выезда'
            elif not date_check_in > date_check_out and not date_check_in < date_check_out:
                return 'Дата заезда и выезда должны отличаться'
            elif today > date_check_in.date():
                return 'Делориан в ремонте, в прошлом бронировать не получится'
            else:
                sql = "UPDATE users SET check_in=?, check_out=?, days=? WHERE id_user=? and date_create=?"
                cursor.execute(sql, (check_in, check_out, days, id_user, date_create))
                connect.commit()
        else:
            return 'Некорректный ввод'
    except ValueError:
        return 'Некорректная дата'


def get_dates(id_user: int, date_create: str) -> tuple[str]:
    """
    По id пользователя возвращаем кортеж из границ дистанции от центра
    """
    cursor.execute("SELECT check_in, check_out FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    dates: tuple[str] = cursor.fetchone()

    return dates


def get_days(id_user: int, date_create: str) -> int:
    """
    Возвращает кол-во дней, на которое бронируется отель
    """
    cursor.execute("SELECT days FROM users WHERE id_user=? and date_create=?", (id_user, date_create))
    days = cursor.fetchone()
    return int(days[0])