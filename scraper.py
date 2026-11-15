"""Парсер каталога книг с сайта Books to Scrape.

Модуль собирает информацию обо всех книгах сайта http://books.toscrape.com:
название, цену, рейтинг, количество в наличии, описание и характеристики
из таблицы Product Information. Результат можно сохранить в текстовый файл
(одна книга — одна строка в формате JSON) и запускать сбор ежедневно
по расписанию с помощью библиотеки ``schedule``.

Примеры запуска из терминала::

    python scraper.py                 # однократный сбор с сохранением
    python scraper.py --schedule      # ежедневный запуск в 19:00
    python scraper.py --schedule --time 12:30
"""

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
import schedule
from bs4 import BeautifulSoup

BASE_URL = 'http://books.toscrape.com/'
CATALOGUE_PAGE_URL = BASE_URL + 'catalogue/page-{}.html'
DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'artifacts' / 'books_data.txt'
REQUEST_TIMEOUT = 15
RATING_WORDS = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}


def get_soup(url: str, session: Optional[requests.Session] = None,
             retries: int = 3) -> BeautifulSoup:
    """Загружает страницу и возвращает её разобранный HTML.

    Args:
        url (str): адрес страницы.
        session (requests.Session | None): сессия для повторного
            использования соединений; если не передана, используется
            ``requests.get``.
        retries (int): число попыток при сетевых ошибках.

    Returns:
        BeautifulSoup: дерево HTML-документа.

    Raises:
        requests.HTTPError: если сервер вернул код ошибки (например, 404).
        requests.RequestException: если все попытки загрузки не удались.
    """
    getter = session.get if session is not None else requests.get
    for attempt in range(1, retries + 1):
        try:
            response = getter(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            break
        except requests.HTTPError:
            raise
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(attempt)
    # Сайт не указывает кодировку в заголовках, сами страницы — в UTF-8.
    response.encoding = 'utf-8'
    return BeautifulSoup(response.text, 'html.parser')


def _parse_price(text: str) -> float:
    """Преобразует строку цены вида '£51.77' в число 51.77."""
    return float(re.sub(r'[^\d.]', '', text))


def _parse_available(text: str) -> int:
    """Извлекает количество из строки 'In stock (22 available)' -> 22."""
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0


def get_book_data(book_url: str,
                  session: Optional[requests.Session] = None) -> dict:
    """Собирает данные об одной книге с её страницы.

    Извлекает название, цену, рейтинг, количество в наличии, описание,
    категорию и все характеристики из таблицы Product Information.

    Args:
        book_url (str): полный адрес страницы книги, например
            'http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html'.
        session (requests.Session | None): необязательная HTTP-сессия.

    Returns:
        dict: словарь с ключами
            'title' (str) — название книги;
            'price' (float) — цена в фунтах (с налогом);
            'rating' (int) — рейтинг от 1 до 5 (0, если не найден);
            'available' (int) — количество экземпляров в наличии;
            'description' (str) — описание (пустая строка, если его нет);
            'category' (str) — категория книги;
            'url' (str) — адрес страницы книги;
            'product_info' (dict) — все пары «характеристика: значение»
            из таблицы Product Information (UPC, Product Type и т.д.).
    """
    soup = get_soup(book_url, session)
    main = soup.find('div', class_='product_main')

    title = main.h1.get_text(strip=True)
    price = _parse_price(main.find('p', class_='price_color').get_text())

    rating_tag = main.find('p', class_='star-rating')
    rating = 0
    if rating_tag is not None:
        for css_class in rating_tag.get('class', []):
            rating = RATING_WORDS.get(css_class, rating)

    description_header = soup.find('div', id='product_description')
    description = ''
    if description_header is not None:
        description = description_header.find_next_sibling('p').get_text(
            strip=True)

    breadcrumb = soup.select('ul.breadcrumb li a')
    category = breadcrumb[-1].get_text(strip=True) if breadcrumb else ''

    product_info = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select('table.table-striped tr')
    }

    return {
        'title': title,
        'price': price,
        'rating': rating,
        'available': _parse_available(product_info.get('Availability', '')),
        'description': description,
        'category': category,
        'url': book_url,
        'product_info': product_info,
    }


def get_book_urls(page_url: str,
                  session: Optional[requests.Session] = None) -> list:
    """Возвращает ссылки на все книги с одной страницы каталога.

    Args:
        page_url (str): адрес страницы каталога вида
            'http://books.toscrape.com/catalogue/page-1.html'.
        session (requests.Session | None): необязательная HTTP-сессия.

    Returns:
        list[str]: абсолютные адреса страниц книг (обычно 20 штук).
    """
    soup = get_soup(page_url, session)
    return [urljoin(page_url, link['href'])
            for link in soup.select('article.product_pod h3 a')]


