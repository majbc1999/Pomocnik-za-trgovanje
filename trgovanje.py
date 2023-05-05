#!/usr/bin/python
# -*- encoding: utf-8 -*-

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

@get('/')
def zacetna_stran():
    cur.execute("""
      SELECT symbol,name from pair
   """)
    return template('zacetna_stran.html', pair=cur)

@get('/prijava')
def prijava():
    return template('prijava.html')

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