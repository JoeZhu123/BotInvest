class StockPool:
    def __init__(self):
        # 这是一个精选的关注列表，包含热门美股和港股
        self.us_stocks = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', # Tech Giants
            'JPM', 'BAC', # Finance
            'KO', 'PEP', 'MCD', # Consumer
            'PFE', 'JNJ' # Healthcare
        ]
        
        self.hk_stocks = [
            '0700.HK', # Tencent
            '9988.HK', # Alibaba
            '3690.HK', # Meituan
            '1810.HK', # Xiaomi
            '1211.HK', # BYD
            '0941.HK', # China Mobile
            '0005.HK'  # HSBC
        ]

    def get_all_tickers(self):
        return self.us_stocks + self.hk_stocks