def save_books(books: list, path: Path = DEFAULT_OUTPUT) -> None:
    """Сохраняет список книг в текстовый файл (одна книга — строка JSON).

    Args:
        books (list[dict]): данные книг, полученные из ``get_book_data``.
        path (Path): путь к файлу; папки создаются при необходимости.

    Returns:
        None
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        for book in books:
            file.write(json.dumps(book, ensure_ascii=False) + '\n')


def scrape_books(is_save: bool = False, max_pages: Optional[int] = None,
                 output_path: Path = DEFAULT_OUTPUT,
                 max_workers: int = 10, verbose: bool = False) -> list:
    """Собирает данные обо всех книгах каталога, обходя страницы по очереди.

    Проходит по страницам вида
    ``http://books.toscrape.com/catalogue/page-{N}.html``, начиная с первой,
    пока сайт не вернёт 404 (или пока не достигнут ``max_pages``). Для каждой
    книги вызывает ``get_book_data``; страницы книг одной страницы каталога
    загружаются параллельно для ускорения.

    Args:
        is_save (bool): если True, результат сохраняется в файл
            ``output_path`` (по умолчанию ``artifacts/books_data.txt``).
        max_pages (int | None): ограничение на число страниц каталога
            (удобно для тестов); None — обойти все страницы.
        output_path (Path): путь к файлу для сохранения.
        max_workers (int): число потоков для загрузки страниц книг.
        verbose (bool): печатать ли прогресс по страницам.

    Returns:
        list[dict]: список словарей с данными книг (формат —
        см. ``get_book_data``).
    """
    books = []
    page = 1
    with requests.Session() as session, \
            ThreadPoolExecutor(max_workers=max_workers) as executor:
        while max_pages is None or page <= max_pages:
            try:
                book_urls = get_book_urls(CATALOGUE_PAGE_URL.format(page),
                                          session)
            except requests.HTTPError as error:
                if error.response is not None \
                        and error.response.status_code == 404:
                    break  # страницы закончились
                raise
            books.extend(executor.map(
                lambda url: get_book_data(url, session), book_urls))
            if verbose:
                print(f'Страница {page}: всего собрано {len(books)} книг')
            page += 1

    if is_save:
        save_books(books, output_path)
    return books


def scheduled_job() -> None:
    """Задача для планировщика: собирает все книги и сохраняет их в файл."""
    started = time.strftime('%Y-%m-%d %H:%M:%S')
    books = scrape_books(is_save=True)
    print(f'[{started}] Собрано {len(books)} книг, '
          f'данные сохранены в {DEFAULT_OUTPUT}')


def run_scheduler(run_at: str = '19:00', check_interval: int = 60,
                  max_runs: Optional[int] = None) -> None:
    """Запускает ежедневный сбор данных в заданное время.

    В бесконечном цикле раз в ``check_interval`` секунд проверяет, не пора
    ли выполнить задачу, чтобы не нагружать процессор постоянной проверкой.

    Args:
        run_at (str): время запуска в формате 'чч:мм' (по умолчанию 19:00).
        check_interval (int): пауза между проверками расписания, секунды.
        max_runs (int | None): остановиться после указанного числа запусков
            (для демонстрации); None — работать бесконечно.

    Returns:
        None
    """
    runs = 0

    def job() -> None:
        nonlocal runs
        scheduled_job()
        runs += 1

    schedule.clear()
    schedule.every().day.at(run_at).do(job)
    print(f'Планировщик запущен: сбор данных каждый день в {run_at}')
    while max_runs is None or runs < max_runs:
        schedule.run_pending()
        time.sleep(check_interval)
    schedule.clear()


def main() -> None:
    """Точка входа: разбирает аргументы командной строки и запускает сбор."""
    parser = argparse.ArgumentParser(
        description='Парсер каталога книг books.toscrape.com')
    parser.add_argument('--schedule', action='store_true',
                        help='запускать сбор ежедневно по расписанию')
    parser.add_argument('--time', default='19:00',
                        help='время ежедневного запуска, чч:мм')
    args = parser.parse_args()

    if args.schedule:
        run_scheduler(args.time)
    else:
        books = scrape_books(is_save=True, verbose=True)
        print(f'Готово: {len(books)} книг сохранено в {DEFAULT_OUTPUT}')


if __name__ == '__main__':
    main()
