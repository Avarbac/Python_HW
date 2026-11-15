"""Автотесты для парсера books.toscrape.com (запуск: ``pytest``)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper import get_book_data, get_book_urls, scrape_books  # noqa: E402

BOOK_URL = ('http://books.toscrape.com/catalogue/'
            'a-light-in-the-attic_1000/index.html')
EXPECTED_KEYS = {'title', 'price', 'rating', 'available', 'description',
                 'category', 'url', 'product_info'}


@pytest.fixture(scope='module')
def book():
    """Данные одной книги, загруженные один раз на весь модуль."""
    return get_book_data(BOOK_URL)


def test_book_data_is_dict_with_keys(book):
    """get_book_data возвращает словарь со всеми нужными ключами."""
    assert isinstance(book, dict)
    assert EXPECTED_KEYS <= book.keys()


def test_book_field_values(book):
    """Значения полей книги совпадают с данными на сайте."""
    assert book['title'] == 'A Light in the Attic'
    assert book['price'] == pytest.approx(51.77)
    assert book['rating'] == 3
    assert book['available'] == 22
    assert book['category'] == 'Poetry'
    assert book['description'].startswith("It's hard to imagine")


def test_product_info_table(book):
    """Таблица Product Information разобрана полностью."""
    info = book['product_info']
    assert info['UPC'] == 'a897fe39b1053632'
    assert info['Product Type'] == 'Books'
    assert info['Number of reviews'] == '0'
    assert len(info) == 7


def test_catalogue_page_has_20_links():
    """На странице каталога 20 абсолютных ссылок на книги."""
    urls = get_book_urls('http://books.toscrape.com/catalogue/page-1.html')
    assert len(urls) == 20
    assert all(url.startswith('http://books.toscrape.com/catalogue/')
               for url in urls)


def test_scrape_books_limited_and_saved(tmp_path):
    """scrape_books собирает 20 книг со страницы и сохраняет их в файл."""
    output = tmp_path / 'books_data.txt'
    books = scrape_books(is_save=True, max_pages=2, output_path=output)
    assert len(books) == 40
    lines = output.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 40
    assert json.loads(lines[0])['title'] == books[0]['title']


def test_scrape_books_without_saving(tmp_path):
    """При is_save=False файл не создаётся."""
    output = tmp_path / 'books_data.txt'
    books = scrape_books(is_save=False, max_pages=1, output_path=output)
    assert len(books) == 20
    assert not output.exists()
