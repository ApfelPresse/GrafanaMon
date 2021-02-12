import datetime
import logging
import os
import time
from multiprocessing import Pool

import pymongo
import requests
import schedule
import yfinance as yf
from graphitesend import GraphiteClient

log = logging.getLogger()


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


def get_stock_data_from_yf(symbol_name: str, start, try_again=True):
    start_str = start.strftime('%Y-%m-%d')
    end_str = (start + datetime.timedelta(days=6)).strftime('%Y-%m-%d')
    try:
        data = yf.multi._download_one(symbol_name,
                                      interval="1m",
                                      start=start_str,
                                      end=end_str,
                                      proxy={
                                          f"http": f"http://{get_env('PROXY_HOST', '10.0.0.6')}:8080",
                                          f"https": f"http://{get_env('PROXY_HOST', '10.0.0.6')}:8080"
                                      })
        log.info(f"> Symbol {symbol_name} {start_str}-{end_str}")
        return data
    except requests.exceptions.ProxyError as ex:
        log.error(ex)
        if try_again:
            return get_stock_data_from_yf(symbol_name, start, False)


graph_client = GraphiteClient(graphite_server=get_env("GRAPHITE_SERVER", "10.0.0.3"), graphite_port=2003,
                              prefix="app.stats")
client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "10.0.0.4")}:27017/')


def insert_stocks(symbol):
    stock_symbol = symbol["ticker"]
    log.info(stock_symbol)

    stock_db = client["stocks"]
    col = stock_db["yahoo_finance"]

    earliest_date = find_earliest_date(col, stock_symbol)
    diff_days = (datetime.datetime.utcnow() - earliest_date).days
    if diff_days < 8:
        log.info(f"SKIP {stock_symbol}")
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
    graph_client.send(f"stocks.inserts", 1)


def main():
    graph_client = GraphiteClient(graphite_server=get_env("GRAPHITE_SERVER", "10.0.0.3"), graphite_port=2003,
                                  prefix="app.stats")
    client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "10.0.0.4")}:27017/')
    stock_db = client["stocks"]

    col_symbols = stock_db["yahoo_finance_stock_symbols"]

    with Pool(3) as p:
        print(p.map(insert_stocks, col_symbols.find({}).sort("_id", -1)))


if __name__ == '__main__':
    main()
    schedule.every().day.do(main)
    while True:
        schedule.run_pending()
        time.sleep(10)
