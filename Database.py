import auth_public as auth

import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki

from typing import List, TypeVar, Type
from modeli import *
from csv import reader
from re import sub, findall
from datetime import date
from pandas import DataFrame
from dataclasses import fields


# Ustvarimo generično TypeVar spremenljivko. Dovolimo le naše entitene, ki jih imamo tudi v bazi
# kot njene vrednosti. Ko dodamo novo entiteno, jo moramo dodati tudi v to spremenljivko.
T = TypeVar(
    "T",
    app_user,
    pair,
    price_history,
    asset,
    trade
    )

class Repo:

    def __init__(self):
        self.conn = psycopg2.connect(database=auth.db, host=auth.host, user=auth.user, password=auth.password, port=5432)
        self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


    def dobi_gen(self, typ: Type[T], take=10, skip=0) -> List[T]:
        """ 
        Generična metoda, ki za podan vhodni dataclass vrne seznam teh objektov iz baze.
        Predpostavljamo, da je tabeli ime natanko tako kot je ime posameznemu dataclassu.
        """

        # ustvarimo sql select stavek, kjer je ime tabele typ.__name__ oz. ime razreda
        tbl_name = typ.__name__
        sql_cmd = f'''SELECT * FROM {tbl_name} LIMIT {take} OFFSET {skip};'''
        self.cur.execute(sql_cmd)
        return [typ.from_dict(d) for d in self.cur.fetchall()]
        #return [d for d in self.cur.fetchall()]
    
    def dobi_gen_id(self, typ: Type[T], id: int | str, id_col = "id") -> T:
        """
        Generična metoda, ki vrne dataclass objekt pridobljen iz baze na podlagi njegovega idja.
        """
        tbl_name = typ.__name__
        sql_cmd = f'SELECT * FROM {tbl_name} WHERE {id_col} = %s';
        self.cur.execute(sql_cmd, (id,))

        d = self.cur.fetchone()

        if d is None:
            raise Exception(f'Vrstica z id-jem {id} ne obstaja v {tbl_name}');
    
        return d

