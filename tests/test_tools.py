import os
import hashlib
import tempfile

from unittest.mock import MagicMock

import pytest
import requests

from gitea_hash_calculator.tools import split_into_three_parts, get_files_from_repo, \
    download_files, sha256_checksum, get_sha256_for_files_in_dir, remove_directory


def test_split_into_three_parts():
    collection = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected_result = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    result = split_into_three_parts(collection)

    assert result == expected_result

    collection = [1, 2, 3, 4, 5]
    expected_result = [[1, 2], [3, 4], [5]]
    result = split_into_three_parts(collection)

    assert result == expected_result

    collection = [1, 2]
    expected_result = [[1], [2]]
    result = split_into_three_parts(collection)

    assert result == expected_result


@pytest.fixture
def mock_requests():
    """
    Mock requests.get method.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [
        {"type": "file", "path": "file1.txt",
         "download_url": "https://example.com/file1.txt"},
        {"type": "file", "path": "file2.txt",
         "html_url": "https://example.com/src/file2.txt"}
    ]
    return MagicMock(return_value=mock_response)


def test_get_files_from_repo(mock_requests):
    url = "https://example.com/user/repo"

    # Мок для requests.get
    requests.get = mock_requests

    # Вызов функции
    result = get_files_from_repo(url)

    # Сравнение с ожидаемым
    assert result[0][0][0] == "file1.txt"
    assert result[0][0][1] == "https://example.com/file1.txt"
    assert result[1][0][0] == "file2.txt"
    assert result[1][0][1] == "https://example.com/raw/file2.txt"
    assert result[1] == result[-1]


@pytest.fixture(scope="module")
def files_collection():
    return [("file1.txt", "https://example.com/file1.txt"),
            ("dir1/file2.txt", "https://example.com/dir1/file2.txt"),
            ("dir2/file3.txt", "https://example.com/dir2/file3.txt")]


@pytest.fixture(scope="module")
def destination_path():
    return tempfile.NamedTemporaryFile().name


def test_download_files(files_collection, destination_path, monkeypatch):
    # Мок для requests.get() для теста скачивания файла
    class MockResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    def mock_get(*args, **kwargs):
        return MockResponse(b"test file contents")

    monkeypatch.setattr(requests, "get", mock_get)

    # Тест скачивания файлов
    download_files(files_collection, destination_path)
    assert os.path.exists(f"{destination_path}/{files_collection[0][0]}")
    assert os.path.exists(f"{destination_path}/{files_collection[1][0]}")
    assert os.path.exists(f"{destination_path}/{files_collection[2][0]}")

    # Тест перезаписи файла
    with open(f"{destination_path}/{files_collection[0][0]}", "w") as f:
        f.write("test")
    download_files([files_collection[0]], destination_path)
    with open(f"{destination_path}/{files_collection[0][0]}", "r") as f:
        assert f.read() == "test file contents"

    # Тест создания директории
    download_files([("new_dir/file.txt", "https://example.com/new_dir/file.txt")],
                   destination_path)
    assert os.path.exists(f"{destination_path}/new_dir")
    assert os.path.exists(f"{destination_path}/new_dir/file.txt")


def test_sha256_checksum():
    # создаем тестовый файл и заполняем его данными
    filename = 'test_file.txt'
    with open(filename, 'wb') as f:
        f.write(b'hello world')

    # проверяем, что хэш сумма файла считается верно
    assert sha256_checksum(filename) == hashlib.sha256(b'hello world').hexdigest()

    # удаляем тестовый файл
    os.remove(filename)


def test_sha256_checksum_large_file():
    # создаем тестовый файл размером 10 Мб
    filename = 'large_file.bin'
    with open(filename, 'wb') as f:
        f.write(os.urandom(10 * 1024 * 1024))

    # проверяем, что хэш сумма файла считается верно
    assert sha256_checksum(filename) == hashlib.sha256(
        open(filename, 'rb').read()
    ).hexdigest()

    # удаляем тестовый файл
    os.remove(filename)


def test_sha256_checksum_empty_file():
    # создаем пустой тестовый файл
    filename = 'empty_file.txt'
    open(filename, 'w').close()

    # проверяем, что хэш сумма файла считается верно
    assert sha256_checksum(filename) == hashlib.sha256(b'').hexdigest()

    # удаляем тестовый файл
    os.remove(filename)


def test_get_sha256_for_files_in_dir():
    # Создаём временную директорию
    with tempfile.TemporaryDirectory() as tmpdir:
        # Создаём временные файлы в директории
        test_file1 = os.path.join(tmpdir, 'test_file1.txt')
        with open(test_file1, 'w') as f:
            f.write('test1')
        test_file2 = os.path.join(tmpdir, 'test_file2.txt')
        with open(test_file2, 'w') as f:
            f.write('test2')

        # Запускаем функцию для получения хэшей файлов в директории
        result_file = os.path.join(tmpdir, 'test_results.txt')
        get_sha256_for_files_in_dir(tmpdir, result_file)

        # Проверяем, что файл с результатами создался
        assert os.path.isfile(result_file)

        # Считываем результаты из файла
        with open(result_file) as f:
            results = f.readlines()

        # Проверяем, что хэши совпадают
        assert any(f'test_file1.txt: {hashlib.sha256("test1".encode()).hexdigest()}'
                   in r for r in results)
        assert any(f'test_file2.txt: {hashlib.sha256("test2".encode()).hexdigest()}'
                   in r for r in results)


def test_remove_directory():
    # создание временной директории для тестов
    temp_dir = tempfile.TemporaryDirectory()
    test_dir = temp_dir.name

    # создание тестовых файлов и директорий
    os.makedirs(os.path.join(test_dir, "test_dir"))
    open(os.path.join(test_dir, "test_file1.txt"), "w").close()
    open(os.path.join(test_dir, "test_file2.txt"), "w").close()

    # удаление директории
    remove_directory(test_dir)

    # проверка, что директория и файлы удалены
    assert not os.path.exists(test_dir)
    assert not os.path.exists(os.path.join(test_dir, "test_dir"))
    assert not os.path.exists(os.path.join(test_dir, "test_file1.txt"))
    assert not os.path.exists(os.path.join(test_dir, "test_file2.txt"))


def test_remove_directory_with_nonexistent_path():
    # попытка удалить несуществующую директорию
    remove_directory("nonexistent_dir")

    # нет ошибки
    assert True
