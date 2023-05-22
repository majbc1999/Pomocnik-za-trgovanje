import os
import re
import csv

from datetime import date
from functools import wraps
from bottle import TEMPLATES, debug
from bottleext import get, post, run, request, template, redirect, static_file, url, response, template_user

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

from auth_public import *
from Podatki import get_history as gh
from graphs import graph_html, graph_cake, graph_stats, analyze

from Database import Repo
from modeli import *
from Services import AuthService

repo = Repo()
auth = AuthService(repo)


debug(True)

# Privzete nastavitve
SERVER_PORT = os.environ.get('BOTTLE_PORT', 8080)
RELOADER = os.environ.get('BOTTLE_RELOADER', True)
DB_PORT = os.environ.get('POSTGRES_PORT', 5432)

# Priklop na bazo
conn = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 


piskot = UporabnikCookie()


@get('/static/<filename:path>')
def static(filename):
   return static_file(filename, root='static')

def cookie_required(f):
    ''' Dekorator, ki zahteva veljaven piškotek. 
        Če piškotka ni, uporabnika preusmeri na stran za prijavo '''
    @wraps(f)
    def decorated( *args, **kwargs): 
        cookie = request.get_cookie('uporabnik')
        if cookie:
            return f(*args, **kwargs)
        
        return template('home.html')
    return decorated


#############################################################
#############      PRIJAVA IN REGISTRACIJA      #############
#############################################################

@get('/')
def zacetna_stran():
    return template('home.html',  pair=cur, naslov='Pomočnik za trgovanje')

@post('/prijava')
def prijava_post():
    global piskot
    uporabnisko_ime = request.forms.ime
    geslo = request.forms.geslo

    if not auth.obstaja_uporabnik(uporabnisko_ime):
        return template("home.html", napaka="Uporabnik s tem imenom ne obstaja")

    # Preveri ali sta uporabnisko_ime in geslo pravilna
    prijava = auth.prijavi_uporabnika(uporabnisko_ime, geslo)
    if prijava[0] != 0:
        # Nastavi piškotek
        response.set_cookie('uporabnik', uporabnisko_ime)

        # Potrebne podatke shrani v razred določen s piškotkom
        piskot = auth.from_piskot_to_param(request.get_cookie('uporabnik'))
        piskot.user_id = prijava[0]
        piskot.user_ime = prijava[1]
        piskot.sporocilo = ''
        redirect('/uporabnik')
    else:
        piskot.uspesna_prijava = False
        piskot.sporocilo = 'Napačno uporabinško ime ali geslo!'
        return template("prijava.html", napaka="Neuspešna prijava. Napačno geslo ali uporabniško ime.")



@get('/logout')
def logout():
    global piskot
    ''' Odjavi uporabnika in izbriše pikotek '''
    del(piskot)
    response.delete_cookie('uporabnik')
    redirect('/')

#############################################################

@get('/registracija')
def registracija_get():
    return template('registracija.html', naslov='Registracija')

@post('/registracija')
def registracija_post():
    global piskot
    ime = request.forms.name
    priimek = request.forms.surname
    datum_rojstva = request.forms.date_of_birth
    uporabnisko_ime = request.forms.user_name
    geslo = request.forms.password

    # Preveri da uporabnisko_ime še ni zasedeno
    if not auth.obstaja_uporabnik(uporabnisko_ime):
        piskot.uspesna_registracija = False
        piskot.sporocilo = 'Registracija ni možna, to uporabniško ime že obstaja.'
        redirect('/registracija')
        return template("home.html", napaka=f'Uporabniško ime {uporabnisko_ime} že obstaja')
    else:
        auth.dodaj_uporabnika(ime, priimek, datum_rojstva, uporabnisko_ime, geslo)
        response.set_cookie('uporabnik', uporabnisko_ime)
        piskot = auth.from_piskot_to_param(request.get_cookie('uporabnik'))
        piskot.sporocilo = ''
        redirect('/uporabnik')
    

#############################################################

@get('/uporabnik')
@cookie_required
def uporabnik():
    global piskot
    piskot.user_assets = repo.dobi_asset_by_user(asset, piskot.user_id)
    
    # V bazi posodobi price_history - če ne dela dodaj: import pandas
    df = gh.update_price_history()
    repo.posodobi_price_history(df)
    return template('uporabnik.html', uporabnik=cur)


#############################################################
##############             NALOŽBE             ##############
#############################################################

@get('/dodaj')
@cookie_required
def dodaj():
    global piskot
    piskot.sporocilo = ''
    seznam = repo.dobi_pare()
    return template('dodaj_par.html', pair=seznam, naslov='Dodaj naložbo')

