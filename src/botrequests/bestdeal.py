from telebot import types
import requests
import json
from decouple import config
from typing import List, Optional
from datetime import date, timedelta
from src.botrequests import history
import re
from src import configs


RAPIDAPI_KEY = config('RAPIDAPI_KEY')

headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': RAPIDAPI_KEY
    }


def delete_span(string: str):
    pattern_1 = r"<span class='highlighted'>"
    pattern_2 = r"</span>"
    repl = ''
    res_1 = re.sub(pattern_1, repl, string)
    res_2 = re.sub(pattern_2, repl, res_1)
    return res_2


def check_city(city: str):
    """
    Делаем запрос и проверяем, все результаты ([имя города, id Города]) с type: 'CITY' записываем в список list_cities
    :param city:
    :return: List[str]
    """
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": city, "locale": "ru_RU", "currency": "RUB"}
    response_city_id: json = requests.request("GET", url, headers=headers, params=querystring)
    data: json = json.loads(response_city_id.text)
    entities = data['suggestions'][0]['entities']
    list_cities = []
    for entity in entities:
        if entity['type'] == 'CITY':
            full_name = delete_span(entity['caption'])
            list_cities.append([full_name, entity['destinationId']])
    return list_cities


def get_city_id(city):
    """
    Возвращает ID требуемого города
    :return: id
    """
    url = "https://hotels4.p.rapidapi.com/locations/search"
    querystring = {"query": city, "locale": "ru_RU"}
    response_city_id = requests.request("GET", url, headers=headers, params=querystring)
    data_city_id = json.loads(response_city_id.text)
    city_id = data_city_id['suggestions'][0]['entities'][0]['destinationId']
    return city_id


def get_properties_list(id_user, page_number) -> List[dict]:
    """
    Парсим API для по городу, границам цен.
    В зависимости от верхней границы расстаяния от центра парсим с разными характеристиками сортировки (если очень
    близко к центру - сортируем по расстоянию от центра (пользователю важнее приближенность к центру чем деньги),
    если далеко от центра (пользователю важнее сэкономить) - сортируем по цене)
    :param page_number: номер страницы вывода списка отелей
    :param id_user:
    :return: лист отелей
    """
    url = "https://hotels4.p.rapidapi.com/properties/list"
    distances = history.get_distance(id_user)
    prices = history.get_price(id_user)
    today = date.today()
    check_in = str(today + timedelta(days=2))
    check_out = str(today + timedelta(days=3))
    if float(distances[1]) <= 2.5:
        querystring = {"destinationId": history.get_id_city_user(id_user), "pageNumber": str(page_number), "pageSize": "25", "checkIn": check_in,
                       "checkOut": check_out, "adults1": "1", "priceMin": prices[0], "priceMax": prices[1],
                       "sortOrder": "DISTANCE_FROM_LANDMARK", "locale": "ru_RU", "currency": "RUB"}
    else:
        querystring = {"destinationId": history.get_id_city_user(id_user), "pageNumber": "1", "pageSize": "25", "checkIn": check_in,
                       "checkOut": check_out, "adults1": "1", "priceMin": prices[0], "priceMax": prices[1],
                       "sortOrder": "PRICE", "locale": "ru_RU", "currency": "RUB"}
    response_properties_list = requests.request("GET", url, headers=headers, params=querystring)
    data = json.loads(response_properties_list.text)
    data = data['data']['body']['searchResults']['results']
    return data


def get_photo(id_hotel: str, number: str) -> json:
    """
    Получаем адрес фотографии по ID отеля
    :param number: количество фотографий отеля
    :param id_hotel: id Отеля
    :return: адрес фотографии
    """
    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {"id": id_hotel}
    response_photo: json = requests.request("GET", url, headers=headers, params=querystring)
    data: json = json.loads(response_photo.text)
    list_photo = []
    for photo in range(int(number)):
        adrress_photo = data['hotelImages'][photo]['baseUrl']
        adrress_photo = adrress_photo.replace('{size}', 'b')
        list_photo.append(types.InputMediaPhoto(adrress_photo))
    return list_photo


def string_to_number(string: str) -> [int, float]:
    """
    Вытаскивает из строки число, меняет запятую на точку
    :param string: строка состоящая из цифр и букв
    """
    number = ''
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


def get_hotels_info(id_user, count: int = 0, page_number: int = 1, top=None) -> List[dict]:
    """
    Сортируем список по цене (сначала дешевые)
    Потом в цикле проверяем каждый отель на соответствие запрошенного расстояния от центра города.
    Далее берем необходимые значения из list_hotels, потом присваиваем их новому словарю. На каждой итерации
    цикла мы добавляем созданный словарь в список top
    :param top:
    :param page_number: номер страницы вывода списка отелей(для функции get_properties_list)
    :param id_user:
    :param count: кол-во отелей, которые соответствуют условиям
    :return: список словарей отелей с необходимыми характеристиками
    """

    if top is None:
        top = []
    sorted_list_hotels = sorted(get_properties_list(id_user, page_number), key=lambda x: int(x['ratePlan']['price']['exactCurrent']))
    distances = history.get_distance(id_user)
    for hotel in sorted_list_hotels:
        if float(distances[0]) <= string_to_number(hotel['landmarks'][0]['distance']) <= float(distances[1]):
            hotel_info = dict()
            count += 1
            name = hotel['name']
            id_hotel = str(hotel['id'])
            booking = ''.join(['https://ru.hotels.com/ho', id_hotel])
            try:
                address: Optional[str] = hotel['address']['streetAddress']
            except KeyError:
                address: Optional[str] = None
            distance_to_center: str = hotel['landmarks'][0]['distance']
            price: str = hotel['ratePlan']['price']['current']
            hotel_info['name']: str = name
            hotel_info['addres']: str = address
            hotel_info['distance_to_center']: str = distance_to_center
            hotel_info['price']: str = price
            hotel_info['booking']: str = booking
            if history.get_count_of_photo(id_user):
                hotel_info['photo']: List[str] = get_photo(hotel['id'], history.get_count_of_photo(id_user))
            top.append(hotel_info)
            if count == history.get_count_of_hotels(id_user):
                break

    if page_number == configs.page_number:
        return top

    if count < history.get_count_of_hotels(id_user):
        page_number += 1
        get_hotels_info(id_user, count, page_number, top)

    return top





