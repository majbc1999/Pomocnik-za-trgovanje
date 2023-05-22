import os
import re

from datetime import date
from functools import wraps

from bottleext import get, post, run, request, template, redirect, static_file, url, response, TEMPLATES

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

from auth_public import *
from Podatki import get_history as gh
from Graphs import Graf

from Database import Repo
from modeli import *
from Services import AuthService


repo = Repo()
auth = AuthService(repo)
graf = Graf()
piskot = UporabnikCookie()


# Privzete nastavitve
SERVER_PORT = os.environ.get('BOTTLE_PORT', 8080)
RELOADER = os.environ.get('BOTTLE_RELOADER', True)
DB_PORT = os.environ.get('POSTGRES_PORT', 5432)

# Priklop na bazo
conn = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 


@get('/static/<filename:path>')
def static(filename):
   return static_file(filename, root='static')

def cookie_required(f):
    ''' Dekorator, ki zahteva veljaven piškotek '''
    @wraps(f)
    def decorated( *args, **kwargs): 
        cookie = request.get_cookie('uporabnik')
        if cookie:
            return f(*args, **kwargs)
        redirect('/')
    return decorated

@get('/Graphs/<ime>.html')
def Graf_assets(ime: str):
    return template(f'Graphs/{ime}.html')


#############################################################
#############      PRIJAVA IN REGISTRACIJA      #############
#############################################################

@get('/')
def zacetna_stran():
    return template('prijava.html', uspesna_prijava=True, naslov='Pomočnik za trgovanje')

@post('/prijava')
def prijava_post():
    global piskot
    uporabnisko_ime = request.forms.ime
    geslo = request.forms.geslo

    if not auth.obstaja_uporabnik(uporabnisko_ime):
        piskot.sporocilo = 'Uporabnik s tem imenom ne obstaja'
        return template('prijava.html', uspesna_prijava=False, naslov='Pomočnik za trgovanje')

    prijava = auth.prijavi_uporabnika(uporabnisko_ime, geslo)
    if prijava[0] == 0:
        piskot.sporocilo = 'Napačno uporabinško ime ali geslo!'
        return template('prijava.html',  uspesna_prijava=False, naslov='Pomočnik za trgovanje')
    
    # Nastavi piškotek
    response.set_cookie('uporabnik', uporabnisko_ime)
    # Potrebne podatke shrani v razred določen s piškotkom
    piskot = auth.from_piskot_to_param(request.get_cookie('uporabnik'))
    piskot.user_id = prijava[0]
    piskot.user_ime = prijava[1]
    piskot.sporocilo = ''
    redirect(f'/{piskot.user_id}/index')

@get('/odjava')
def logout():
    response.delete_cookie('uporabnik')
    redirect('/')

#############################################################

@get('/registracija')
def registracija_get():
    return template('registracija.html', uspesna_registracija = True, naslov='Registracija')

@post('/registracija')
def registracija_post():
    global piskot
    ime = request.forms.name
    priimek = request.forms.surname
    datum_rojstva = request.forms.date_of_birth
    uporabnisko_ime = request.forms.user_name
    geslo = request.forms.password

    if not auth.obstaja_uporabnik(uporabnisko_ime):
        piskot.sporocilo = 'Registracija ni možna, to uporabniško ime že obstaja.'
        return template('registracija.html', uspesna_registracija = False, naslov='Registracija')

    auth.dodaj_uporabnika(ime, priimek, datum_rojstva, uporabnisko_ime, geslo)
    piskot.sporocilo = 'Registracija uspešna!'
    return template('prijava.html',  uspesna_prijava = False, naslov='Pomočnik za trgovanje')    

#############################################################

@get('/<id>/index')
@cookie_required
def index(id: int):
    global piskot
    piskot.user_assets = repo.dobi_asset_by_user(asset, id)

    # V bazi posodobi price_history
    df = gh.update_price_history()
    repo.posodobi_price_history(df)
    return template('index.html')

@get('/<id>/uredi_profil')
@cookie_required
def uredi_profil(id: int):


    return template('uredi_profil.html', sprememba=False, naslov='Uredi profil')   

@post('/posodobi')
def posodobi(id: int):
    global piskot
    
    piskot.sporocilo = "Sprememba uspešna!"
    return template('uredi_profil.html', sprememba=True, naslov='Uredi profil') 


#############################################################
##############             NALOŽBE             ##############
#############################################################

@get('/<id>/pregled_nalozb')
@cookie_required
def dodaj(id: int):
    global piskot
    piskot.sporocilo = ''
    seznam = repo.dobi_pare()
    return template('pregled_nalozb.html', pravilen_simbol=True, pairs=seznam, naslov='Dodaj naložbo')

@post('/dodaj_par')
def dodaj_par():
    ''' Doda nov par v tabelo pari '''
    global piskot
    symbol = request.forms.symbol
    name = request.forms.ime

    # Preveri ali vnešen simbol obstaja
    if gh.preveri_ustreznost(f'{symbol}') == 0:
        piskot.sporocilo = 'Vnešen napačen simbol'
        return template('pregled_nalozb.html', pravilen_simbol=False, naslov='Dodaj naložbo')

    # Vnese simbol v tabelo par
    repo.dodaj_par(symbol, name)
    gh.get_historic_data(['{}'.format(symbol)], date.today())
    repo.uvozi_Price_History('{}.csv'.format(symbol))
    gh.merge_csv(gh.get_symbols(), 'price_history.csv')
    piskot.sporocilo = 'Simbol uspešno dodan'
    return template('pregled_nalozb.html', pravilen_simbol=True, naslov='Dodaj naložbo')

