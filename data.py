import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import pyarrow
import time
import random
import os

tz = pytz.timezone('Asia/Shanghai')
today = datetime.now(tz).strftime('%Y-%m-%d')

stk_path = './stk.parquet'
stock_list = pd.read_parquet(stk_path)
stock_list = stock_list['股票代码'].tolist()
stock_list = [('sh.' if stk.startswith('6') else 'sz.') + stk for stk in stock_list]

start_date = today
end_date = today - timedelta(days=1)

bs.login()
result = []
for code in stock_list:
    rs_list = []
    rs_factor = bs.query_adjust_factor(code=code, start_date=start_date, end_date=end_date)
    while (rs_factor.error_code == '0') & rs_factor.next():
        rs_list.append(rs_factor.get_row_data())
    result_factor = pd.DataFrame(rs_list, columns=rs_factor.fields)
    if not result_factor.empty:
        result.append(result_factor)
bs.logout()

if result:
    df = pd.concat(result,ignore_index=True)
    if os.path.exists('./data/raw_factor.parquet'):
        old_raw = pd.read_parquet('./data/raw_factor.parquet')
        new_raw = pd.concat([old_raw,df],ignore_index=False)
    else:
        new_raw = df
    new_raw = new_raw.drop_duplicates()
    new_raw.to_parquet('./data/raw_factor.parquet',engine='pyarrow',index=False)
    df['股票代码'] = df['code'].str[-6]
    df['除权除息日'] = pd.to_datetime(df['dividOperateDate'])
    df['后复权因子'] = df['backAdjustFactor'].astype('float64')
    df = df[['股票代码','除权除息日','后复权因子']]
    if os.path.exists('./data/hfq_factor.parquet'):
        old_hfq = pd.read_parquet('./data/hfq_factor.parquet')
        new_hfq = pd.concat([old_hfq,df],ignore_index=False)
    else:
        new_hfq = df
    new_hfq = new_hfq.drop_duplicates()
    new_hfq = new_hfq.sort_values(['股票代码','除权除息日'])
    new_hfq.to_parquet("./data/hfq_factor.parquet",engine='pyarrow',index=False)
