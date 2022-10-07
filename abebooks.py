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

url = "https://www.abebooks.com"

name = "AbeBooks"

encoding = "utf-8"
thread_count = 1
semaphore = threading.Semaphore(thread_count)


def getData(soup):
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


def getCourse(bid):
    file = f"{name}-courses/{bid}.json"
    if os.path.isfile(file):
        print(f"Already scraped {url}")
        return
    with semaphore:
        course_url = f"{url}/servlet/BookDetailsPL?bi={bid}"
        print("Working on", course_url)
        try:
            data = getData(getSoup(course_url))
            print(json.dumps(data, indent=4))
            with open(file, 'w') as outfile:
                json.dump(data, outfile, indent=4)
        except:
            traceback.print_exc()
            print(f"Error on book ID {bid}")


def processCollections():
    with open('collection3.txt', 'r') as cfile:
        collections = cfile.read().splitlines()
    threads = []
    for col in collections:
        for i in range(1, 1000):
            collection = f"{url}{col.split('?')[0]}/items/json?offset={i}"
            print(f"Working on collection {collection}")
            res = requests.get(collection).json()
            if not res:
                break
            for item in res:
                threads.append(threading.Thread(target=getCourse, args=(item['id'],)))
                threads[-1].start()
                # time.sleep(0.1)
    for thread in threads:
        thread.join()


def getCollections():
    viewall = "btn btn-default btn-xs-block pull-right"
    if not os.path.isfile("collection1.txt"):
        soup = BeautifulSoup(requests.get(f'{url}/collections/').text, "lxml")
        collection1 = [f"{url}{a['href']}" for a in soup.find_all('a', {'class': viewall})]
        with open('collection1.txt', 'w') as cfile:
            cfile.write("\n".join(collection1))
    else:
        with open('collection1.txt', 'r') as cfile:
            collection1 = cfile.read().splitlines()
    if not os.path.isfile("collection2.txt"):
        collection2 = []
        for collection in collection1:
            print("Working on collection: {}".format(collection))
            soup = BeautifulSoup(requests.get(collection).text, "lxml")
            collection2.extend([a['href'] for a in soup.find_all('a', {'class': viewall})])
            # break
        with open('collection2.txt', 'w') as cfile:
            cfile.write("\n".join(collection2))
    else:
        with open('collection2.txt', 'r') as cfile:
            collection2 = cfile.read().splitlines()
    if not os.path.isfile("collection3.txt"):
        collection3 = []
        for collection in collection2:
            print("Working on collection: {}".format(collection))
            soup = BeautifulSoup(requests.get(f"{url}{collection}").text, "lxml")
            collection3.extend([div.find('a')['href'] for div in soup.find_all('div', {"class": "collection-card"})])
            # break
        with open('collection3.txt', 'w') as cfile:
            cfile.write("\n".join(collection3))
    else:
        with open('collection3.txt', 'r') as cfile:
            collection3 = cfile.read().splitlines()


def main():
    logo()
    if not os.path.isdir(f"{name}-courses"):
        os.mkdir(f"{name}-courses")
    getCollections()
    processCollections()
    combineJson()
    # if not os.path.isdir(f"{name}-pages"):
    #     os.mkdir(f"{name}-pages")


def getSoup(get_url, retry=3):
    return BeautifulSoup(requests.get(get_url).text, "lxml")
    # soup = BeautifulSoup(requests.get(get_url).text, 'lxml')
    # if "HTTP Status 429 – Too Many Requests" in str(soup):
    #     time.sleep(1)
    #     if retry == 0:
    #         return None
    #     return getSoup(get_url, retry - 1)


def combineJson():
    data = []
    for file in os.listdir(f"{name}-courses"):
        with open(f"{name}-courses/{file}", "r", encoding=encoding) as f:
            data.append(json.loads(f.read()))
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
    print(r"""
    _________                        __  .__             .____    .__              
    \_   ___ \_______   ____ _____ _/  |_|__|__  __ ____ |    |   |__|__  __ ____  
    /    \  \/\_  __ \_/ __ \\__  \\   __\  \  \/ // __ \|    |   |  \  \/ // __ \ 
    \     \____|  | \/\  ___/ / __ \|  | |  |\   /\  ___/|    |___|  |\   /\  ___/ 
     \______  /|__|    \___  >____  /__| |__| \_/  \___  >_______ \__| \_/  \___  >
            \/             \/     \/                   \/        \/             \/ 
=========================================================================================
           CreativeLive courses scraper by @evilgenius786
=========================================================================================
[+] CSV/JSON/XLSX files will be saved in the current directory
[+] Without browser
[+] API based
_________________________________________________________________________________________
""")


if __name__ == '__main__':
    main()