#############################################################

@get('/<id>/nalozbe')
@cookie_required
def nalozbe(id: int):
    seznam = repo.dobi_asset_amount_by_user(id)
    piskot.sporocilo = ''
    return template('nalozbe.html', assets=seznam, napaka=False, naslov='Asset')

@post('/buy_sell')
def buy_sell():
    ''' Če kupimo ali prodamo naložbo, ta funkcija
        vnese spremembe v tabelo assets in doda trade '''
    global piskot
    symbol = request.forms.symbol
    datum = request.forms.datum
    tip = request.forms.tip
    amount = float(repo.sign(request.forms.amount, tip))

    try:
        # Preveri da smo vnesli pravilen simbol
        if repo.dobi_gen_id(pair, symbol, id_col="symbol"):
            pass
    except Exception:
        piskot.sporocilo = 'Napačen simbol!'
        seznam = repo.dobi_asset_amount_by_user(piskot.user_id)
        return template('nalozbe.html', assets=seznam, napaka=True, naslov='Asset')

    # Zabeleži trade v tabelo trades
    trejd = trade(  user_id = piskot.user_id,
                    symbol_id = symbol, 
                    type = tip,
                    date = datum, 
                    pnl = amount
                )
    repo.dodaj_gen(trejd, serial_col='id_trade')

    # Vnese spremembo v tabelo assets
    repo.trade_result(piskot.user_id, symbol, amount)
    piskot.sporocilo = 'Transakcija potrjena'
    seznam = repo.dobi_asset_amount_by_user(piskot.user_id)
    return template('nalozbe.html', assets=seznam, napaka=False, naslov='Asset')


#############################################################

@get('/<id>/napredek')
@cookie_required
def performance(id: int):
    global piskot
    graf.graph_html(piskot.user_id, piskot.user_assets) 
    graf.graph_cake(piskot.user_id)
    TEMPLATES.clear()
    return template('performance.html', assets=piskot.user_assets, naslov='Poglej napredek')

@post('/new_equity_graph')
def new_equity_graph():
    global piskot
    simboli_graf = request.forms.simboli
    seznam = re.split(r' ', simboli_graf)
    graf.graph_html(piskot.user_id, seznam)
    TEMPLATES.clear()
    return template('performance.html', assets=piskot.user_assets, naslov='Poglej napredek')


#############################################################
#################         TRADES            #################
#############################################################

@get('/<id>/trades')
@cookie_required
def trades(id: int):
    piskot.sporocilo = ''
    seznam = repo.dobi_trade_delno(id)
    return template('trades.html', trade=seznam, naslov='Dodaj trade')

@post('/dodaj_trade')
def dodaj_trade():
    global  piskot
    simbol = request.forms.symbol
    TP = request.forms.TP
    PNL = request.forms.PNL

    try: # Preveri ali vnešen simbol obstaja
        if repo.dobi_gen_id(pair, simbol, id_col="symbol"):
            if TP == '':
                TP = psycopg2.extensions.AsIs('NULL')
            trejd = trade(  user_id = piskot.user_id,
                            symbol_id = simbol, 
                            type = request.forms.type,
                            strategy = request.forms.strategy,
                            rr = request.forms.RR,
                            target = request.forms.target,
                            date = request.forms.date, 
                            duration = request.forms.duration,
                            tp = TP,
                            pnl = PNL
                        )
            # Zabeleži trade v tabelo trades
            repo.dodaj_gen(trejd, serial_col='id_trade')
            # Izid trada poračuna v asset
            repo.pnl_trade(piskot.user_id, simbol, PNL)
            piskot.sporocilo = 'Trade dodan'
    except:
        piskot.sporocilo = 'Napačen simbol, če želite dodati trade za njega, ga najprej dodajte v tabelo pari!'

    seznam = repo.dobi_trade_delno(piskot.user_id)
    return template('trades.html', trade=seznam, naslov='Dodaj trade')


#############################################################

@get('/<id>/statistika')
@cookie_required
def stats(id: int):
    global piskot
    seznam = repo.dobi_strategije(id)
    piskot.stats_tuple = graf.graph_stats(piskot.user_id, 'All')
    TEMPLATES.clear()
    return template('stats.html', strategy=seznam, naslov='Statistika')

@post('/strategy')
def strategy():
    global piskot
    strategy = request.forms.strategy
    piskot.stats_tuple = graf.graph_stats(piskot.user_id, strategy)
    TEMPLATES.clear()

    seznam = repo.dobi_strategije(piskot.user_id)
    return template('stats.html', strategy=seznam, naslov='Statistika')

#############################################################

@get('/<id>/analiza')
@cookie_required
def analyze_main(id: int):
    seznam = repo.dobi_strategije(id)
    return template('analysis.html', strategy=seznam, naslov='Analiza')

@post('/analyze')
def analyze_f():
    global piskot
    piskot.anl_stats = graf.analyze( piskot.user_id, 
                                request.forms.strategy, 
                                int(request.forms.duration), 
                                int(request.forms.rr), 
                                int(request.forms.target), 
                                request.forms.tip)
    TEMPLATES.clear()
    seznam = repo.dobi_strategije(piskot.user_id)
    return template('analysis.html', strategy=seznam, naslov='Analiza')

#############################################################

if __name__ == '__main__':
    run(host='localhost', port=SERVER_PORT, reloader=RELOADER)
