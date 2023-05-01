import csv
import os
import pandas as pd
from yahoofinancials import YahooFinancials as yf


trading_pairs = ['BTC-USD', 'ETH-USD', 'LINK-USD', 'XMR-USD', 'AAPL', 'SPY', 'NVDA', 'TSLA', 'EURUSD=X', 'MATIC-USD', 'PAXG-USD']

begin_date = '2022-01-01'
end_date = '2023-4-30'


def clean_dict(slovar):
    '''Iz slovarja odstrani odvečne elemente.'''
    new_dict = dict()
    for key in slovar.keys():
        if key == 'formatted_date':
            new_dict['date'] = slovar[key]
        elif key == 'close':
            new_dict['price'] = round(slovar[key], 2)
    return new_dict

def shorten_list(seznam):
    sez = list()
    for i in seznam:
        sez.append(clean_dict(i))        
    return sez

def pripravi_imenik(ime_datoteke):
    '''Ce se ne obstaja, pripravi prazen imenik za dano datoteko.'''
    imenik = os.path.dirname(ime_datoteke)
    if imenik:
        os.makedirs(imenik, exist_ok=True)

def zapisi_csv(slovarji, imena_polj, ime_datoteke):
    '''Iz seznama slovarjev ustvari CSV datoteko z glavo.'''
    pripravi_imenik(ime_datoteke)
    with open(ime_datoteke, 'w', encoding='utf-8') as csv_datoteka:
        writer = csv.DictWriter(csv_datoteka, fieldnames=imena_polj)
        writer.writeheader()
        for slovar in slovarji:
            writer.writerow(slovar)

def get_historic_data(seznam_parov):
    '''Za vsak simbol ustvari csv dokument, ter
    v njega shrani zadnjo dnevno ceno za določeno casovno obdobje'''
    for simbol in seznam_parov:
        zacasni_sez = yf(simbol).get_historical_price_data( begin_date, end_date, 'daily')
        seznam_cen = zacasni_sez[simbol]['prices']
        seznam_cen = shorten_list(seznam_cen)
        for i in seznam_cen:
            i.update({"symbol_id": str(simbol)})
        zapisi_csv(seznam_cen,  ['symbol_id', 'date', 'price'], 'Podatki/Posamezni_simboli/' + str(simbol) + '.csv')

def get_symbols():
    '''Vrne seznam csv datotek v mapi'''
    sez_datotek = list()
    for _, _, files in os.walk(r'Podatki/Posamezni_simboli'):
        for file in files:
            if (file.endswith('.csv')):
                sez_datotek.append(file)
    return sez_datotek

def merge_csv(seznam, csv_name):
    '''Zdruzi izbrane posamezne csv dokumente'''
    zacasni = list()
    for item in seznam:
         zacasni.append(pd.read_csv(r'Podatki/Posamezni_simboli/' + str(item)))
    df = pd.concat(zacasni, copy=False)
    df.to_csv('Podatki/'+ str(csv_name), index=False)


get_historic_data(trading_pairs)
merge_csv(get_symbols(), 'price_history.csv')
