import datetime
import os
import time

import feedparser
import pymongo
import requests
import schedule
from dateutil.parser import parse
from fake_headers import Headers

header = Headers(
    headers=True
)


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
    return collection.count_documents({"articles.url": url}) > 0


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


def get_news_feed(url):
    xml_to_convert = retry(lambda: requests.get(url, headers=header.generate(), proxies={
        f"http": f"{get_env('PROXY_HOST', '10.0.0.6')}:8080",
        f"https": f"{get_env('PROXY_HOST', '10.0.0.6')}:8080"
    }).content)
    xml_to_convert = xml_to_convert.decode("utf-8").replace("\n", "")
    return feedparser.parse(xml_to_convert)


def main():
    client = pymongo.MongoClient(f"mongodb://10.0.0.4:27017/")
    mydb = client["news"]
    col = mydb["handelsblatt"]
    col.create_index([("date", 1)])
    col.create_index([("articles.url", 1)])

    items = [
        "schlagzeilen",
        "wirtschaft",
        "top-themen",
        "finanzen",
        "marktberichte",
        "unternehmen",
        "politik",
        "technologie",
        "panorama",
        "research-institut",
    ]
    for item in items:
        insert_articles(col, f"https://www.handelsblatt.com/contentexport/feed/{item}")


def insert_articles(col, url):
    news_feeds = get_news_feed(url)
    for news_feed in news_feeds["entries"]:
        if exists(col, news_feed["link"]):
            continue

        feed_date = parse(news_feed["published"]).astimezone(datetime.timezone.utc)
        item_date = datetime.datetime.strptime(feed_date.strftime("%Y%m%d"), '%Y%m%d')
        mod_feed = {
            "headline": news_feed["title"],
            "url": news_feed["link"],
            "summary": news_feed["summary"],
            "tags": [tag["term"] for tag in news_feed["tags"]],
            "published": feed_date,
            "full_text": None
        }
        insert_article(col, item_date, mod_feed)


if __name__ == '__main__':
    main()
    schedule.every(10).minutes.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
