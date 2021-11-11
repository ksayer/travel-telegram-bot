import requests
import json
from decouple import config
from typing import List, Optional
from datetime import date, timedelta, datetime
from src.botrequests import history
import re

RAPIDAPI_KEY: str = config('RAPIDAPI_KEY')

headers = {
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
    :return: List[str] Города, которые совпали в написании с тем, что запросил пользователь
    """
    url: str = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring: dict = {"query": city, "locale": "ru_RU", "currency": "RUB"}

    response_city_id: json = requests.request("GET", url, headers=headers, params=querystring)
    data: json = json.loads(response_city_id.text)

    entities: List[dict] = data['suggestions'][0]['entities']
    list_cities: List = []

    for entity in entities:
        if entity['type'] == 'CITY':
            full_name: str = delete_span(entity['caption'])
            list_cities.append([full_name, entity['destinationId']])

    return list_cities


def get_properties_list(id_city: int) -> List[dict]:
    """
    Функция возвращающая список отелей, отсортированным по цене (сначала самые дешевые)
    :param id_city: id города
    :return:  список отелей, в котором хранится информация о каждом отеле
    """
    today: datetime.date = date.today()
    check_in: str = str(today + timedelta(days=2))
    check_out: str = str(today + timedelta(days=3))
    url: str = "https://hotels4.p.rapidapi.com/properties/list"
    querystring: dict = {"destinationId": id_city, "pageNumber": "1", "pageSize": "25", "checkIn": check_in,
                         "checkOut": check_out, "adults1": "1", "sortOrder": "PRICE", "locale": "ru_RU",
                         "currency": "RUB"}

    response_properties_list: json = requests.request("GET", url, headers=headers, params=querystring)
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
    response_photo: json = requests.request("GET", url, headers=headers, params=querystring)
    data: json = json.loads(response_photo.text)

    list_photo: List = []

    for photo in range(int(number)):
        address_photo = data['hotelImages'][photo]['baseUrl']
        address_photo = address_photo.replace('{size}', 'b')
        list_photo.append(address_photo)

    return list_photo


def get_hotels_info(id_user, date_create) -> None:
    """
    Финальная функция. Создает список словарей, которые включают в себя информацию, которую будем выводить пользователю
    по каждому отелю.
    В функции get_properties_list мы берем список 25 отелей и присваиваем его list_hotels
    Сначала мы вы берем необходимые значения из list_hotels, потом присваиваем их новому словарю. На каждой итерации
    цикла мы добавляем созданный словарь в список top.
    count - счетчик кол-ва добавленных отелей, как только станет равен числу от пользователя - цикл остановится, список
    запишется в БД.
    Если пользователь попросил фотографии, то запросим в функции get_photo
    """
    count: int = 0
    top: List = []
    list_hotels: List[dict] = get_properties_list(history.get_id_city_user(id_user, date_create))
    for hotel in list_hotels:
        hotel_info: dict = dict()
        count += 1
        name: str = hotel['name']
        id_hotel: str = str(hotel['id'])
        booking = ''.join(['https://ru.hotels.com/ho', id_hotel])
        try:
            address: Optional[str] = hotel['address']['streetAddress']
        except KeyError:
            address: Optional[str] = None
        distance_to_center: str = hotel['landmarks'][0]['distance']
        price: str = hotel['ratePlan']['price']['current']

        hotel_info['name']: str = name
        hotel_info['address']: str = address
        hotel_info['distance_to_center']: str = distance_to_center
        hotel_info['price']: str = price
        hotel_info['booking']: str = booking

        if history.get_photo(id_user, date_create):
            hotel_info['photo']: List[str] = get_photo(hotel['id'], history.get_count_of_photo(id_user, date_create))
        top.append(hotel_info)

        if count == history.get_count_of_hotels(id_user, date_create):
            break

    history.set_hotels(id_user, top, date_create)
