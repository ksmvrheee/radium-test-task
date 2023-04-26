from multiprocessing import Process

from tools import get_files_from_repo, download_files,\
    get_sha256_for_files_in_dir, remove_directory


# добавление ссылки на репозиторий
repo_url = 'https://gitea.radium.group/radium/project-configuration'
# имя временной папки для скачивания содержимого репозитория
destination_folder = 'tmp'
# имя итогового файла с результатами
result_file_name = 'HASHING_RESULTS.txt'

# получение разделённой на три части коллекции с данными о файлах репозитория
files_in_head = get_files_from_repo(repo_url)


def download(files_collection):
    """
    Создание процессов выполнения функций с аргументами из коллекции.
    """
    process_pool = []
    for collection in files_collection:
        process_pool.append(Process(
            target=download_files,
            args=(collection, destination_folder)
        ))

    # запуск процессов на выполнение
    for process in process_pool:
        process.start()

    # ожидание завершения процессов
    for process in process_pool:
        process.join()


if __name__ == '__main__':
    download(files_in_head)
    get_sha256_for_files_in_dir(destination_folder, result_file_name)
    remove_directory(destination_folder)
