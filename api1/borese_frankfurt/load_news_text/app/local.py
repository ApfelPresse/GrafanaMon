import os

from api1.borese_frankfurt.load_news_text.app.main import main

if __name__ == '__main__':
    os.environ["GRAPHITE_SERVER"] = ""
    os.environ['MONGO_HOST'] = ""
    os.environ["PASSWORD"] = ""
    main()
