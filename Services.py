import hashlib

from modeli import *
from datetime import date
from Database import Repo


class AuthService:

    repo : Repo
    def __init__(self, repo : Repo):
        
        self.repo = repo

    def obstaja_uporabnik(self, uporabnik: str) -> bool:
        try:
            uporabnik = self.repo.dobi_gen_id(app_user, uporabnik, id_col="user_name")
            if uporabnik == None:
                return False 
            return True
        except Exception:
            return False
    

    def prijavi_uporabnika(self, uporabnik : str, geslo: str) -> list:

        # Najprej dobimo uporabnika iz baze
        user = self.repo.dobi_gen_id(app_user, uporabnik, id_col="user_name")

        # Ustvarimo hash iz gesla, ki ga je vnesel uporabnik
        h = hashlib.blake2b()
        h.update(geslo.encode(encoding='utf-8'))
        hashed_pass = h.hexdigest()
        
        if hashed_pass == user['password']:
            return [user[0], user[1]]
        return [0, 0]
    

    def dodaj_uporabnika(self, ime: str, priimek: str, datum_rojstva: date, uporabnisko_ime: str, geslo: str):

        # Ustvarimo hash iz gesla, ki ga je vnesel uporabnik
        h = hashlib.blake2b()
        h.update(geslo.encode(encoding='utf-8'))
        hashed_pass = h.hexdigest()

        # Sedaj ustvarimo objekt Uporabnik in ga zapišemo bazo
        uporabnik = app_user(
            name = ime,
            surname = priimek,
            date_of_birth = datum_rojstva,
            user_name= uporabnisko_ime,
            password = hashed_pass
            )

        self.repo.dodaj_gen(uporabnik, serial_col='id_user')