@post('/dodaj_potrdi')
def dodaj_potrdi():
    ''' Doda nov par v tabelo pari '''
    global piskot
    symbol = request.forms.symbol
    name = request.forms.ime

    # Preveri ali vnešen simbol obstaja
    if gh.preveri_ustreznost('{}'.format(symbol)) == 0:
        piskot.pravilen_simbol = False
        piskot.sporocilo = 'Vnešen napačen simbol'
        redirect('/dodaj')
    else:
        # Vnese simbol v tabelo par
        repo.dodaj_par(symbol, name)
        gh.get_historic_data(['{}'.format(symbol)], date.today())
        repo.uvozi_Price_History('{}.csv'.format(symbol))
        gh.merge_csv(gh.get_symbols(), 'price_history.csv')
        piskot.pravilen_simbol = True
        piskot.sporocilo = 'Simbol uspešno dodan'
        redirect('/dodaj')


#############################################################

@get('/assets')
@cookie_required
def assets():
    seznam_asset = repo.dobi_asset_amount_by_user(piskot.user_id)
    return template('assets.html', asset=seznam_asset, naslov='Asset')

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
        repo.dobi_gen_id(pair, symbol, id_col="symbol")
    except:
        piskot.sporocilo = 'Napačen simbol!'
        redirect('/assets')

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
    redirect('/assets')

#############################################################

@get('/performance')
@cookie_required
def performance():
    global piskot
    # Naloži grafe, če smo program zagnali na novo
    if piskot.first_load_assets == True:
       # Pripravi default graf za /performance.html
        graph_html(piskot.user_id, piskot.user_assets) 
        # Posodobi graf cake.html
        graph_cake(piskot.user_id, str(date.today()))
        piskot.first_load_assets = False
        piskot.first_load_stats = True
    # Počisti cache, da se naloži nov graf 
    TEMPLATES.clear()
    return template('performance.html', assets=piskot.user_assets, naslov='Poglej napredek')

@post('/new_equity_graph')
def new_equity_graph():
    simboli_graf = request.forms.simboli
    seznam = re.split(r' ', simboli_graf)
    graph_html(piskot.user_id, seznam)
    return redirect('/performance')

@get('/Graphs/assets.html')
def Graf_assets():
    return template('Graphs/assets.html')

@get('/Graphs/cake.html')
def Graf_assets():
    return template('Graphs/cake.html')


#############################################################
#################         TRADES            #################
#############################################################

@get('/trades')
@cookie_required
def trades():
    seznam = repo.dobi_trade_delno(piskot.user_id)
    return template('trades.html', trade=seznam, naslov='Dodaj trade')

@post('/dodaj_trade')
def dodaj_trade():
    global  piskot
    simbol = request.forms.symbol
    TP = request.forms.TP
    PNL = request.forms.PNL

    # Preveri da je simbol veljaven
    try:
        # Preveri da smo vnesli pravilen simbol
        repo.dobi_gen_id(pair, simbol, id_col="symbol")
    except:
        sporocilo = 'Napačen simbol, če želite dodati trade za njega, ga najprej dodajte v tabelo pari!'
        redirect('/trades')

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
    redirect('/trades')


#############################################################

@get('/stats')
@cookie_required
def stats():
    global piskot
    seznam = repo.dobi_strategije(piskot.user_id)

    if piskot.first_load_stats == True:
        # Pripravi default tuple za /stats.html
        piskot.stats_tuple = graph_stats(piskot.user_id, 'All')
        piskot.first_load_stats = False
        piskot.first_load_assets = True
    TEMPLATES.clear()
    return template('stats.html', strategy=seznam, naslov='Statistika')

@post('/strategy')
def strategy():
    global piskot
    strategy = request.forms.strategy

    # V global tuple shrani statistiko  in posodobi graf
    piskot.stats_tuple = graph_stats(piskot.user_id, strategy)
    TEMPLATES.clear()
    return redirect('/stats')

@get('/Graphs/win_rate.html')
def Graf_assets():
    return template('Graphs/win_rate.html')

@get('/Graphs/win_by_type.html')
def Graf_assets():
    return template('Graphs/win_by_type.html')

@get('/Graphs/pnl_graph.html')
def Graf_assets():
    return template('Graphs/pnl_graph.html')

#############################################################

@get('/analysis')
@cookie_required
def stats():
    seznam = repo.dobi_strategije(piskot.user_id)
    return template('analysis.html', strategy=seznam, naslov='Analiza')

@post('/analyze')
def analyze_f():
    global piskot
    strat = request.forms.strategy
    duration = int(request.forms.duration)
    rr = int(request.forms.rr)
    target = int(request.forms.target)
    tip = request.forms.tip

    # V global tuple shrani rezultate analize in posodobi graf
    piskot.anl_stats = analyze(piskot.user_id, strat, duration, rr, target, tip)
    TEMPLATES.clear()
    return redirect('/analysis')


@get('/Graphs/win_rate_anl.html')
def Graf_assets():
    return template('Graphs/win_rate_anl.html')

#############################################################

if __name__ == '__main__':
    run(host='localhost', port=SERVER_PORT, reloader=RELOADER)
