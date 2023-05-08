from auth_public import *

import plotly
import pandas as pd
import os

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

import plotly.graph_objects as go


DB_PORT = os.environ.get('POSTGRES_PORT', 5432)
con = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)
# cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

price_data = pd.read_sql("SELECT * FROM price_history", con)
pair_data = pd.read_sql("SELECT * FROM pair", con)
asset_data = pd.read_sql("SELECT * FROM asset", con)
trade_data = pd.read_sql_query("SELECT user_id, symbol_id, type, date, pnl FROM trade", con)

asset_data = asset_data.sort_values(by ='user_id')
trade_data = trade_data.sort_values(by ='user_id')

def filter_by(df, column_name, filter):
    for i in range(len(df)):
        df.drop(df[(df[column_name][i]) != filter], index=i)
    


def graph(df, X_column, Y_column):
    fig = go.Figure([go.Scatter(x=df[X_column], y=df[Y_column])])
    fig.show()

#btc_data = pd.read_sql("SELECT date, price FROM price_history WHERE symbol_id = 'BTC-USD'", con)
#graph(btc_data, 'date', 'price')
#assets_on_day

#date_price_asset

#print(trade_data['symbol_id'])

#filter_by(trade_data, 'symbol_id', 'BTC-USD')
print(trade_data.filter(like='BTC-USD', axis=0))
#print(len(trade_data))
#trade_data.drop