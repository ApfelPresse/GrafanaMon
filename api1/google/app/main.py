import datetime
import os
import re
import time

import feedparser
import pymongo
import requests
import schedule
from bs4 import BeautifulSoup
from dateutil.parser import parse
from fake_headers import Headers
from graphitesend import GraphiteClient
from tqdm import tqdm

header = Headers(
    headers=True
)


def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)


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


def exists(collection, url: str):
    return collection.count_documents({"articles.google_url": url}) > 0


def get_env(key, default=None):
    try:
        return os.environ[key]
    except:
        if not default:
            raise
    return default


def retry(fun, max_tries=3):
    for i in range(max_tries):
        try:
            return fun()
        except requests.exceptions.ProxyError as err:
            if i < max_tries - 1:
                raise err
            continue


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


def get_news_feed(url):
    resp = retry(lambda: req(url).content)
    xml_to_convert = resp.decode("utf-8").replace("\n", "")
    return feedparser.parse(xml_to_convert)


def main():
    graph_client = GraphiteClient(graphite_server=get_env("GRAPHITE_SERVER", "10.0.0.3"), graphite_port=2003,
                                  prefix="app.stats")
    client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "10.0.0.4")}:27017/')

    mydb = client["news"]
    col = mydb["google_news"]
    col.create_index([("date", 1)])
    col.create_index([("articles.google_url", 1)])

    topics = [
        "WORLD",
        "NATION",
        "BUSINESS",
        "TECHNOLOGY",
        "ENTERTAINMENT",
        "SCIENCE"
    ]

    graph_client.send("google.load_article.execution", 1)
    try:
        for topic in topics:
            insert_articles(col, f"https://news.google.com/news/rss/headlines/section/topic/{topic}?hl=de", graph_client)
    except Exception as ex:
        graph_client.send("google.articles.exceptions", 1)
        print(ex)
        raise ex


def insert_articles(col, url, graph_client):
    news_feeds = get_news_feed(url)
    inserts = 0
    try:
        for news_feed in tqdm(news_feeds["entries"]):
            if exists(col, news_feed["link"]):
                continue

            feed_date = parse(news_feed["published"]).astimezone(datetime.timezone.utc)
            item_date = datetime.datetime.strptime(feed_date.strftime("%Y%m%d"), '%Y%m%d')

            feed_url = retry(lambda: req(news_feed["link"]).url)

            summary = BeautifulSoup(news_feed["summary"], 'html.parser').get_text()
            mod_feed = {
                "headline": news_feed["title"],
                "google_url": news_feed["link"],
                "url": feed_url,
                "summary": summary,
                "published": feed_date,
                "full_text": None
            }
            insert_article(col, item_date, mod_feed)
            inserts += 1
    finally:
        graph_client.send("google.articles.inserts", inserts)


if __name__ == '__main__':
    main()
    schedule.every().minute.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
