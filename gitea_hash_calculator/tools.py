import hashlib
import os

from shutil import rmtree
from sys import exit

import requests


def split_into_three_parts(collection):
    """
    Делит коллекцию на три примерно равные части.
    """
    chunk_size = round(len(collection) / 3)  # получение размера одной части

    # разделение коллекции на части
    first_chunk = collection[:chunk_size]
    second_chunk = collection[chunk_size:2 * chunk_size]
    third_chunk = collection[2 * chunk_size:]

    # запись результатов
    result = []
    if first_chunk:
        result.append(first_chunk)
    if second_chunk:
        result.append(second_chunk)
    if third_chunk:
        result.append(third_chunk)

    return result


def get_files_from_repo(url):
    """
    Получает файлы из репозитория и делит коллекцию с ними на три части.
    """

    # реставрация url для запроса
    domain, username, project_name = url.split('://')[-1].split('/')
    request_url = f'https://{domain}/api/v1/repos/{username}/{project_name}/contents/'

    stack = [request_url]  # инициализация стека с url для запроса
    files = []

    while stack:
        current_url = stack.pop()

        # Совершение запроса
        try:
            response = requests.get(current_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:  # обработка исключений
            print(f'Ошибка при подключении к серверу: {error}.')
            exit(1)
        else:
            data = response.json()  # Получение ответа в формате json

        # Итерация json, создание списка кортежей (<путь_к_файлу>, <ссылка_на_скачивание>)
        for element in data:
            el_type = element.get('type')

            if el_type == 'file':
                if not element.get('download_url'):
                    # создание новой ссылки для скачивания в случае её отсутствия
                    download_url = element['html_url'].replace('/src/', '/raw/', 1)
                else:
                    download_url = element['download_url']

                files.append((element['path'], download_url))

            elif el_type == 'dir':
                stack.append(element['url'])  # добавление элемента в стек

            elif not el_type:
                # вывод сообщения об ошибке в случае, если у json-объекта нет ключа type
                print('Ошибка при парсинге json: ключ не найден.')
                exit(1)

    # Разделение списка на три примерно равные части
    files = split_into_three_parts(files)

    return files


def download_files(files_collection, destination_path):
    """
    Скачивает файлы из коллекции в указанную папку.
    Если данный каталог и файлы уже существуют, будет произведена перезапись.
    """
    for file in files_collection:
        # извлечение имени файла, url, задание пути для него
        filename = file[0].split('/')[-1]
        path = f'{destination_path}/{file[0]}'
        url = file[1]

        # проверка на существование директории и создание директории, обработка ошибок
        if not os.path.exists(os.path.dirname(path)) and os.path.dirname(path):
            try:
                os.makedirs(os.path.dirname(path))
            except OSError as exc:
                print(f'Ошибка при создании директории: {exc}.')

        # скачивание файлов с помощью requests, обработка ошибок
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(path, 'wb') as f:
                f.write(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Произошла ошибка: {e}.")

        print(f'Загружен файл {filename}.\n')


def sha256_checksum(filename, block_size=65536):
    """
    Считает хэш-сумму файла по кластерам со стандартным размером 64кб,
    возвращает общую хэш-сумму файла.
    """
    sha256 = hashlib.sha256()  # инициализация объекта хэшера

    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):  # чтение файла блоками
            sha256.update(block)  # составление хэша блоками

    return sha256.hexdigest()  # получение общего хэша


def get_sha256_for_files_in_dir(directory, result_file_name):
    """
    Считает хэш-сумму всех файлов в директории и вложенных папках.
    Сохраняет результат хэширования в файл на один каталог выше с названием,
    которое было передано, также дублируя его в консоль.
    """
    def trim_dir(path):
        """
        Обрезает имя директории для корректного вывода.
        """
        first_dash = path.find('\\')  # поиск первой обратной косой черты

        return path[first_dash + 1:]

    hash_list = []  # список для хранения пар (<путь>), (<хэш-сумма>)

    for root, dirs, files in os.walk(directory):  # проход по директории
        # сортировка файлов и папок лексикографически
        dirs.sort()
        files.sort()

        for file in files:
            file_path = os.path.join(root, file)  # получение пути к файлу
            checksum = sha256_checksum(file_path)  # расчёт хэш-суммы
            file_path = trim_dir(file_path)  # оптимизация пути к файлу
            hash_list.append((file_path, checksum))  # добавление в список

            print(f'{file_path}: {checksum}.')

    # определение директории для файла результатов
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_name = os.path.join(parent_dir, result_file_name)

    # итерация списка и запись в файл
    with open(file_name, 'w') as f:
        for elements in hash_list:
            f.write(f'{elements[0]}: {elements[1]}\n')
        print(f'Записано в {result_file_name}.')


def remove_directory(path):
    """
    Удаляет директорию со всеми вложенными файлами и папками.
    """
    try:
        rmtree(path)
    except OSError as e:
        print(f"Ошибка при удалении директории {path}: {e}.")
