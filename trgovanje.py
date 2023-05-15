from bottleext import get, post, run, request, template, redirect, static_file, url, response, template_user


from bottle import TEMPLATES

from auth_public import *

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

import os

import re

import csv

import pandas

from Podatki import get_history as gh

from graphs import graph_html, graph_cake, graph_stats, analyze

from datetime import date

import hashlib

from functools import wraps

# privzete nastavitve
SERVER_PORT = os.environ.get('BOTTLE_PORT', 8080)
RELOADER = os.environ.get('BOTTLE_RELOADER', True)
DB_PORT = os.environ.get('POSTGRES_PORT', 5432)

# PRIKLOP NA BAZO
conn = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 

# odkomentiraj, če želiš sporočila o napakah
# debug(True)

@get('/static/<filename:path>')
def static(filename):
   return static_file(filename, root='static')

user_ime = ""
uspesna_prijava = True        
sporocilo = ""
user_id = 0
user_assets  = []
pravilen_simbol = True
uspesna_registracija = True

########################### Prijava in registracija ###########################
@get('/')
def zacetna_stran():
    return template('home.html', pair=cur, naslov="Pomočnik za trgovanje")

def cookie_required(f):
    """
    Dekorator, ki zahteva veljaven piškotek. Če piškotka ni, uporabnika preusmeri na stran za prijavo.
    """
    @wraps(f)
    def decorated( *args, **kwargs): 
           
        cookie = request.get_cookie("uporabnik")
        if cookie:
            return f(*args, **kwargs)
        
        return template("home.html", napaka="Potrebna je prijava!")
        
    return decorated

@post('/prijava')
def prijava_post():
    uporabnisko_ime = request.forms.getunicode("ime")
    geslo = request.forms.getunicode('geslo')
    h = hashlib.blake2b()
    h.update(geslo.encode(encoding='utf-8'))
    hashed_pass = h.hexdigest()
    print(hashed_pass)
    global uspesna_prijava, sporocilo, user_id, user_ime
    row = cur.execute("SELECT DISTINCT id_user, name FROM app_user WHERE user_name = '{0}' and password = '{1}'".format(uporabnisko_ime, hashed_pass))
    row = cur.fetchone()
    if row != None:
        user_id = row[0]
        user_ime = row[1]
        sporocilo = ""
        response.set_cookie("uporabnik", uporabnisko_ime)
        redirect(url('/uporabnik'))
    else:
        uspesna_prijava = False
        sporocilo = "Napačno uporabinško ime ali geslo!"
        redirect(url('/'))

@get('/registracija')
def registracija_get():
    return template('registracija.html', naslov = "Registracija")

@post('/registracija')
def registracija_post():
    ime = request.forms.name
    priimek = request.forms.surname
    datum_rojstva = request.forms.date_of_birth
    uporabnisko_ime = request.forms.user_name
    geslo = request.forms.password
    global uspesna_registracija, sporocilo
    row = cur.execute("SELECT name FROM app_user WHERE user_name = '{}'".format(uporabnisko_ime))
    row = cur.fetchone()
    if row != None:
        uspesna_registracija = False
        sporocilo = "Registracija ni možna, to uporabniško ime že obstaja."
        redirect('/registracija')
    else:
        h = hashlib.blake2b()
        h.update(geslo.encode(encoding='utf-8'))
        hashed_pass = h.hexdigest()
        cur.execute("INSERT INTO app_user (name, surname, date_of_birth, user_name, password) VALUES (%s, %s, %s, %s, %s) RETURNING id_user",
                (ime, priimek, datum_rojstva, uporabnisko_ime, hashed_pass))
        conn.commit()
        sporocilo = ""
        redirect('/uporabnik')

@get('/logout')
def logout():

    response.delete_cookie("uporabnik")

    redirect(url('/'))

#############################################################################

"""SELECT app_user.name, symbol_id, amount FROM asset 
    INNER JOIN app_user ON user_id = id_user 
    ORDER BY app_user.name """

@get('/uporabnik')
@cookie_required
def uporabnik():
    global user_id, user_assets, stats_tuple
    cur.execute("""SELECT symbol_id FROM asset WHERE user_id = {}""".format(user_id))
    seznam = cur.fetchall()
    for i in seznam:
        user_assets.append(i[0])
    # Posodobi price_history
    df = gh.update_price_history()
    try:
        for i in df.index:
            cur.execute('''
                INSERT INTO price_history (symbol_id, date, price)
                VALUES (%s, %s, %s)''', (df['symbol_id'][i], df['date'][i], df['price'][i]))
        conn.commit()
    except AttributeError:
        pass
    # Pripravi default graf za /performance.html
    graph_html(user_id, user_assets)
    # Pripravi default tuple za /stats.html
    stats_tuple = graph_stats(user_id, 'All')
    print(request.get_cookie("uporabnik"))
    return template('uporabnik.html', uporabnik=cur)