########################################################################################################
########################################################################################################
########################################################################################################




    def izbrisi_gen(self,  typ: Type[T], id: int | str, id_col = "id"):
        """
        Generična metoda, ki vrne dataclass objekt pridobljen iz baze na podlagi njegovega idja.
        """
        tbl_name = typ.__name__
        sql_cmd = f'Delete  FROM {tbl_name} WHERE {id_col} = %s';
        self.cur.execute(sql_cmd, (id,))
        self.conn.commit()

       

    
    def dodaj_gen(self, typ: T, serial_col="id", auto_commit=True):
        """
        Generična metoda, ki v bazo doda entiteto/objekt. V kolikor imamo definiran serial
        stolpec, objektu to vrednost tudi nastavimo.
        """

        tbl_name = type(typ).__name__

        cols =[c.name for c in fields(typ) if c.name != serial_col]
        
        sql_cmd = f'''
        INSERT INTO {tbl_name} ({", ".join(cols)})
        VALUES
        ({self.cur.mogrify(",".join(['%s']*len(cols)), [getattr(typ, c) for c in cols]).decode('utf-8')})
        '''

        if serial_col != None:
            sql_cmd += f'RETURNING {serial_col}'

        self.cur.execute(sql_cmd)

        if serial_col != None:
            serial_val = self.cur.fetchone()[0]

            # Nastavimo vrednost serial stolpca
            setattr(typ, serial_col, serial_val)

        if auto_commit: self.conn.commit()

        # Dobro se je zavedati, da tukaj sam dataclass dejansko
        # "mutiramo" in ne ustvarimo nove reference. Return tukaj ni niti potreben.
      
    def dodaj_gen_list(self, typs: List[T], serial_col="id"):
        """
        Generična metoda, ki v bazo zapiše seznam objekton/entitet. Uporabi funkcijo
        dodaj_gen, le da ustvari samo en commit na koncu.
        """

        if len(typs) == 0: return # nič za narest

        # drugače dobimo tip iz prve vrstice
        typ = typs[0]

        tbl_name = type(typ).__name__

        cols =[c.name for c in fields(typ) if c.name != serial_col]
        sql_cmd = f'''
            INSERT INTO {tbl_name} ({", ".join(cols)})
            VALUES
            {','.join(
                self.cur.mogrify(f'({",".join(["%s"]*len(cols))})', i.to_dict()).decode('utf-8')
                for i in typs
                )}
        '''

        if serial_col != None:
            sql_cmd += f' RETURNING {serial_col};'

        self.cur.execute(sql_cmd)

        if serial_col != None:
            res = self.cur.fetchall()

            for i, d in enumerate(res):
                setattr(typs[i], serial_col, d[0])

        self.conn.commit()



    def posodobi_gen(self, typ: T, id_col = "id", auto_commit=True):
        """
        Generična metoda, ki posodobi objekt v bazi. Predpostavljamo, da je ime pripadajoče tabele
        enako imenu objekta, ter da so atributi objekta direktno vezani na ime stolpcev v tabeli.
        """

        tbl_name = type(typ).__name__
        
        id = getattr(typ, id_col)
        # dobimo vse atribute objekta razen id stolpca
        fields = [c.name for c in fields(typ) if c.name != id_col]

        sql_cmd = f'UPDATE {tbl_name} SET \n ' + \
                    ", \n".join([f'{field} = %s' for field in fields]) +\
                    f'WHERE {id_col} = %s'
        
        # iz objekta naredimo slovar (deluje samo za dataclasses_json)
        d = typ.to_dict()

        # sestavimo seznam parametrov, ki jih potem vsatvimo v sql ukaz
        parameters = [d[field] for field in fields]
        parameters.append(id)

        # izvedemo sql
        self.cur.execute(sql_cmd, parameters)
        if auto_commit: self.conn.commit()
        

    def posodobi_list_gen(self, typs : List[T], id_col = "id"):
        """
        Generična metoda, ki  posodobi seznam entitet(objektov). Uporabimo isti princip
        kot pri posodobi_gen funkciji, le da spremembe commitamo samo enkrat na koncu.
        """
        
        # Posodobimo vsak element seznama, pri čemer sprememb ne comitamo takoj na bazi
        for typ in typs:
            self.posodobi_gen(typ, id_col=id_col, auto_commit=False)

        # Na koncu commitamo vse skupaj
        self.conn.commit()


    def camel_case(self, s):
        """
        Pomožna funkcija, ki podan niz spremeni v camel case zapis.
        """
        
        s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
        return ''.join(s)     

    def col_to_sql(self, col: str, col_type: str, use_camel_case=True, is_key=False):
        """
        Funkcija ustvari del sql stavka za create table na podlagi njegovega imena
        in (python) tipa. Dodatno ga lahko opremimo še z primary key omejitvijo
        ali s serial lastnostjo. Z dodatnimi parametri, bi lahko dodali še dodatne lastnosti.
        """

        # ali stolpce pretvorimo v camel case zapis?
        if use_camel_case:
            col = self.camel_case(col)
        
        match col_type:

            case "int":
                return f'"{col}" BIGINT{" PRIMARY KEY" if  is_key else ""}'
            case "int32":
                return f'"{col}" BIGINT{" PRIMARY KEY" if  is_key else ""}'
         
            case "int64":
                return f'"{col}" BIGINT{" PRIMARY KEY" if  is_key else ""}'
            case "float":
                return f'"{col}" FLOAT'
            case "float32":
                return f'"{col}" FLOAT'
            case "float64":
                return f'"{col}" FLOAT'
        
        # če ni ujemanj stolpec naredimo kar kot text
        return f'"{col}" TEXT{" PRIMARY KEY" if  is_key else ""}'
    
    def df_to_sql_create(self, df: DataFrame, name: str, add_serial=False, use_camel_case=True) -> str:
        """
        Funkcija ustvari in izvede sql stavek za create table na podlagi podanega pandas DataFrame-a. 
        df: DataFrame za katerega zgradimo sql stavek
        name: ime nastale tabele v bazi
        add_serial: opcijski parameter, ki nam pove ali želimo dodat serial primary key stolpec
        """

        # dobimo slovar stolpcev in njihovih tipov
        cols = dict(df.dtypes)

        cols_sql = ""

        # dodamo serial primary key
        if add_serial: cols_sql += 'Id SERIAL PRIMARY KEY,\n'
        
        # dodamo ostale stolpce
        # tukaj bi stolpce lahko še dodatno filtrirali, preimenovali, itd.
        cols_sql += ",\n".join([self.col_to_sql(col, str(typ), use_camel_case=use_camel_case) for col, typ in cols.items()])


        # zgradimo končen sql stavek
        sql = f'''CREATE TABLE IF NOT EXISTS {name}(
            {cols_sql}
        )'''


        self.cur.execute(sql)
        self.conn.commit()
        

    def df_to_sql_insert(self, df:DataFrame, name:str, use_camel_case=True):
        """
        Vnese DataFrame v postgresql bazo. Paziti je treba pri velikosti dataframa,
        saj je sql stavek omejen glede na dolžino. Če je dataframe prevelik, ga je potrebno naložit
        po delih (recimo po 100 vrstic naenkrat), ali pa uporabit bulk_insert.
        df: DataFrame, ki ga želimo prenesti v bazo
        name: Ime tabele kamor želimo shranit podatke
        use_camel_case: ali pretovrimo stolpce v camel case zapis
        """

        cols = list(df.columns)

        # po potrebi pretvorimo imena stolpcev
        if use_camel_case: cols = [self.camel_case(c) for c in cols]

        # ustvarimo sql stavek, ki vnese več vrstic naenkrat
        sql_cmd = f'''INSERT INTO {name} ({", ".join([f'"{c}"' for c in cols])})
            VALUES 
            {','.join(
                self.cur.mogrify(f'({",".join(["%s"]*len(cols))})', i).decode('utf-8')
                for i in df.itertuples(index=False)
                )}
        '''

        # izvedemo ukaz
        self.cur.execute(sql_cmd)
        self.conn.commit()

    
    def izdelki(self) -> List[IzdelekDto]: 
        izdelki = self.cur.execute(
            """
            SELECT i.id, i.ime, k.oznaka FROM Izdelki i
            left join KategorijaIzdelka k on i.kategorija = k.id
            """)

        return [IzdelekDto(id, ime, oznaka) for (id, ime, oznaka) in izdelki]
    
    def cena_izdelkov(self, skip: int = 0, take: int = 10, leta: List[Leto] = []) -> List[CenaIzdelkaDto]:

        if leta:
            # V poizvedbi mormao uporabit še in stavek, da določimo le izbrana leta

            sql_query = self.cur.mogrify(f"""
                select c.id, i.id as izdelek_id, i.ime, k.oznaka, date_part('year', c.leto)::TEXT as leto, c.cena from cenaizdelka c
                    left join izdelek i on i.id = c.izdelek_id
                    left join kategorijaizdelka k on k.id = i.kategorija
                where date_part('year', c.leto)::TEXT in %s
                limit {take}
                offset {skip};
                """, (tuple([leto.leto for leto in leta if leto.izbrano]),) )
            self.cur.execute(sql_query)
                
            
                

        else:
            self.cur.execute(
                f"""
                select c.id, i.id as izdelek_id, i.ime, k.oznaka, date_part('year', c.leto)::TEXT as leto, c.cena from cenaizdelka c
                    left join izdelek i on i.id = c.izdelek_id
                    left join kategorijaizdelka k on k.id = i.kategorija

                limit {take}
                offset {skip};
            
                """
        )

        return [CenaIzdelkaDto(id, izdelek_id, ime, oznaka, leto, cena) for (id, izdelek_id, ime, oznaka, leto, cena) in self.cur.fetchall()]
    
    def kategorije_izdelkov(self, skip:int = 0, take: int = 10) -> List[KategorijaIzdelkaDto]:
        self.cur.execute(
            f"""
            select c.id, max(c.oznaka) as oznaka, count(i.ime) as st_izdelkov from kategorijaIzdelka c
                left join izdelek i on i.kategorija = c.id
                group by c.id

            limit {take}
            offset {skip};
           
             """
        )

        return [KategorijaIzdelkaDto(id, oznaka, st_izdelkov) for (id, oznaka, st_izdelkov) in self.cur.fetchall()]
    
    def dobi_leta(self) -> List[Leto]:
        self.cur.execute(
            """
            select distinct date_part('year', leto)::TEXT as leto from cenaizdelka
            order by date_part('year', leto)::TEXT asc;
            """
        )
        


        return [Leto(leto, True) for (leto,) in self.cur.fetchall()]

    def dobi_izdelek(self, ime_izdelka: str) -> Izdelek:
        # Preverimo, če izdelek že obstaja
        self.cur.execute("""
            SELECT id, ime, kategorija from Izdelek
            WHERE ime = %s
          """, (ime_izdelka,))
        
        row = self.cur.fetchone()

        if row:
            id, ime, kategorija = row
            return Izdelek(id, ime, kategorija)
        
        raise Exception("Izdelek z imenom " + ime_izdelka + " ne obstaja")

    
    def dodaj_izdelek(self, izdelek: Izdelek) -> Izdelek:

        # Preverimo, če izdelek že obstaja
        self.cur.execute("""
            SELECT id, ime, kategorija from Izdelek
            WHERE ime = %s
          """, (izdelek.ime,))
        
        row = self.cur.fetchone()
        if row:
            izdelek.id = row[0]
            return izdelek

        
    

        # Sedaj dodamo izdelek
        self.cur.execute("""
            INSERT INTO Izdelek (ime, kategorija)
              VALUES (%s, %s) RETURNING id; """, (izdelek.ime, izdelek.kategorija))
        izdelek.id = self.cur.fetchone()[0]
        self.conn.commit()
        return izdelek


    def dodaj_kategorijo(self, kategorija: KategorijaIzdelka) -> KategorijaIzdelka:

        
        
        # Preverimo, če določena kategorija že obstaja
        self.cur.execute("""
            SELECT id from KategorijaIzdelka
            WHERE oznaka = %s
          """, (kategorija.oznaka,))
        
        row = self.cur.fetchone()
        
        if row:
            kategorija.id = row[0]
            return kategorija


        # Če še ne obstaja jo vnesemo in vrnemo njen id
        self.cur.execute("""
            INSERT INTO KategorijaIzdelka (oznaka)
              VALUES (%s) RETURNING id; """, (kategorija.oznaka,))
        self.conn.commit()
        kategorija.id = self.cur.fetchone()[0]

        

        return kategorija
    
    def dodaj_ceno_izdelka(self, cena_izdelka: CenaIzdelka) -> CenaIzdelka:

         # Preverimo, če določena kategorija že obstaja
        self.cur.execute("""
            SELECT id, izdelek_id, leto, cena from CenaIzdelka
            WHERE izdelek_id = %s and leto = %s
          """, (cena_izdelka.izdelek_id, date(int(cena_izdelka.leto), 1, 1)))
        
        row = self.cur.fetchone()
        if row:
            cena_izdelka.id = row[0]
            return cena_izdelka
        
        # Dodamo novo ceno izdelka

        self.cur.execute("""
            INSERT INTO CenaIzdelka (izdelek_id, leto, cena)
              VALUES (%s, %s, %s) RETURNING id; """, (cena_izdelka.izdelek_id, date(int(cena_izdelka.leto), 1, 1), cena_izdelka.cena,))
        self.conn.commit()

        cena_izdelka.id = self.cur.fetchone()[0]
        return cena_izdelka
    
    ##################################################################################################
    ##################################################################################################


    def uvozi_Price_History(self, tabela: str):
        # Vnese zgodovino simbola v tabelo price_history
        with open('Podatki/Posamezni_simboli/{0}'.format(tabela)) as csvfile:
            podatki = reader(csvfile)
            next(podatki)
            for r in podatki:
                r = [None if x in ('', '-') else x for x in r]
                self.cur.execute('''
                    INSERT INTO price_history
                    (symbol_id, date, price)
                    VALUES (%s, %s, %s)
                ''', r)
            self.conn.commit()
            print('Uspesno uvozil csv datoteko!')



    def dodaj_par(self, simbol: str, name: str):
        self.cur.execute('''
            INSERT INTO pair (symbol, name) 
            VALUES (%s, %s)
        ''', (simbol, name))
        self.conn.commit()




    def posodobi_price_history(self, df: DataFrame | None):
        if not df is None:
            for i in df.index:
                self.cur.execute('''
                    INSERT INTO price_history (symbol_id, date, price)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (symbol_id, date)
                    DO UPDATE SET price = {}
                '''.format(df['price'][i]), (df['symbol_id'][i], df['date'][i], df['price'][i]))
            self.conn.commit()
            


    def dobi_asset_by_user(self, typ: Type[T], id: int | str, id_col = "user_id") -> List[str]:
        """
        Generična metoda, ki vrne seznam dataclass objektov pridobljen iz baze na podlagi njegovega idja.
        """
        tbl_name = typ.__name__
        sql_cmd = f'SELECT * FROM {tbl_name} WHERE {id_col} = %s';
        self.cur.execute(sql_cmd, (id,))

        d = self.cur.fetchall()

        if d is None:
            raise Exception(f'Vrstica z id-jem {id} ne obstaja v {tbl_name}');
    
        seznam = list()
        for i in d:
            seznam.append(i[1])

        return seznam
    


    def dobi_asset_amount_by_user(self, user_id: int) -> List[List]:
        self.cur.execute('''
            SELECT symbol_id, amount
            FROM asset
            WHERE user_id = %s
        ''', (user_id,))
        return self.cur.fetchall()
    

    def dobi_pare(self) -> List[List]:
        self.cur.execute('''
            SELECT symbol, name
            FROM pair
        ''')
        return self.cur.fetchall()



    def dobi_strategije(self, user_id: int) -> List[str]:
        self.cur.execute('''
            SELECT strategy 
            FROM trade
            WHERE user_id = {} 
            AND (type = 'L' OR type = 'S') 
            GROUP BY strategy
        '''.format(user_id))
        zacasni = self.cur.fetchall()
        seznam = list()
        for item in zacasni:
            seznam.append(item[0])
        return seznam



    def sign(self, amount: float | str, tip: str) -> float:
        amount = float(amount)
    # Določi predznak
        if tip == 'Sell':
            return -abs(amount)
        return abs(amount)





    def trade_result(self, user_id: int, simbol: str, pnl: float | str):
        self.cur.execute('''
            SELECT amount 
            FROM asset
            WHERE user_id = '{0}' 
            AND symbol_id = '{1}'
        '''.format(user_id, simbol))
        row = self.cur.fetchone()
        if row is None:
            self.cur.execute('''
                INSERT INTO asset (user_id, symbol_id, amount) 
                VALUES (%s, %s, %s)
            ''', (user_id, simbol, pnl))
        else:
            amount = round(pnl + float(row[0]), 2)
            self.cur.execute('''
                UPDATE  asset 
                SET amount = {0} 
                WHERE user_id = '{1}' 
                AND symbol_id = '{2}'
            '''.format(amount, user_id, simbol))
        self.conn.commit()



    def dobi_trade_delno(self, user_id: int) -> List[T]:
        self.cur.execute('''
            SELECT symbol_id, type, strategy, RR, target, date, duration, TP, PNL 
            FROM trade
            WHERE user_id = {} 
            ORDER BY symbol_id 
        '''.format(user_id))
        seznam = self.cur.fetchall()
        return seznam


    def pnl_trade(self, user_id: int, simbol: str, pnl: float | str):
        dollar = findall(r'\$', pnl)
        
        if dollar == []:    # PNL doda pri assetu na katerem je trade
            Repo().trade_result(self, user_id, simbol, float(pnl))
        
        elif dollar != []:  # PNL doda pri USD
            pnl = sub('\$','',pnl)
            Repo().trade_result(user_id, 'USD', float(pnl))





