from auth_public import *

import os
import re
import pandas as pd

import plotly.express as px
import plotly.graph_objects as go
import chart_studio.tools as tls
import plotly.io as pio
import chart_studio.plotly as py

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

tls.set_credentials_file(username='Avto2703', api_key='nxfzKttfX0xGZsWMSttd')

DB_PORT = os.environ.get('POSTGRES_PORT', 5432)
con = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)

price_data = pd.read_sql("SELECT * FROM price_history", con)
#pair_data = pd.read_sql("SELECT * FROM pair", con)
#asset_data = pd.read_sql("SELECT * FROM asset", con)
trade_data = pd.read_sql("SELECT user_id, symbol_id, type, date, pnl FROM trade", con)

def filter_by_row(df, column, filter_list):
    ''' Vrne df, samo z vrsticami, ki imajo v stolpcu column
        eno izmed vrednosti s seznama filter_list '''
    seznam = list()
    for row in df.index:
        drop_item = True
        for value in filter_list:
            if df[column][row] == value:
                drop_item = False
        if drop_item == True:
            seznam.append(row)
    df = df.drop(seznam)
    df = df.reset_index(drop=True)
    return df

def datumi():
    ''' Vrne df z vsemi možnimi datumi in stolpcem z 0 '''
    df = filter_by_row(price_data, 'symbol_id', ['BTC-USD'])
    df = df.drop(['symbol_id', 'price'], axis=1)
    df = df.reset_index(drop=True)
    df['price'] = [0] * len(df.index)
    return df

def pnl_type(df, usd=False):
    ''' Funkcija vrne le trade, ki imajo PNL v istem assetu kot je trade.
        PNL je velikokrat lahko tudi v USD, toda v tem primeru moram PNL 
        računati pri USD namest pri pripadajočem assetu '''
    bad_index = list()
    for i in df.index:
        pnl = re.findall(r'\d+(?:\.\d+)?\$', df['pnl'][i])
        if usd == False:
            if pnl != []:
                bad_index.append(i)
        else:
            if pnl == []:
                bad_index.append(i)
    df = df.drop(bad_index)
    if usd == True:
        df = clean_sign(df)
    df['pnl'] = pd.to_numeric(df['pnl'])
    return df

def clean_sign(df):
    for row in df.index:
        pnl = re.findall(r'(?:-)?\d+(?:\.\d+)?\$', df['pnl'][row])
        if pnl != []:
            pnl = re.sub('\$','',pnl[0])
            df.loc[row, 'pnl'] = pnl
    return df

def pripravi_trade_data(id_user, symbol_id, usd=False):
    ''' Za izbranega uporabnika in izbran simbol vrne df
        s stoplci date, symbol_id, pnl '''
    df = trade_data
    df = filter_by_row(df, 'user_id', [id_user])
    if symbol_id != 'dollar':
        df = filter_by_row(df, 'symbol_id', [symbol_id])
    df = df.drop(['user_id', 'type', 'symbol_id'], axis=1)
    df = pnl_type(df, usd)
    df = df.groupby('date', as_index=False).sum()
    return df

def fix_stocks(symbol_id):
    ''' Zgodovina delnic je brez vikendov in praznikov, ta funkcija
        generira 'realne podatke' in jih vstavi'''
    stock = filter_by_row(price_data, 'symbol_id', [symbol_id])
    df = datumi()
    if len(stock) < len(df):
        # Vstavi ceno 0 za dni, ki niso definirani
        for row in df.index:
            for i in stock.index:
                if df['date'][row] == stock['date'][i]:
                    df.loc[row, 'price'] = stock['price'][i]
        # Popravi ceno, kjer je ta 0, da bo graf zvezen
        if len(stock) > 0:
            for row in df.index:
                i = 1
                while df['price'][row] == 0:
                    if row < (len(df) - 3):
                        try:
                            df.loc[row, 'price'] = df['price'][row + i]
                        except KeyError or ValueError:
                            df.loc[row, 'price'] = 0
                    elif row > (len(df) - 5):
                        df.loc[row, 'price'] = df['price'][row - i]
                    i += 1
        # Dodamo symbol_id in preuredimo stolpce
        df['symbol_id'] = [symbol_id] * len(df.index)
        df = df[['symbol_id', 'date', 'price']]
        return df
    else:
        return stock

