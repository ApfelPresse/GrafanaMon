import datetime

from api1.yahoo.app.main import main, get_stock_data_from_yf


def get_random_proxy():
    return {}


main.get_random_proxy = get_random_proxy

if __name__ == '__main__':
    df = get_stock_data_from_yf("NFLX", datetime.datetime.utcnow()-datetime.timedelta(days=5))
    main()
