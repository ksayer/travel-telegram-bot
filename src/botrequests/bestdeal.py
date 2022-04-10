import requests
import json
import re
from decouple import config
from typing import List, Optional

from src.botrequests import history
from src import configs


RAPIDAPI_KEY: str = config('RAPIDAPI_KEY')

headers: dict = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': RAPIDAPI_KEY
    }


def delete_span(string: str) -> str:
    """
    Удаляем из строки города HTML элементы из строки
    :param string: строка из которой нужно убрать лишнее
    :return:
    """
    pattern_1: str = r"<span class='highlighted'>"
    pattern_2: str = r"</span>"
    repl: str = ''

    res_1: str = re.sub(pattern_1, repl, string)
    res_2: str = re.sub(pattern_2, repl, res_1)

    return res_2


def check_city(city: str) -> List[List[str]]:
    """
    Делаем запрос и проверяем, все результаты ([имя города, id Города]) с type: 'CITY' записываем в список list_cities
    :param city: Город который ввел пользователь
    :return: Города, которые совпали в написании с тем, что запросил пользователь
    """
    url: str = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring: dict = {"query": city, "locale": "ru_RU", "currency": "RUB"}

    response_city_id: json = requests.request("GET", url,
                                              headers=headers,
                                              params=querystring,
                                              timeout=configs.time_out)
    data: json = json.loads(response_city_id.text)

    entities: List[dict] = data['suggestions'][0]['entities']
    list_cities: List = []

    for entity in entities:
        if entity['type'] == 'CITY':
            full_name: str = delete_span(entity['caption'])
            list_cities.append([full_name, entity['destinationId']])

    return list_cities


def get_properties_list(id_user: int, page_number: int, date_create: str) -> List[dict]:
    """
    Парсим API для по городу, границам цен.
    В зависимости от верхней границы расстаяния от центра парсим с разными характеристиками сортировки (если очень
    близко к центру - сортируем по расстоянию от центра (пользователю важнее приближенность к центру чем деньги),
    если далеко от центра (пользователю важнее сэкономить) - сортируем по цене).
    :param date_create: дата ввода команды
    :param page_number: номер страницы вывода списка отелей
    :param id_user: id пользователя
    :return: лист отелей
    """
    distances: tuple[int] = history.get_distance(id_user, date_create)
    prices: tuple[int] = history.get_price(id_user, date_create)
    dates = history.get_dates(id_user, date_create)
    check_in: str = dates[0]
    check_out: str = dates[1]
    url = "https://hotels4.p.rapidapi.com/properties/list"

    if float(distances[1]) <= 2:
        querystring = {"destinationId": history.get_id_city_user(id_user, date_create), "pageNumber": page_number,
                       "pageSize": "25", "checkIn": check_in, "checkOut": check_out, "adults1": "1",
                       "priceMin": prices[0], "priceMax": prices[1], "sortOrder": "DISTANCE_FROM_LANDMARK",
                       "locale": "ru_RU", "currency": "RUB"}
    else:
        querystring = {"destinationId": history.get_id_city_user(id_user, date_create), "pageNumber": page_number,
                       "pageSize": "25", "checkIn": check_in, "checkOut": check_out, "adults1": "1",
                       "priceMin": prices[0], "priceMax": prices[1], "sortOrder": "PRICE", "locale": "ru_RU",
                       "currency": "RUB"}

    response_properties_list: json = requests.request("GET", url,
                                                      headers=headers,
                                                      params=querystring,
                                                      timeout=configs.time_out)
    data: json = json.loads(response_properties_list.text)
    full_list_hotels: List[dict] = data['data']['body']['searchResults']['results']

    return full_list_hotels


def get_photo(id_hotel: str, number: int) -> List[str]:
    """
    Получаем адрес фотографии по ID отеля, в полученной адресе меняем строку {size} на b (размер фотографии).
    Составляем список адресов
    :param number: количество фотографий отеля
    :param id_hotel: id Отеля
    :return: адрес фотографии
    """
    url: str = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring: dict = {"id": id_hotel}
    response_photo: json = requests.request("GET", url, headers=headers, params=querystring, timeout=configs.time_out)
    data: json = json.loads(response_photo.text)

    list_photo: List = []

    for photo in range(int(number)):
        address_photo = data['hotelImages'][photo]['baseUrl']
        address_photo = address_photo.replace('{size}', 'b')
        list_photo.append(address_photo)

    return list_photo


def string_to_number(string: str) -> [int, float]:
    """
    Вытаскивает из строки число, меняет запятую на точку
    :param string: строка которую редактируем
    """
    number: str = ''
    for sym in string:
        if sym == ',':
            number += '.'
        elif sym == ' ':
            break
        else:
            number += sym

    if '.' in number:
        return float(number)

    return int(number)


def get_hotels_info(id_user, date_create, count: int = 0, page_number: int = 1, top=None):
    """
    Сортируем список по цене (сначала дешевые)
    Потом в цикле проверяем каждый отель на соответствие запрошенного расстояния от центра города.
    Далее берем необходимые значения из list_hotels, потом присваиваем их новому словарю. На каждой итерации
    цикла мы добавляем созданный словарь в список top.
    count - счетчик кол-ва добавленных отелей, как только станет равен числу от пользователя - цикл остановится, список
    запишется в БД.
    Если пользователь попросил фотографии, то запросим в функции get_photo.
    """

    if top is None:
        top: List = []
    sorted_list_hotels = sorted(get_properties_list(id_user, page_number, date_create),
                                key=lambda x: int(x['ratePlan']['price']['exactCurrent']))
    distances = history.get_distance(id_user, date_create)
    for hotel in sorted_list_hotels:
        if float(distances[0]) <= string_to_number(hotel['landmarks'][0]['distance']) <= float(distances[1]):
            hotel_info = dict()
            count += 1
            name: str = hotel['name']
            id_hotel: str = str(hotel['id'])
            booking: str = ''.join(['https://ru.hotels.com/ho', id_hotel])
            try:
                address: Optional[str] = hotel['address']['streetAddress']
            except KeyError:
                address: Optional[str] = None
            distance_to_center: str = hotel['landmarks'][0]['distance']
            price: str = hotel['ratePlan']['price']['current']
            days_booking: int = history.get_days(id_user, date_create)
            if days_booking > 1:
                price_for_night = round(float(hotel['ratePlan']['price']['exactCurrent']) / days_booking, 2)
                hotel_info['price_for_night']: str = ' '.join([str(price_for_night), 'RUB'])

            hotel_info['name']: str = name
            hotel_info['address']: str = address
            hotel_info['distance_to_center']: str = distance_to_center
            hotel_info['price']: str = price
            hotel_info['booking']: str = booking
            if history.get_photo(id_user, date_create):
                hotel_info['photo']: List[str] = get_photo(hotel['id'], history.get_count_of_photo(id_user,
                                                                                                   date_create))
            top.append(hotel_info)
            if count == history.get_count_of_hotels(id_user, date_create):
                break

    if page_number == configs.page_number:
        history.set_hotels(id_user, top, date_create)
        return

    if count < history.get_count_of_hotels(id_user, date_create):
        page_number += 1
        get_hotels_info(id_user, date_create, count, page_number, top)

    history.set_hotels(id_user, top, date_create)
