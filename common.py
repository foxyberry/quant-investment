def download_yf_data(ticker: str, start: datetime, end: datetime, retries: int = 5) -> pd.DataFrame:
    wait_time = 5
    for attempt in range(retries):
        try:
            if attempt > 0:
                print(f"Retrying download in {wait_time} seconds...")
                time.sleep(wait_time)
                wait_time *= 2
            print(f"Downloading data for {ticker} from Yahoo Finance...")
            df = yf.download(
                ticker,
                start=start,
                end=end,
                progress=False,
                auto_adjust=True
            )
            if df.empty:
                print("No data received.")
                continue
            df.index = pd.to_datetime(df.index)
            print(f"✅ Successfully downloaded {len(df)} rows of data for {ticker}")
            return df
        except Exception as e:
            print(f"❌ Error: {e}")
            if attempt == retries - 1:
                raise
    return pd.DataFrame()  # Empty on failure


def setup_backtrader(cerebro: bt.Cerebro, data: pd.DataFrame, ticker: str):

    data_feed = bt.feeds.PandasData(
        dataname=data,
        datetime=None,
        open='Open',
        high='High',
        low='Low',
        close='Close',
        volume='Volume',
        openinterest=-1,
        timeframe=bt.TimeFrame.Days
    )

    already_exists = any(getattr(d, '_name', None) == ticker for d in cerebro.datas)

    if not already_exists:
        cerebro.adddata(data_feed, name=ticker)
    else:
        print(f"❗{ticker} 데이터 이미 존재함 - 추가 생략")
    
    print("🚀 Running backtrader analysis...")
