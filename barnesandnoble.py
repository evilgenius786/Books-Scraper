import csv
import json
import os
import os.path
import threading
import traceback
from threading import Semaphore

import cfscrape
import openpyxl
from bs4 import BeautifulSoup
from slugify import slugify

url = "https://www.barnesandnoble.com"

name = "BarnesAndNoble"
encoding = "utf-8"
thread_count = 20
semaphore = Semaphore(thread_count)
threads = []


def getData(book_url, breadcrumbs=""):
    soup = getSoup(book_url)
    data = {
        "URL": soup.find('meta', {'property': "og:url"}).get('content', ""),
        "ISBN": soup.find('button', {'data-sku': True}).get('data-sku', ""),
        "Cost (USD)": soup.find('span', {'id': "pdp-cur-price"}).text.strip(),
        "Name": soup.find('meta', {'property': "og:title"}).get('content', ""),
        "Details": soup.find('div', {'itemprop': "description"}).text.strip(),
        "Language": soup.find('span', {'itemprop': "inLanguage"}).get('content', ""),
        "Platform": name,
        "Filter": breadcrumbs,
        "Author": soup.find('span', {'itemprop': "author"}).text.strip(),
        "Cover": soup.find('meta', {'property': "og:image"}).get('content', ""),
        "Images": " | ".join(
            [img.get('src', "") for img in soup.find('div', {"class": "product-thumb"}).find_all('img')]) if soup.find('div', {"class": "product-thumb"}) else "",
    }
    return data


def getBook(href, breadcrumbs=""):
    file = f"{name}-Books/{slugify(href)}.json"
    if os.path.isfile(file):
        print(f"Already scraped {url}")
        return
    book_url = f"{url}{href}"
    print("Working on", book_url)
    try:
        data = getData(book_url, breadcrumbs)
        print(json.dumps(data, indent=4))
        with open(file, 'w') as outfile:
            json.dump(data, outfile, indent=4)
    except:
        traceback.print_exc()
        print(f"Error on book url {href}")


def processCategory(href, breadcrumbs=""):
    next_page = f"{url}{href}?Nrpp=40" if href.startswith('/') else f"{href}?Nrpp=40"
    while next_page:
        soup = getSoup(next_page)
        for a in soup.find_all('a', {'class': "title"}):
            t = threading.Thread(target=getBook, args=(a.get('href'), breadcrumbs,))
            threads.append(t)
            t.start()
        next_page = soup.find('a', {'class': "next-button"})
        if next_page:
            next_page = next_page.get('href')


def processSections(href):
    u = f"{url}{href}" if href.startswith('/') else href
    soup = getSoup(u)
    ol = "selected-facets lists lists--unstyled lists--bread-crumbs bc_wrapper"
    if soup.find('ol', {'class': ol}):
        breadcrumbs = " > ".join([li.text.strip() for li in soup.find('ol', {'class': ol}).find_all('span',{"itemprop":"name"})])
    else:
        breadcrumbs = ""
    # print(soup.prettify())
    # print(soup.find('div', {"id", "searchGrid"}).text)
    sec_class = "record-spot-light-section"
    secs = soup.find_all('section', {'class': sec_class})
    if len(secs) == 0:
        processCategory(href, breadcrumbs)
        return
    print(f"Sections found {len(secs)} {href}")
    for sec in secs:
        see_all = sec.find('a', {"class": "see-all-link"})
        if see_all:
            t = threading.Thread(target=processCategory, args=(see_all.get('href'), breadcrumbs,))
            threads.append(t)
            t.start()
        else:
            for a in sec.find_all('a', {"class": "carousel-image-link focus", "href": True}):
                t = threading.Thread(target=getBook, args=(a.get('href'), breadcrumbs,))
                threads.append(t)
                t.start()


def startCategories():
    soup = getSoup('https://www.barnesandnoble.com/h/books/browse')
    for a in soup.find('div', {"class": "html-embed-container"}).find_all('a'):
        t = threading.Thread(target=processSections, args=(a.get('href'),))
        threads.append(t)
        t.start()


def main():
    # processSections('https://www.barnesandnoble.com/b/books/literature/folklore-mythology/_/N-29Z8q8Z2geb')
    # input("Done")
    logo()
    initialize()
    startCategories()
    # combineJson()


def getSoup(get_url):
    print(f"Fetching data from {get_url}")
    file = f"{name}/{slugify(get_url.replace(url, ''))}.html"
    if os.path.isfile(file) and os.path.getsize(file) > 10:
        print(f"Reading from file {file}")
        with open(file, 'r', encoding=encoding) as f:
            return BeautifulSoup(f.read(), 'lxml')
    else:
        with semaphore:
            soup = BeautifulSoup(cfscrape.create_scraper().get(get_url).content, "lxml")
            try:
                with open(file, 'w', encoding=encoding) as f:
                    f.write(soup.prettify())
            except:
                pass
            return soup


def initialize():
    if not os.path.isdir(f"{name}-Books"):
        os.mkdir(f"{name}-Books")
    if not os.path.isdir(f"{name}"):
        os.mkdir(f"{name}")


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
___.                                                         .___           ___.   .__          
\_ |__ _____ _______  ____   ____   ___________    ____    __| _/____   ____\_ |__ |  |   ____  
 | __ \\__  \\_  __ \/    \_/ __ \ /  ___/\__  \  /    \  / __ |/    \ /  _ \| __ \|  | _/ __ \ 
 | \_\ \/ __ \|  | \/   |  \  ___/ \___ \  / __ \|   |  \/ /_/ |   |  (  <_> ) \_\ \  |_\  ___/ 
 |___  (____  /__|  |___|  /\___  >____  >(____  /___|  /\____ |___|  /\____/|___  /____/\___  >
     \/     \/           \/     \/     \/      \/     \/      \/    \/           \/          \/ 
=================================================================================================
                        {name} Books scraper by @evilgenius786
=================================================================================================
[+] CSV/JSON/XLSX files will be saved in the current directory
[+] Without browser
[+] API based
_________________________________________________________________________________________________
""")


if __name__ == '__main__':
    main()
