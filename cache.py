#server
@get('/dodaj')
def dodaj():
    global sporocilo
    sporocilo = ""
    cur.execute("""
      SELECT symbol,name from pair
   """)
    return template('dodaj_par.html', pair=cur)


#server
@post('/buy_sell')
def buy_sell():
    global sporocilo

###
else:
        #print(row[0])
        amount = round(pnl + float(row[0]), 2)
        #print(amount)
        cur.execute("UPDATE  asset SET amount = {0} WHERE user_id = '{1}' AND symbol_id = '{2}'".format(amount, uid, simbol))
    conn.commit()


##
@get('/performance')
def performance():
    return template('performance.html')






if __name__ == "__main__":
    run(host='localhost', port=8080, reloader=True)

###############assets
 % if sporocilo == "":
        <div>{{sporocilo}}</div>


</div>
        <a href="/uporabnik" class="Button"><input type='button' value='Nazaj' /></a>
    </body>
########uporabnik
<ul>
                <li> <a href="/dodaj">Add assets</a></li>
                <li> <a href="/assets">Buy/Sell</a></li>
                <li><a href="/performance">View performance</a></li>
            </ul>

