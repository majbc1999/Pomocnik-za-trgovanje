from auth import *
import csv

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki

conn = psycopg2.connect(database=db, host=host, user=user, password=password)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 


def ustvari_tabele():
    with open('trgovanje.sql') as f:
        koda = f.read()
    cur.execute(koda)
    conn.commit()
    print("Uspesno ustvaril tabele!")

ustvari_tabele()


def uvoziCSV(tabela):
    with open('podatki/{0}'.format(tabela)) as csvfile:
        podatki = csv.reader(csvfile)
        next(podatki)
        for r in podatki:
            r = [None if x in ('', '-') else x for x in r]
            if "trades.csv" in tabela:
                cur.execute("""
                    INSERT INTO trade
                    (user_id, symbol_id, type, strategy, RR, target, date, duration, TP, PNL)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id_trade
                """, r)
            elif "price_history.csv" in tabela:
                cur.execute("""
                    INSERT INTO price_history
                    (symbol_id, date, price)
                    VALUES (%s, %s, %s)
                """, r)
        conn.commit()
        print("Uspesno uvozil csv datoteko!")

def uvozSQL(tabela):
    with open('podatki/{0}'.format(tabela)) as sqlfile:
        koda = sqlfile.read()
        cur.execute(koda)
    conn.commit()
    print("Uspesno nalozil podatke!")

uvozSQL("app_user.sql")
uvozSQL("pair.sql")
uvoziCSV("price_history.csv")
uvoziCSV("trades.csv")
uvozSQL("asset.sql")
