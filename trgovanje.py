#!/usr/bin/python
# -*- encoding: utf-8 -*-

from bottle import *
# uvozimo bottle.py
from bottleext import get, post, run, request, template, redirect, static_file, url

# uvozimo ustrezne podatke za povezavo
from auth_public import *

# uvozimo psycopg2
import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki

import os

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

#skrivnost = 'laqwXUtKfHTp1SSpnkSg7VbsJtCgYS89QnvE7PedkXqbE8pPj7VeRUwqdXu1Fr1kEkMzZQAaBR93PoGWks11alfe8y3CPSKh3mEQ'

#napakaSporocilo = None
#def nastaviSporocilo(sporocilo = None):
    #global napakaSporocilo
    #staro = napakaSporocilo
    #napakaSporocilo = sporocilo
    #return staro 

#funkcija za piškotke
#def id_uporabnik():
    #if request.get_cookie("id", secret = skrivnost):
    #    piskotek = request.get_cookie("id", secret = skrivnost)
    #    return piskotek
    #else:
    #    return 0

@get('/')
def zacetna_stran():
    return template('home.html', pair=cur)

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
        cur.execute("INSERT INTO app_user (name, surname, date_of_birth, user_name, password) VALUES (%s, %s, %s, %s, %s) RETURNING id_user",
                (ime, priimek, datum_rojstva, uporabnisko_ime, geslo))
        conn.commit()
        sporocilo = ""
        redirect('/uporabnik')

uspesna_registracija = True
sporocilo = ""

#@get('/users')
#def users():
#    cur.execute("SELECT name, surname, date_of_birth FROM app_user")
#    return template('users.html', app_user=cur)


@get('/trades')
def trades():
    cur.execute("SELECT symbol_id, type, strategy, RR, target, date, duration, TP, PNL FROM trade")
    return template('trades.html', trade=cur)

@get('/pairs')
def pairs():
    cur.execute("SELECT symbol, name FROM pair")
    return template('pairs.html', pair=cur)

@get('/asset')
def asset():
    cur.execute("""SELECT app_user.name, symbol_id, amount FROM asset 
    INNER JOIN app_user ON user_id = id_user 
    ORDER BY app_user.name """)
    return template('asset.html', asset=cur)



######################################################################
# poženemo strežnik na podanih vratih, npr. http://localhost:8080/
if __name__ == "__main__":
    run(host='localhost', port=SERVER_PORT, reloader=RELOADER)