import datetime

import pandas as pd
import requests
import yfinance as yf


def find_earlierst_date(collection, stock):
    return collection.find({"stock": stock}).sort({"date_time": -1}).limit(1)


def insert_stock(collection, date: datetime, stock: str, items: dict):
    res = collection.update_one(
        {"date": date},
        {"stock": stock},
        {
            "$addToSet": {
                "stock_data": items
            },
        },
        upsert=True
    )
    return res


def get_stock_data_from_yf(symbol_name: str, start, end):
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')
    try:
        data = yf.multi._download_one(symbol_name,
                                      interval="1m",
                                      start=start_str,
                                      end=end_str,
                                      proxy={})
        print(f"> Symbol {symbol_name} {start_str}-{end_str}")
        return data
    except requests.exceptions.ProxyError as ex:
        print(ex)
    print(f"> ALL PROXIES DOWN, download without")
    return yf.download(symbol_name, interval="1m", start=start_str, end=end_str, group_by='ticker')


def get_last_30_days_from_stock(symbol_name):
    end = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=28)
    intervals = []
    while end <= datetime.datetime.utcnow():
        end = start + datetime.timedelta(days=6)
        intervals.append([start, end])
        start = end
    df = None
    for start, end in intervals:
        try:
            if df is None:
                df = get_stock_data_from_yf(symbol_name, start, end)
            else:
                df = df.append(get_stock_data_from_yf(symbol_name, start, end))
        except Exception as ex:
            print(ex)
    return df


def get_symbol_df(symbol):
    df = get_last_30_days_from_stock(symbol)
    if df.shape[0] == 0:
        raise Exception(f"Empty Dataframe {symbol}")
    return df


def main():
    with open("stock_symbols.txt", "r") as stocks:
        lines = stocks.readlines()
        while True:
            for stock_symbol in lines:
                try:
                    stock_symbol = stock_symbol.replace("\n", "")
                    df = get_symbol_df(stock_symbol)
                    df["Date"] = df.index
                    agg = df.groupby([df['Date'].dt.to_period("D")])
                    for day, group in agg:
                        print(day)
                        print(group)
                        ins = group.to_dict('records')
                        print(ins)
                        print()

                    df['Datetime'] = pd.to_datetime(df['Datetime'], format='%Y-%m-%d ')

                    print(df)
                    break
                finally:
                    pass
