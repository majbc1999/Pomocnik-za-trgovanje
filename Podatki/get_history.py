import os
import re
import csv
import pickle
import pandas as pd
from datetime import date
from yahoofinancials import YahooFinancials as yf


trading_pairs = ['BTC-USD', 'ETH-USD', 'LINK-USD', 'XMR-USD', 'AAPL', 'SPY', 'NVDA', 'TSLA', 'EURUSD=X', 'MATIC-USD', 'PAXG-USD']
begin_date = '2022-01-01'


def clean_dict(slovar):
    ''' Iz slovarja odstrani odvečne elemente '''
    new_dict = dict()
    for key in slovar.keys():
        if key == 'formatted_date':
            new_dict['date'] = slovar[key]
        elif key == 'close':
            try:
                new_dict['price'] = round(slovar[key], 2)
            except:
                pass
    return new_dict

def shorten_list(seznam):
    sez = list()
    for i in seznam:
        sez.append(clean_dict(i))        
    return sez

def pripravi_imenik(ime_datoteke):
    ''' Če še ne obstaja, pripravi prazen imenik za dano datoteko '''
    imenik = os.path.dirname(ime_datoteke)
    if imenik:
        os.makedirs(imenik, exist_ok=True)

def zapisi_csv(slovarji, imena_polj, ime_datoteke):
    ''' Iz seznama slovarjev ustvari CSV datoteko z glavo '''
    pripravi_imenik(ime_datoteke)
    with open(ime_datoteke, 'w', encoding='utf-8') as csv_datoteka:
        writer = csv.DictWriter(csv_datoteka, fieldnames=imena_polj)
        writer.writeheader()
        for slovar in slovarji:
            writer.writerow(slovar)

def get_historic_data(seznam_parov, end_date):
    ''' Za vsak simbol ustvari csv dokument, ter
        v njega shrani zadnjo dnevno ceno za določeno casovno obdobje '''
    for simbol in seznam_parov:
        zacasni_sez = yf(simbol).get_historical_price_data( begin_date, str(end_date), 'daily')
        seznam_cen = zacasni_sez[simbol]['prices']
        seznam_cen = shorten_list(seznam_cen)
        for i in seznam_cen:
            i.update({'symbol_id': str(simbol)})
        zapisi_csv(seznam_cen,  ['symbol_id', 'date', 'price'], 'Podatki/Posamezni_simboli/' + str(simbol) + '.csv')

def get_symbols():
    ''' Vrne seznam csv datotek v mapi '''
    sez_datotek = list()
    for _, _, files in os.walk(r'Podatki/Posamezni_simboli'):
        for file in files:
            if (file.endswith('.csv')):
                sez_datotek.append(file)
    return sez_datotek

def get_symbols_list():
    ''' Vrne seznam simbolov v mapi '''
    sez_datotek = list()
    for _, _, files in os.walk(r'Podatki/Posamezni_simboli'):
        for file in files:
            if (file.endswith('.csv')):
                file = re.sub('.csv', '', file)
                sez_datotek.append(file)
    return sez_datotek

def merge_csv(seznam, csv_name):
    ''' Združi izbrane posamezne csv dokumente '''
    zacasni = list()
    for item in seznam:
         zacasni.append(pd.read_csv(r'Podatki/Posamezni_simboli/' + str(item)))
    df = pd.concat(zacasni, copy=False)
    df.to_csv('Podatki/'+ str(csv_name), index=False)

def preveri_ustreznost(simbol):
    ''' Preveri če simbol obstaja, če ne obstaja vrne 0, sicer pa 1 '''
    # Če bi dodali novejše simbole, je treba funkcijo posodobit
    data = yf(str(simbol)).get_historical_price_data('2023-05-03', '2023-05-04', 'daily')
    if isinstance(data[simbol], type(None)):
        return 0
    elif isinstance(data[simbol], dict):
        if len(data[simbol]) == 1:
            return 0
        else:
            return 1

def update_price_history():
    ''' Vzeto iz
        https://stackoverflow.com/questions/74813518/how-to-save-a-variable-and-read-it-on-the-next-run '''
    STORE = os.path.join(os.path.dirname(__file__), 'last_run.pickle')

    today = date.today()
    print('Today is', today)

    # Load the stored date from last run:
    if os.path.isfile(STORE):
        with open(STORE, 'rb') as store:
            last_run = pickle.load(store)
    else:
        print('No STORE detected. Assuming this is the first run...')
        last_run = today

    print('Last run was', last_run)
    if last_run < today:
        old = pd.read_csv(r'Podatki/price_history.csv')
        get_historic_data(get_symbols_list(), today)
        merge_csv(get_symbols(), 'price_history.csv')
        new = pd.read_csv(r'Podatki/price_history.csv')
        new_df = pd.concat([old, new]).reset_index(drop=True)
        df = new_df.drop_duplicates(subset=['symbol_id','date'], keep=False)

    # store todays run date for the next run:
    with open(STORE, 'wb') as store:
        pickle.dump(today, store)

    try:
        return df
    except UnboundLocalError:
        print('Vsa zgodovina je naložena!')
        pass
