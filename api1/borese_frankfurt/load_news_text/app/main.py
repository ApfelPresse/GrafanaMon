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

def get_env(key, default=None):
    try:
        return os.environ[key]
    except:
        if not default:
            raise
    return default


def req(url, timeout=30):
    resp = requests.get(url, timeout=timeout, headers=header.generate(), proxies={
        f"http": f"{get_env('PROXY_HOST', '127.0.0.1')}:8080",
        f"https": f"{get_env('PROXY_HOST', '127.0.0.1')}:8080"
    })
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


def get_news(url):
    _id = url.rsplit('/', 1)[-1]
    request_url = f"https://api.boerse-frankfurt.de/v1/data/news?id={_id}"
    print(request_url)
    resp = req(request_url)
    return json.loads(resp.content)


def main():
    graph_client = GraphiteClient(graphite_server=get_env("GRAPHITE_SERVER", "127.0.0.1"), graphite_port=2003,
                                  prefix="app.stats")
    graph_client.send("boerse.frankfurt.load_news_text.executions", 1)

    client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "127.0.0.1")}:27017/')
    mydb = client["news"]
    col = mydb["boerse_frankfurt"]

    for item in col.find({"articles.full_text": {"$type": 10}, "articles.skip": {"$exists": False}}):
        inserts = 0
        try:
            print(item["date"])
            for doc in tqdm(item["articles"]):
                if doc["full_text"] is not None:
                    continue

                try:
                    json_response = get_news(doc["url"])
                    item_full_text = clean_data(json_response["body"])
                    item_country_codes = json_response["countryCodes"]
                    item_subject_codes = json_response["subjectCodes"]

                    doc["full_text"] = item_full_text
                    doc["country_codes"] = item_country_codes
                    doc["subject_codes"] = item_subject_codes
                except requests.exceptions.HTTPError as err:
                    if err.response.status_code == 404:
                        doc["skip"] = "404 Exception"
                        continue
                    else:
                        raise err

                inserts += 1
            col.replace_one({'_id': item['_id']}, item)
        except requests.exceptions.ProxyError as ex:
            graph_client.send("boerse.frankfurt.load_news_text.proxy_error", 1)
        finally:
            graph_client.send("boerse.frankfurt.load_news_text.count", inserts)


if __name__ == '__main__':
    schedule.every(5).minutes.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