########################### Pari-dodajanje ###########################
@get('/dodaj')
@cookie_required
def dodaj():
    #ce je global sporocilo = ""ga ne izpise ker ga da skos na "", ce pa ni tega pa ne zgine
    global sporocilo
    sporocilo = ""
    cur.execute("""
      SELECT symbol,name from pair
   """)
    return template('dodaj_par.html', pair=cur, naslov="Dodaj naložbo")

@post('/dodaj_potrdi')
def dodaj_potrdi():
    global pravilen_simbol, sporocilo
    symbol = request.forms.symbol
    name = request.forms.ime
    if gh.preveri_ustreznost('{}'.format(symbol)) == 0:
        pravilen_simbol = False
        sporocilo = "Vnešen napačen simbol"
        redirect(url('/dodaj'))
    else:
        cur.execute("INSERT INTO pair (symbol, name) VALUES (%s, %s)", (symbol, name))
        conn.commit()
        gh.get_historic_data(['{}'.format(symbol)], date.today())
        uvozi_Price_History('{}.csv'.format(symbol))
        pravilen_simbol = True
        sporocilo = "Simbol uspešno dodan"
        redirect(url('/dodaj'))

def uvozi_Price_History(tabela):
    # ce uvozim iz uvoz_podatkov vrne error 'no module named auth'
    with open('Podatki/Posamezni_simboli/{0}'.format(tabela)) as csvfile:
        podatki = csv.reader(csvfile)
        next(podatki)
        for r in podatki:
            r = [None if x in ('', '-') else x for x in r]
            cur.execute("""
                INSERT INTO price_history
                (symbol_id, date, price)
                VALUES (%s, %s, %s)
            """, r)
        conn.commit()
        print("Uspesno uvozil csv datoteko!")

#############################################################################
######################## Assets - pregled, dodajanje ########################
@get('/assets')
@cookie_required
def asset():
    cur.execute("""
        SELECT symbol_id, amount 
        FROM asset 
        WHERE user_id = {} ORDER BY amount
    """.format(user_id))
    return template('assets.html', naslov = "Asset", asset=cur)

@post('/buy_sell')
def buy_sell():
    global sporocilo
    symbol = request.forms.symbol
    datum = request.forms.datum
    tip = request.forms.tip
    amount = request.forms.amount
    amount = float(amount)
    amount = sign(amount, tip)
    check_user(user_id)
    row = cur.execute("SELECT symbol FROM pair WHERE symbol = '{}'".format(symbol))
    row = cur.fetchone()
    if row != None:
        cur.execute("INSERT INTO trade (user_id, symbol_id, type, date, pnl) VALUES (%s, %s, %s, %s, %s) RETURNING id_trade",
                    (user_id, symbol, tip, datum, amount))
        conn.commit()
        trade = [user_id, symbol, float(amount)]
        trade_result(trade)
        sporocilo = "Transakcija potrjena"
        redirect(url('/assets'))
    else:
        sporocilo = "Napačen simbol!"
        redirect(url('/assets'))

def sign(amount: float, bs):
    if bs == 'Buy':
        return abs(amount)
    elif bs == 'Sell':
         return -abs(amount)
    else:
        return print(bs)

def trade_result(trade):
    uid = trade[0]
    simbol = trade[1]
    pnl = trade[2]
    row = cur.execute("SELECT amount FROM asset WHERE user_id = '{0}' AND symbol_id = '{1}'".format(uid, simbol))
    row = cur.fetchone()
    if row == None:
        cur.execute("INSERT INTO asset (user_id, symbol_id, amount) VALUES (%s, %s, %s)", (uid, simbol, pnl))
    else:
        amount = round(pnl + float(row[0]), 2)
        cur.execute("UPDATE  asset SET amount = {0} WHERE user_id = '{1}' AND symbol_id = '{2}'".format(amount, uid, simbol))
    conn.commit()

def check_user(user_id):
    if user_id > 0:
        pass
    else:
        print('user_id is still 0')
        ValueError
    
#############################################################################
######################## Trades - pregled, dodajanje ########################
@get('/trades')
@cookie_required
def trades():
    cur.execute("""SELECT symbol_id, type, strategy, RR, target, date, duration, TP, PNL FROM trade
    WHERE user_id = {} ORDER BY symbol_id """.format(user_id))
    return template('trades.html', trade=cur, naslov="Dodaj trade")

