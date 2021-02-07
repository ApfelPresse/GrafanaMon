import os
import time

import pymongo
import requests
import schedule
from fake_headers import Headers
from graphitesend import GraphiteClient
from newsplease import NewsPlease
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


def req(url):
    headers = header.generate()
    if "Accept-Encoding" in headers:
        headers.pop("Accept-Encoding")
    proxies = {
        f"http": f"http://{get_env('PROXY_HOST', '10.0.0.6')}:8080",
        f"https": f"http://{get_env('PROXY_HOST', '10.0.0.6')}:8080"
    }
    resp = requests.get(url, headers=headers, proxies=proxies)
    resp.raise_for_status()
    return resp


def get_article(url):
    html = req(url).content.decode("utf-8")
    article = NewsPlease.from_html(html)
    if not article.maintext:
        raise Exception("Article Missing Maintext")
    return article


def main():
    graph_client = GraphiteClient(graphite_server=get_env("GRAPHITE_SERVER", "10.0.0.3"), graphite_port=2003,
                                  prefix="app.stats")
    client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "10.0.0.4")}:27017/')

    db = client["news"]
    col = db["handelsblatt"]

    graph_client.send("load_full_text.load_news_text.execution", 1)
    for item in col.find({"articles.full_text": {"$type": 10}, "articles.skip": {"$exists": False}}):
        inserts = 0
        try:
            print(item["date"])
            for doc in tqdm(item["articles"]):
                if doc["full_text"]:
                    continue
                try:
                    article = get_article(doc["url"])
                    full_text = article.maintext
                    lang = article.language

                    doc["full_text"] = full_text
                    doc["lang"] = lang

                    inserts += 1
                except UnicodeDecodeError as err:
                    graph_client.send("load_full_text.load_news_text.exceptions.unicode", 1)
                    print(err)
                    continue
                except requests.exceptions.HTTPError as err:
                    if err.response.status_code == 404:
                        doc["skip"] = "404 Exception"
                        graph_client.send("load_full_text.load_news_text.exceptions.404", 1)
                        print(err)
                        continue
                    else:
                        graph_client.send("load_full_text.load_news_text.exceptions.httperror", 1)
                        print(err)
                        raise err
                except requests.exceptions.ProxyError as ex:
                    graph_client.send("load_full_text.load_news_text.proxy_error", 1)
                    print(ex)
                    continue
                except Exception as err:
                    graph_client.send("load_full_text.load_news_text.exceptions.general", 1)
                    print(err)
                    raise err
                finally:
                    if not doc["full_text"]:
                        skip_count = 0
                        if skip_count in doc:
                            skip_count = doc["skip_count"]
                        doc["skip_count"] = skip_count + 1

            col.replace_one({'_id': item['_id']}, item)
        finally:
            graph_client.send("load_full_text.load_news_text.inserts", inserts)


if __name__ == '__main__':
    main()
    schedule.every().minute.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
