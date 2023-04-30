import json

from yahoofinancials import YahooFinancials

cryptocurrencies = ['BTC-USD']
yahoo_financials_cryptocurrencies = YahooFinancials(cryptocurrencies)

daily_crypto_prices = yahoo_financials_cryptocurrencies.get_historical_price_data('2023-04-27', '2023-4-29', 'daily')


prices_list = daily_crypto_prices["BTC-USD"]["prices"]

def clean_dict(slovar):
    new_dict = dict()
    for key in slovar.keys():
        if key == 'close' or key == 'formatted_date':
            new_dict[key] = slovar[key]
    slovar = new_dict
    return slovar

def shorten_list(seznam):
    sez = list()
    for i in seznam:
        sez.append(clean_dict(i))        
    return sez

print(shorten_list(prices_list))
