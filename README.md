# Books Scraper

Парсер каталога книг с учебного сайта [Books to Scrape](http://books.toscrape.com).
Домашнее задание 3 курса Python для анализа данных: парсинг, Git и тестирование.

## Цель

Автоматически собирать данные обо всех 1000 книгах сайта — название, цену,
рейтинг, количество в наличии, описание, категорию и характеристики из таблицы
Product Information — и сохранять их в текстовый файл. Сбор можно запускать
вручную или ежедневно по расписанию (по умолчанию в 19:00).

## Структура проекта

```
books_scraper/
├── artifacts/
│   └── books_data.txt        # результат парсинга: одна книга — одна строка JSON
├── notebooks/
│   └── HW_03_python_ds.ipynb # ноутбук с решением и выводами ячеек
├── tests/
│   └── test_scraper.py       # автотесты pytest
├── scraper.py                # основной скрипт
├── requirements.txt
├── .gitignore
└── README.md
```

## Установка

```bash
git clone <ссылка на репозиторий>
cd books_scraper
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

## Запуск

Однократный сбор всех книг с сохранением в `artifacts/books_data.txt`:

```bash
python scraper.py
```

Ежедневный запуск по расписанию (по умолчанию в 19:00, время можно изменить):

```bash
python scraper.py --schedule
python scraper.py --schedule --time 08:30
```

Использование из Python:

```python
from scraper import get_book_data, scrape_books

book = get_book_data('http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html')
books = scrape_books(is_save=True)   # список из 1000 словарей + файл
```

## Тесты

Тесты обращаются к сайту, поэтому нужен доступ в интернет:

```bash
pytest
```

## Формат данных

Каждая строка `artifacts/books_data.txt` — JSON-объект:

```json
{"title": "A Light in the Attic", "price": 51.77, "rating": 3, "available": 22,
 "description": "It's hard to imagine a world without ...", "category": "Poetry",
 "url": "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
 "product_info": {"UPC": "a897fe39b1053632", "Product Type": "Books", "...": "..."}}
```

## Используемые библиотеки

- `requests` — HTTP-запросы к сайту;
- `beautifulsoup4` — разбор HTML;
- `schedule` — запуск задачи по расписанию;
- `pytest` — автотесты;
- `jupyter` — ноутбук с решением;
- стандартная библиотека: `json`, `re`, `time`, `argparse`, `pathlib`, `concurrent.futures`.
