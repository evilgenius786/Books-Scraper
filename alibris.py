import csv
import json
import os
import os.path
import threading
import time
import traceback

import openpyxl
import requests
from bs4 import BeautifulSoup
from slugify import slugify

url = "https://www.alibris.com"

name = "AlIbris"

encoding = "utf-8"
thread_count = 1
semaphore = threading.Semaphore(thread_count)


def getData(book_url):
    return {}
    soup = getSoup(book_url)
    bi = soup.find('meta', {"itemprop": "productID"}).get('content').replace('bi:', '').strip()
    data = {
        "URL": f"{url}/servlet/BookDetailsPL?bi={bi}",
        "Cost (USD)": soup.find('meta', {'itemprop': "price"}).get('content', ""),
        "Name": soup.find('span', {'class': "main-heading"}).text,
        "Details": soup.find('div', {'class': "cf detail-section"}).find('div').text.strip(),
        # "Language": "",
        "Platform": name,
        "Filter": " > ".join([span.text.strip() for span in soup.find('div', {'id': "breadcrumbs"}).find_all('span', {
            'class': 'breadcrumb'})]),
        "Author": soup.find('h2', {'id': "book-author"}).text.strip(),
        "Cover": soup.find('meta', {'itemprop': "image"}).get('content', ""),
        "Images": " | ".join([img.get('src', "") for img in soup.find_all('img', {"class": "gallery-thumb hide"})]),
    }
    return data


def getBook(href):
    file = f"{name}-Books/{slugify(href)}.json"
    if os.path.isfile(file):
        print(f"Already scraped {url}")
        return
    with semaphore:
        book_url = f"{url}{href}"
        print("Working on", book_url)
        try:
            data = getData(book_url)
            print(json.dumps(data, indent=4))
            with open(file, 'w') as outfile:
                json.dump(data, outfile, indent=4)
        except:
            traceback.print_exc()
            print(f"Error on book url {href}")


def processCategory(href):
    for i in range(21):
        soup = getSoup(f"{url}{href}?page={i}")
        for a in soup.find_all('a', {'class': "title"}):
            getBook(a.get('href'))


def startCategories():
    soup = getSoup('https://www.alibris.com/subjects')
    cats = [a.get('href') for a in soup.find('table', {"id": "browse-subject"}).find_all('a')]
    for cat in cats:
        processCategory(cat)


def main():
    logo()
    initialize()
    startCategories()
    combineJson()


def initialize():
    if not os.path.isdir(f"{name}-Books"):
        os.mkdir(f"{name}-Books")
    if not os.path.isdir(f"{name}"):
        os.mkdir(f"{name}")


def getSoup(get_url):
    print(f"Fetching data from {get_url}")
    file = f"{name}/{slugify(get_url.replace(url, ''))}.html"
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
    for file in os.listdir(f"{name}-Books"):
        with open(f"{name}-Books/{file}", "r", encoding=encoding) as f:
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
               _____ ___.         __________               __            
              /  _  \\_ |__   ____\______   \ ____   ____ |  | __  ______
             /  /_\  \| __ \_/ __ \|    |  _//  _ \ /  _ \|  |/ / /  ___/
            /    |    \ \_\ \  ___/|    |   (  <_> |  <_> )    <  \___ \ 
            \____|__  /___  /\___  >______  /\____/ \____/|__|_ \/____  >
                    \/    \/     \/       \/                   \/     \/ 
=========================================================================================
           {name} Books scraper by @evilgenius786
=========================================================================================
[+] CSV/JSON/XLSX files will be saved in the current directory
[+] Without browser
[+] API based
_________________________________________________________________________________________
""")


if __name__ == '__main__':
    main()
