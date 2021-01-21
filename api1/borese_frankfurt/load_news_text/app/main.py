import json
import os
import random
import re
import time

import pymongo
import requests
import schedule
from fake_headers import Headers
from graphitesend import GraphiteClient
from tqdm import tqdm

header = Headers(
    headers=True
)

proxy_list = [{
    f"http": f"{os.environ['PROXY_HOST']}:900{i}",
    f"https": f"{os.environ['PROXY_HOST']}:900{i}"
} for i in range(0, 10)]


def get_random_proxy():
    return random.choice(proxy_list)


def req(url, timeout=30, proxy={}):
    resp = requests.get(url, timeout=timeout, headers=header.generate(), proxies=proxy)
    resp.raise_for_status()
    return resp


def clean_data(data):
    data = data.replace("\n", "") \
        .replace("\r", "") \
        .replace("\t", "") \
        .replace(";", ",") \
        .replace("\"", "'") \
        .strip()
    data = re.sub('<[^>]*>', ' ', data)
    data = re.sub('\s+', ' ', data)
    data = data.strip()
    return data


def get_news(url, proxy):
    _id = url.rsplit('/', 1)[-1]
    request_url = f"https://api.boerse-frankfurt.de/v1/data/news?id={_id}"
    resp = req(request_url, proxy=proxy)
    time.sleep(0.1)
    return json.loads(resp.content)


def main():
    graph_client = GraphiteClient(graphite_server=os.environ["GRAPHITE_SERVER"], graphite_port=2003, prefix="app.stats")
    graph_client.send("boerse.frankfurt.load_news_text.executions", 1)

    client = pymongo.MongoClient(f"mongodb://{os.environ['MONGO_HOST']}:27017/")
    mydb = client["news"]
    col = mydb["boerse_frankfurt"]

    inserts = 0
    try:
        proxy = get_random_proxy()
        for item in col.find({"articles.full_text": {"$type": 10}}):
            print(item["date"])
            for doc in tqdm(item["articles"]):
                if doc["full_text"] is not None:
                    continue

                json_response = get_news(doc["url"], proxy)
                item_full_text = clean_data(json_response["body"])
                item_country_codes = json_response["countryCodes"]
                item_subject_codes = json_response["subjectCodes"]

                doc["full_text"] = item_full_text
                doc["country_codes"] = item_country_codes
                doc["subject_codes"] = item_subject_codes
                inserts += 1

            col.replace_one({'_id': item['_id']}, item)
    finally:
        graph_client.send("boerse.frankfurt.load_news_text.count", inserts)


if __name__ == '__main__':
    main()
    schedule.every(30).minutes.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
