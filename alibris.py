import csv
import json
import os
import os.path
import time
import traceback

import openpyxl
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from slugify import slugify
from webdriver_manager.chrome import ChromeDriverManager

url = "https://www.alibris.com"

name = "AlIbris"
debug = True
encoding = "utf-8"


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
    cats = [a.get('href') for a in soup.find('div', {"id": "browse-subject"}).find_all('a')]
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
        print(f"Reading from file {file}")
        with open(file, 'r', encoding=encoding) as f:
            return BeautifulSoup(f.read(), 'lxml')
    else:
        driver.get(get_url)
        time.sleep(1)
        while "Checking if the site connection is secure" in driver.page_source:
            print(driver.find_element(By.XPATH,'//*').text)
            time.sleep(1)
            # driver.get(get_url)
        soup = BeautifulSoup(driver.page_source, "lxml")
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


def getChromeDriver():
    options = webdriver.ChromeOptions()
    if debug:
        # print("Connecting existing Chrome for debugging...")
        options.debugger_address = "127.0.0.1:9222"
    else:
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--user-data-dir=C:/Selenium1/ChromeProfile')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


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
    driver = getChromeDriver()
    main()
