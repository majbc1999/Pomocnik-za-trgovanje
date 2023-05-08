from bottleext import get, post, run, request, template, redirect, static_file, url

from auth_public import *

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

import os

import csv

from Podatki import get_history as gh

import hashlib

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

@get('/')
def zacetna_stran():
    return template('home.html', pair=cur)

@get('/registracija')
def registracija():
    return template('registracija.html')

@get('/users')
def users():
    cur.execute("SELECT name, surname, date_of_birth FROM app_user")
    return template('users.html', app_user=cur)

@get('/add_user')
def add_user():
    return template('add_user.html', name='', surname='', date_of_birth='', napaka=None)

@post('/add_user')
def add_user_post():
    name = request.forms.name
    surname = request.forms.surname
    date_of_birth = request.forms.date_of_birth
    try:
        cur.execute("INSERT INTO app_user (name, surname, date_of_birth) VALUES (%s, %s, %s) RETURNING id_user",
                    (name, surname, date_of_birth))
        conn.commit()
    except Exception as ex:
        conn.rollback()
        return template('add_user.html', name=name, surname=surname, date_of_birth=date_of_birth,
                        napaka='Zgodila se je napaka: %s' % ex)
    redirect(url('/users'))

@get('/trades')
def trades():
    cur.execute("SELECT symbol_id, type, strategy, RR, target, date, duration, TP, PNL FROM trade")
    return template('trades.html', trade=cur)

@get('/pairs')
def pairs():
    cur.execute("SELECT symbol, name FROM pair")
    return template('pairs.html', pair=cur)

@get('/assets')
def asset():
    cur.execute("""SELECT app_user.name, symbol_id, amount FROM asset 
    INNER JOIN app_user ON user_id = id_user 
    ORDER BY app_user.name """)
    return template('assets.html', asset=cur)

@post('/prijava')
def prijava_post():
    uporabnisko_ime = request.forms.getunicode("ime")
    geslo = request.forms.getunicode('geslo')
    global uspesna_prijava, sporocilo, uporabnik
    row = cur.execute("SELECT DISTINCT name FROM app_user WHERE user_name = '{0}' and password = '{1}'".format(uporabnisko_ime, geslo))
    row = cur.fetchone()
    if row != None:
        uporabnik = row[0]
        sporocilo = ""
        redirect(url('/uporabnik'))
    else:
        uspesna_prijava = False
        sporocilo = "Napačno uporabinško ime ali geslo!"
        redirect(url('/'))

uspesna_prijava = True        
sporocilo = ""
uporabnik = ""
pravilen_simbol = True

@get('/uporabnik')
def uporabnik():
    return template('uporabnik.html', uporabnik=cur)

@get('/dodaj')
def dodaj():
    cur.execute("""
      SELECT symbol,name from pair
   """)
    return template('dodaj_par.html', pair=cur)

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
        gh.get_historic_data(['{}'.format(symbol)])
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


if __name__ == "__main__":
    run(host='localhost', port=8080, reloader=True)