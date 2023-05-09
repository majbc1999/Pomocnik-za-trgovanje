from auth_public import *

import os
import re
import pandas as pd

import plotly
import plotly.graph_objects as go

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

DB_PORT = os.environ.get('POSTGRES_PORT', 5432)
con = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)
# cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

price_data = pd.read_sql("SELECT * FROM price_history", con)
pair_data = pd.read_sql("SELECT * FROM pair", con)
asset_data = pd.read_sql("SELECT * FROM asset", con)
trade_data = pd.read_sql("SELECT user_id, symbol_id, type, date, pnl FROM trade", con)

def filter_by_row(df, column, filter_list):
    '''Vrne df, samo z vrsticami, ki imajo v stolpcu column
        eno izmed vrednosti s seznama filter_list'''
    seznam = list()
    for row in df.index:
        drop_item = True
        for value in filter_list:
            if df[column][row] == value:
                drop_item = False
        if drop_item == True:
            seznam.append(row)
    return df.drop(seznam)

def pnl_type(df, usd=False):
    '''Funkcija vrne le trade, ki imajo PNL v istem assetu kot je trade.
    PNL je velikokrat lahko tudi v USD, toda v tem primeru moram PNL 
    računati pri USD namest pri pripadajočem assetu.'''
    bad_index = list()
    for i in df.index:
        pnl = re.findall(r'\d+(?:\.\d+)?\$', df['pnl'][i])
        if usd == False:
            if pnl != []:
                bad_index.append(i)
        else:
            if pnl == []:
                bad_index.append(i)
    return df.drop(bad_index)

def clean_trade_data(df, id_user, symbol_id, usd=False):
    df = filter_by_row(df, 'user_id', [id_user])
    df = filter_by_row(df, 'symbol_id', [symbol_id])
    df = df.drop(['user_id', 'type'], axis=1)
    df = pnl_type(df)
    df['pnl'] = pd.to_numeric(df['pnl'])
    df = df.groupby(['date', 'symbol_id'], as_index=False).sum()
    return df

def assets_on_day(symbol_id, price_df, pnl_df):
    price_df = filter_by_row(price_df, 'symbol_id', [symbol_id])
    weekend_stocks(symbol_id, price_df, pnl_df)
    pnl_df['pnl'] = pd.to_numeric(pnl_df['pnl'])
    price_df['amount'] = 0
    price_df = price_df.sort_values(by='date').reset_index()
    for row in price_df.index:
        same_amount = True
        if price_df['price'][row] == 0:
            price_df['price'][row] = weekend_stock_price(price_df, row)
        for item in pnl_df.index:
            if price_df['date'][row] == pnl_df['date'][item]:
                same_amount = False
                try:
                    price_df['amount'][row] =  price_df['amount'][row-1] + pnl_df['pnl'][item]
                except KeyError:
                    price_df['amount'][row] += pnl_df['pnl'][item]
            elif (price_df['date'][row] != pnl_df['date'][item]) and (same_amount == True):
                same_amount = False
                try:
                    price_df['amount'][row] = price_df['amount'][row-1]
                except KeyError:
                    price_df['amount'][row] = 0
    price_df['value'] = price_df['price'] * price_df['amount']
    return price_df

def weekend_stocks(symbol_id, price_df, pnl_df):
    seznam = list()
    for item in pnl_df.index:
        add_date = True
        for row in price_df.index:
            if pnl_df['date'][item] == price_df['date'][row]:
                add_date = False
        if add_date == True:
            price_df.loc[len(price_df)] = [symbol_id, pnl_df['date'][item], 0]

def weekend_stock_price(df, index):
    try:
        return df['price'][index - 1]
    except KeyError:
        return df['price'][index + 1]
    
def graph_data_asset(symbol_id, price_data, trade_data, user_id):
    pnl_df = clean_trade_data(trade_data, user_id, symbol_id)
    return assets_on_day(symbol_id, price_data, pnl_df)

def graph(df, X_column, Y_column):
    fig = go.Figure([go.Scatter(x=df[X_column], y=df[Y_column])])
    fig.show()

symbol_list = ['BTC-USD', 'ETH-USD', 'SPY']

def multy_asset(s_list, price_data, trade_data, user_id):
    seznam = list()
    #df = filter_by_row(price_data, 'symbol_id', ['BTC-USD'])
    #df = df.drop(['symbol_id', 'price'], axis=1)
    #df['value'] = 0
    #df['value'] = 0
    df = pd.DataFrame
    #print(df)
    for simbol in s_list:
        s = graph_data_asset(simbol, price_data, trade_data, user_id)
        #s = s.drop(['index', 'symbol_id', 'price', 'amount'], axis=1)
        #seznam.append(s)
        #df.join(simbol, how='left', on='date')
        #f.merge(simbol, how='outer', on='date')
        #print(simbol)
        #df = df.groupby(['date'], as_index=False ).sum()
        df = pd.concat(seznam, copy=False)
    df = df.sort_values(by='date').reset_index()
    #df.groupby(['date'], as_index=False).sum()
    print(df.to_string())


    #df = df.groupby(['date', 'symbol_id'], as_index=False).sum()


data = graph_data_asset('SPY', price_data, trade_data, 1)
#multy_asset(symbol_list, price_data, trade_data, 1)
print(len(data))
#graph(data, 'date', 'value')