@post('/dodaj_trade')
def dodaj_trade():
    global sporocilo, user_id
    simbol = request.forms.symbol
    tip = request.forms.type
    strategija = request.forms.strategy
    RR = request.forms.RR
    tarča = request.forms.target
    datum = request.forms.date
    trajanje = request.forms.duration
    TP = request.forms.TP
    PNL = request.forms.PNL
    check_user(user_id)
    row = cur.execute("SELECT symbol FROM pair WHERE symbol = '{}'".format(simbol))
    row = cur.fetchone()
    if row != None:
        if TP == '':
            cur.execute("INSERT INTO trade (user_id, symbol_id, type, strategy, rr, target, date, duration, pnl) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_trade",
                        (user_id, simbol, tip, strategija, RR, tarča, datum, trajanje, PNL))
        else:
            cur.execute("INSERT INTO trade (user_id, symbol_id, type, strategy, rr, target, date, duration, tp, pnl) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_trade",
                        (user_id, simbol, tip, strategija, RR, tarča, datum, trajanje, TP, PNL))
        conn.commit()
        pnl_trade(user_id, simbol, PNL)
        sporocilo = "Trade dodan"
        redirect(url('/trades'))
        sporocilo = ""
    else:
        sporocilo = "Napačen simbol, če želite dodati trade za njega, ga najprej dodajte v tabelo pari!"
        redirect(url('/trades'))

def pnl_trade(user_id, simbol, pnl):
    dollar = re.findall(r'\$', pnl)
    # PNL doda pri assetu na katerem je trade
    if dollar == []:
        trade = [user_id, simbol, float(pnl)]
        trade_result(trade)
    # PNL dodda pri USD
    elif dollar != []:
        pnl = re.sub('\$','',pnl)
        trade = [user_id, 'USD', float(pnl)]
        trade_result(trade)

#kako dodati da bo RR in tarča le decimalke, ne text (numeric ne gre so samo cela števila)
#kako dodati da bo TP lahko dodal v tabelo '' ker ni nujno da imaš TP



#############################################################################
@get('/performance')
@cookie_required
def performance():
    cur.execute("""SELECT symbol_id, amount FROM asset
    WHERE user_id = {}""".format(user_id))
    graph_cake(user_id, str(date.today()))
    TEMPLATES.clear()
    return template('performance.html', assets=cur, naslov = "Poglej napredek")


@post('/new_equity_graph')
def new_equity_graph():
    simboli_graf = request.forms.simboli
    seznam = re.split(r' ', simboli_graf)
    #########################################################
    ##### Tudi to ne dela zaradi - : if request.forms.BTC-USD == 1:
    ##### Ne obarva item, ne zazna ga kot iterable ampak string?
    #for item in user_assets:
    #    seznam.append(exec("request.forms.{}".format(item)))
    #print(seznam)
    #########################################################
    graph_html(user_id, seznam)
    return redirect(url('/performance'))

@get('/Graphs/assets.html')
def Graf_assets():
    return template('Graphs/assets.html')

@get('/Graphs/cake.html')
def Graf_assets():
    return template('Graphs/cake.html')
#############################################################################
@get('/stats')
@cookie_required
def stats():
    cur.execute("""SELECT strategy FROM trade
    WHERE user_id = {} AND (type = 'L' OR type = 'S') GROUP BY strategy""".format(user_id))
    return template('stats.html', strategy=cur, naslov = "Statistika")

@post('/strategy')
def strategy():
    global stats_tuple
    strategy = request.forms.strategy
    stats_tuple = graph_stats(user_id, strategy)
    TEMPLATES.clear()
    return redirect(url('/stats'))

stats_tuple = tuple()

@get('/Graphs/win_rate.html')
def Graf_assets():
    return template('Graphs/win_rate.html')

@get('/Graphs/win_by_type.html')
def Graf_assets():
    return template('Graphs/win_by_type.html')

@get('/Graphs/pnl_graph.html')
def Graf_assets():
    return template('Graphs/pnl_graph.html')
#############################################################################
@get('/analysis')
@cookie_required
def stats():
    cur.execute("""SELECT strategy FROM trade
    WHERE user_id = {} AND (type = 'L' OR type = 'S') GROUP BY strategy""".format(user_id))
    return template('analysis.html', strategy=cur, naslov = "Analiza")

@post('/analyze')
def analyze_f():
    global anl_stats
    strat = request.forms.strategy
    duration = int(request.forms.duration)
    rr = int(request.forms.rr)
    target = int(request.forms.target)
    tip = request.forms.tip
    anl_stats = analyze(user_id, strat, duration, rr, target, tip)
    TEMPLATES.clear()
    return redirect(url('/analysis'))

anl_stats = (0, 0, 0, 0, 0, 0)

@get('/Graphs/win_rate_anl.html')
def Graf_assets():
    return template('Graphs/win_rate_anl.html')

#############################################################################

if __name__ == "__main__":
    run(host='localhost', port=8080, reloader=True)
