import datetime
import os
import random
import time

import pymongo
import requests
import schedule
import yfinance as yf
from graphitesend import GraphiteClient
from tqdm import tqdm


def get_env(key, default=None):
    try:
        return os.environ[key]
    except:
        if not default:
            raise
    return default


def find_earliest_date(collection, stock):
    last = list(collection.find({"stock": stock}).sort([("date", -1)]).limit(1))
    if len(last) == 0:
        return datetime.datetime.utcnow() - datetime.timedelta(days=28)
    return last[0]["date"]


def insert_stock(collection, date: datetime, stock: str, items: list):
    res = collection.update_one(
        {
            "date": date,
            "stock": stock,
        },
        {
            '$set': {
                'stock_data': items
            }
        },
        upsert=True
    )
    return res


def get_random_proxy():
    proxy_list = [{
        f"http": f"{get_env('PROXY_HOST', '127.0.0.1')}:900{i}",
        f"https": f"{get_env('PROXY_HOST', '127.0.0.1')}:900{i}"
    } for i in range(0, 10)]
    return random.choice(proxy_list)


def get_stock_data_from_yf(symbol_name: str, start, try_again=True):
    proxy = get_random_proxy()
    start_str = start.strftime('%Y-%m-%d')
    end_str = (start + datetime.timedelta(days=6)).strftime('%Y-%m-%d')
    try:
        data = yf.multi._download_one(symbol_name,
                                      interval="1m",
                                      start=start_str,
                                      end=end_str,
                                      proxy=proxy)
        print(f"> Symbol {symbol_name} {start_str}-{end_str}")
        return data
    except requests.exceptions.ProxyError as ex:
        print(ex)
        if try_again:
            return get_stock_data_from_yf(symbol_name, start, False)


def insert_stocks(col, stock_symbol):
    earliest_date = find_earliest_date(col, stock_symbol)
    diff_days = (datetime.datetime.utcnow() - earliest_date).days
    if diff_days < 8:
        print(f"SKIP {stock_symbol}")
        return
    df = get_stock_data_from_yf(stock_symbol, earliest_date)
    if df.size == 0:
        return
    df["Timestamp"] = df.index
    agg = df.groupby([df['Timestamp'].dt.to_period("D")])
    for day, group in agg:
        day = day.start_time
        ins = group.to_dict('records')
        insert_stock(col, day, stock_symbol, ins)


def main():
    graph_client = GraphiteClient(graphite_server=get_env("GRAPHITE_SERVER", "127.0.0.1"), graphite_port=2003,
                                  prefix="app.stats")
    client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "127.0.0.1")}:27017/')

    stock_db = client["stocks"]
    col = stock_db["yahoo_finance"]

    with open("stock_list.txt", "r") as file:
        for stock_symbol in tqdm(file.readlines()):
            stock_symbol = stock_symbol.replace("\n", "")
            insert_stocks(col, stock_symbol)
            graph_client.send(f"stocks.{stock_symbol}", 1)


if __name__ == '__main__':
    main()
    schedule.every().day.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
