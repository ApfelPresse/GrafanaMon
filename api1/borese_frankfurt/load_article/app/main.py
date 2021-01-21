import datetime
import json
import logging
import os
import random
import time

import pymongo
import requests
import schedule
from fake_headers import Headers
from graphitesend import GraphiteClient
from tqdm import tqdm

logger = logging.getLogger()

header = Headers(
    headers=True
)


def exists(collection, date: datetime, url: str):
    return collection.count_documents({"articles.url": url}) > 0


def insert_article(collection, date: datetime, item: dict):
    res = collection.update_one(
        {"date": date},
        {
            "$addToSet": {
                "articles": item
            },
        },
        upsert=True
    )
    return res


proxy_list = [{
    f"http": f"{os.environ['PROXY_HOST']}:900{i}",
    f"https": f"{os.environ['PROXY_HOST']}:900{i}"
} for i in range(0, 10)]


def get_random_proxy():
    return random.choice(proxy_list)


def req(url, timeout=60, proxy={}):
    resp = requests.get(url, timeout=timeout, headers=header.generate(), proxies=proxy)
    resp.raise_for_status()
    return resp


def main(limit):
    graph_client = GraphiteClient(graphite_server=os.environ["GRAPHITE_SERVER"], graphite_port=2003, prefix="app.stats")
    graph_client.send("boerse.frankfurt.load_article.executions", 1)
    client = pymongo.MongoClient(f"mongodb://{os.environ['MONGO_HOST']}:27017/")

    db = client["news"]
    col = db["boerse_frankfurt"]

    proxy = get_random_proxy()
    inserts = 0
    try:
        for offset in range(0, limit, limit):
            request_url = f"https://api.boerse-frankfurt.de/v1/data/category_news?withPaging=true&newsType=ALL&lang=de&offset={offset}&limit={limit}"
            resp = req(request_url, proxy=proxy)
            json_response = json.loads(resp.content)
            data = json_response["data"]

            for item in tqdm(data):
                _date = datetime.datetime.fromisoformat(item["time"])
                item_utc = _date.astimezone(datetime.timezone.utc)
                item_date = datetime.datetime.strptime(item_utc.strftime("%Y%m%d"), '%Y%m%d')
                item_headline = item["headline"]
                item_source = item["source"]
                item_lang = "de"
                item_url = f"https://www.boerse-frankfurt.de/nachrichten/{item['id']}"
                db_item = {
                    "url": item_url,
                    "time": item_utc,
                    "source": item_source,
                    "lang": item_lang,
                    "headline": item_headline,
                    "full_text": None,
                }
                if exists(col, item_date, item_url):
                    continue

                insert_article(col, item_date, db_item)
                inserts += 1
    finally:
        graph_client.send("boerse.frankfurt.load_article.inserts", inserts)


if __name__ == '__main__':
    main(100)
    schedule.every(30).minutes.do(main, 100)
    schedule.every().day.do(main, 2000)
    while True:
        schedule.run_pending()
        time.sleep(10)