def assets_on_day(user_id, symbol_id):
    ''' Vrne df, v katerem je vrednost naše naložbe za vsak dan '''
    price_df = fix_stocks(symbol_id)
    trade_df = pripravi_trade_data(user_id, symbol_id)
    price_df['amount'] = [0] * len(price_df.index)
    price_df = price_df.sort_values(by='date').reset_index(drop=True)
    for row in price_df.index:
            same_amount = True
            for item in trade_df.index:
                if price_df['date'][row] == trade_df['date'][item]:
                    same_amount = False
                    try:
                        price_df.loc[row, 'amount'] =  price_df['amount'][row-1] + trade_df['pnl'][item]
                    except KeyError:
                        price_df.loc[row, 'amount'] += trade_df['pnl'][item]
                elif (price_df['date'][row] != trade_df['date'][item]) and (same_amount == True):
                    same_amount = False
                    try:
                        if row != 0:
                            price_df.loc[row, 'amount'] = price_df['amount'][row-1]
                        else:
                            price_df.loc[row, 'amount'] = 0
                    except KeyError:
                        price_df.loc[row, 'amount'] = 0
    price_df['value'] = price_df['price'] * price_df['amount']
    return price_df

def usd_case(user_id):
    ''' Simbol USD je obravnavan drugače, ker imajo lahko tradi
        v drugih assetih dobiček v USD '''
    df = datumi()
    trade_df = get_usd_data(user_id)
    df.rename(columns = {'price':'value'}, inplace = True)
    for row in df.index:
            same_amount = True
            for trade in trade_df.index:
                if df['date'][row] == trade_df['date'][trade]:
                    same_amount = False
                    try:
                        df.loc[row, 'value'] =  df['value'][row-1] + trade_df['price'][trade]
                    except KeyError:
                        df.loc[row, 'value'] += trade_df['price'][trade]
                elif (df['date'][row] != trade_df['date'][trade]) and (same_amount == True):
                    same_amount = False
                    try:
                        df.loc[row, 'value'] = df['value'][row-1]
                    except KeyError:
                        df.loc[row, 'value'] = 0
    return df

def get_usd_data(user_id):
    ''' Pomožna funkcija, ki vrne vse dobičke odražene v $ '''
    df = datumi()
    trade_1 = pripravi_trade_data(user_id, 'dollar', True)
    trade_2 = pripravi_trade_data(user_id, 'USD', True)
    trade_3 = pripravi_trade_data(user_id, 'USD', False)
    seznam = list()
    seznam.append(trade_1)
    seznam.append(trade_2)
    seznam.append(trade_3)
    trade_df = pd.concat(seznam, copy=False)
    trade_df = trade_df.groupby('date', as_index=False).sum()
    trade_df = trade_df.sort_values(by='date').reset_index(drop=True)
    # Vstavi ceno 0 za dni, ki niso definirani
    for row in df.index:
        for i in trade_df.index:
            if df['date'][row] == trade_df['date'][i]:
                df.loc[row, 'price'] = trade_df['pnl'][i]
    return df

def multy_asset(s_list, user_id):
    ''' Sprejme seznam simbolov, za katere združi podatke
        za vsak dan '''
    seznam = list()
    for simbol in s_list:
        if simbol == 'USD':
            s = usd_case(user_id)
        else:
            s = assets_on_day(user_id, simbol)
            s = s.drop(['symbol_id', 'price', 'amount'], axis=1)
        seznam.append(s)
    df = pd.concat(seznam, copy=False)
    df = df.groupby('date', as_index=False).sum()
    df = df.sort_values(by='date').reset_index(drop=True)
    return df

def graph_html(user_id, symbol_list, X_column='date', Y_column='value'):
    global i
    data = multy_asset(symbol_list, user_id)
    fig = go.Figure([go.Scatter(x=data[X_column], y=data[Y_column])])
    imenik = os.path.dirname("Views/Graphs/assets.html")
    if imenik:
        os.makedirs(imenik, exist_ok=True)
    fig.write_html("Views/Graphs/assets.html")

def graph_cake(user_id, date):
    global i
    seznam = list()
    zacasni = list()
    asset_data = pd.read_sql("SELECT symbol_id FROM asset WHERE user_id  = {}".format(user_id), con)
    for row in asset_data.index:
        seznam.append(asset_data['symbol_id'][row])
    for simbol in seznam:
        if simbol != 'USD':
            df = assets_on_day(user_id, simbol)
        if simbol == 'USD':
            df = usd_case(user_id)
            df['symbol_id'] = ['USD'] * len(df.index)
        df = df.iloc[[-1]]
        zacasni.append(df)
    df = pd.concat(zacasni, copy=False)
    df = df.rename(columns={'symbol_id': 'simbol', 'value': 'vrednost'})
    fig = px.pie(df, values='vrednost', names='simbol',
                 color_discrete_sequence=px.colors.sequential.Purp_r)
    imenik = os.path.dirname("Views/Graphs/cake.html")
    if imenik:
        os.makedirs(imenik, exist_ok=True)
    fig.write_html("Views/Graphs/cake.html")

cake  = graph_cake(1, '2023-04-30')