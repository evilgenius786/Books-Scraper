import csv
import json
import os
import os.path
import threading
import traceback

import openpyxl
import requests
from bs4 import BeautifulSoup
from slugify import slugify

name = "BookDepository"

encoding = "utf-8"
thread_count = 10
semaphore1 = threading.Semaphore(thread_count)
semaphore2 = threading.Semaphore(thread_count)
urls = []
url = "https://www.bookdepository.com"
threads = []


def getData(book_url, filters=None):
    with semaphore2:
        if filters is None:
            filters = []
        soup = getSoup(book_url)
        data = {
            "URL": f"{url}{soup.find('meta', {'itemprop': 'url'}).get('content').strip()}",
            "Sale Price": soup.find('span', {'class': "sale-price"}).text if soup.find('span', {'class': "sale-price"}) else "",
            "List Price": soup.find('span', {'class': "list-price"}).text if
            soup.find('span', {'class': "list-price"}) else "",
            "Name": soup.find('h1', {'itemprop': "name"}).text.strip(),
            "Details": soup.find('div', {'itemprop': "description"}).text.strip(),
            "Language": soup.find('span', {'itemprop': "inLanguage"}).text.strip(),
            "Platform": name,
            "Filter": " > ".join(filters),
            "Author": ", ".join(
                [author.text.strip() for author in soup.find('span', {'itemprop': "author"}) if author.text.strip()]),
            "Cover": soup.find('img', {'class': "book-img"}).get('src', ""),
        }
        return data

def initialize():
    if not os.path.isdir(f"{name}"):
        os.mkdir(f"{name}")
    if not os.path.isdir(f"{name}-books"):
        os.mkdir(f"{name}-books")
def main():
    logo()
    initialize()
    if not os.path.isfile(f'{name}-urls.txt'):
        getCategoryUrls('/')
        with open(f"{name}-urls.txt", "w") as f:
            f.write("\n".join(urls))
        print(f"Found {len(urls)} urls")
    else:
        processCategoryUrls()


def scrapeBook(book_url, filter):
    book_url = book_url.replace("?ref=grid-view","")
    file = f"{name}-books/{slugify(book_url)}.json"
    if os.path.isfile(file):
        print("Already scraped", book_url)
    else:
        try:
            data = getData(f"{url}{book_url}", filter)
            with open(file, 'w', encoding=encoding) as f:
                json.dump(data, f)
        except:
            traceback.print_exc()
            print("Error scraping", book_url)


def getBooks(cat_url):
    with semaphore1:
        book_url = f"{url}{cat_url}"
        print("Working on", book_url)
        soup = getSoup(book_url)
        count = int(soup.find('span', {"class": "search-count"}).text.strip().replace(',', ''))
        print(f"Found {count} books")
        for i in range(1, min((int(count / 30)) + 1, 333)):
            print(f"Page {i}")
            soup = getSoup(f"{book_url}?page={i}")
            for div in soup.find_all('div', {'class': "item-img"}):
                filters = [li.text.strip() for li in soup.find_all('li', {'class': "parent-item"})]
                threads.append(threading.Thread(target=scrapeBook, args=(div.find('a')['href'], filters[1:],)))
                threads[-1].start()


def processCategoryUrls():
    with open(f'{name}-urls.txt', 'r') as cfile:
        cat_urls = cfile.read().splitlines()
    for cat_url in cat_urls:
        threads.append(threading.Thread(target=getBooks, args=(cat_url,)))
        threads[-1].start()
    for thread in threads:
        thread.join()


def getCategoryUrls(cat_url, level=0):
    c_url = f"https://www.bookdepository.com{cat_url}"
    # print(url)
    if level == 0:
        soup = getSoup(c_url)
        for li in soup.find('ul', {"class": "category-dropdown-list vertical-dropdown-list"}).find_all('li'):
            print(f"Level ({level}) {li.find('a').text.strip()}")
            getCategoryUrls(li.find('a')['href'], level + 1)
    elif level == 1:
        soup = getSoup(c_url)
        for a in soup.find_all('a', {'class': f"sub-category-{level}"})[1:]:
            print(f"Level ({level}) {a.text.strip()}")
            getCategoryUrls(a['href'], level + 1)
    elif level == 2:
        urls.extend([a['href'] for a in getSoup(url).find_all('a', {'class': f"sub-category-{level}"})[1:]])
    else:
        return


def getSoup(get_url):
    print("URL ", get_url)
    file = f"{name}/{slugify(get_url.replace(url,''))}.html"
    if os.path.isfile(file):
        print("Reading from file ", file)
        with open(file, 'r', encoding=encoding) as f:
            return BeautifulSoup(f.read(), 'lxml')
    else:
        soup = BeautifulSoup(requests.get(get_url).text, "lxml")
        try:
            with open(file, 'w', encoding=encoding) as f:
                f.write(soup.prettify())
        except:
            pass
        return soup


def combineJson():
    data = []
    for file in os.listdir(f"{name}-books"):
        with open(f"{name}-books/{file}", "r", encoding=encoding) as f:
            try:
                data.append(json.load(f))
            except:
                traceback.print_exc()
                print(f"Error on file {file}")
    with open(f"{name}.csv", "w", encoding=encoding, newline='') as f:
        c = csv.DictWriter(f, data[0].keys())
        c.writeheader()
        c.writerows(data)
    convert(f"{name}.csv")


def convert(filename):
    wb = openpyxl.Workbook()
    ws = wb.active
    # csv.field_size_limit(sys.maxsize)
    with open(filename, encoding=encoding) as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            ws.append(row)
    wb.save(filename.replace("csv", "xlsx"))


def logo():
    print(fr"""
___.                  __       .___                         .__  __                       
\_ |__   ____   ____ |  | __ __| _/____ ______   ____  _____|__|/  |_  ___________ ___.__.
 | __ \ /  _ \ /  _ \|  |/ // __ |/ __ \\____ \ /  _ \/  ___/  \   __\/  _ \_  __ <   |  |
 | \_\ (  <_> |  <_> )    </ /_/ \  ___/|  |_> >  <_> )___ \|  ||  | (  <_> )  | \/\___  |
 |___  /\____/ \____/|__|_ \____ |\___  >   __/ \____/____  >__||__|  \____/|__|   / ____|
     \/                   \/    \/    \/|__|              \/                       \/     
=========================================================================================
           {name} books scraper by @evilgenius786
=========================================================================================
[+] CSV/JSON/XLSX files will be saved in the current directory
[+] Without browser
[+] API based
_________________________________________________________________________________________
""")


if __name__ == '__main__':
    main()
