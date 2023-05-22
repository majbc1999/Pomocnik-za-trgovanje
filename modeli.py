from dataclasses import dataclass, field
from datetime import date


import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki

@dataclass
class app_user:
    id_user: int = field(default=0)
    name: str = field(default="")
    surname: str = field(default="")
    date_of_birth: date = field(default=(date(2000, 1, 1)))
    user_name: str = field(default="")
    password: str = field(default="")


@dataclass
class pair:
    symbol: str = field(default="")
    name: str = field(default="")


@dataclass
class price_history:
    symbol_id: str = field(default="")
    date: str = field(default="")
    price: float = field(default=0)


@dataclass
class asset:
    user_id: int = field(default=0)
    symbol_id: str = field(default="")
    amount: float = field(default=0)


@dataclass
class trade:
    user_id: int
    symbol_id: str
    type: str
    date: str
    pnl: str
    id_trade: int = field(default=0)
    strategy: str = field(default=psycopg2.extensions.AsIs('NULL'))
    rr: float = field(default=psycopg2.extensions.AsIs('NULL'))
    target: float = field(default=psycopg2.extensions.AsIs('NULL'))
    duration: str = field(default=psycopg2.extensions.AsIs('NULL'))
    tp: int = field(default=psycopg2.extensions.AsIs('NULL'))


@dataclass
class UporabnikCookie:
    user_ime: str = field(default='')
    sporocilo: str = field(default='')
    user_id: int = field(default=0)
    user_assets: list[str] = field(default_factory=lambda: [])
    uspesna_prijava: bool = field(default=True)  
    pravilen_simbol: bool = field(default=True)
    first_load_assets: bool = field(default=True)
    first_load_stats: bool = field(default=True)
    uspesna_registracija: bool = field(default=True)
    anl_stats: tuple = field(default=(0, 0, 0, 0, 0, 0))
    stats_tuple: tuple = field(default=(0, 0, 0, 0, 0, 0, 0))

#################################################
#################################################
#################################################
#################################################
@dataclass
class Izdelek:
    id: int = field(default=0)
    ime: str = field(default="")
    kategorija: int = field(default=0)



@dataclass
class IzdelekDto:
    id: int = field(default=0)
    ime: str = field(default="")
    oznaka: str = field(default="")


@dataclass
class KategorijaIzdelka:
    id: int = field(default=0)
    oznaka: str = field(default="")

@dataclass
class KategorijaIzdelkaDto:
    id: int = field(default=0)
    oznaka: str = field(default="")
    st_izdelkov: int = field(default=0)

@dataclass
class Leto:
    leto: str = field(default="")
    izbrano: bool = field(default=False)
    
@dataclass
class CenaIzdelka:
    id: int = field(default=0)
    izdelek_id : int = field(default=0)
    leto : str = field(default="")
    cena : float = field(default=0)

@dataclass
class CenaIzdelkaDto:
    id: int = field(default=0)
    izdelek_id : int = field(default=0)
    izdelek_ime : str = field(default="")
    izdelek_oznaka : str = field(default="")
    leto : str = field(default="")
    cena : float = field(default=0)

@dataclass
class Uporabnik:
    username: str = field(default="")
    role: str = field(default="")
    password_hash: str = field(default="")
    last_login: str = field(default="")

@dataclass
class UporabnikDto:
    username: str = field(default="")
    role: str = field(default="")

#uporabnik = UporabnikCookie()

#uporabnik.user_id = 1

#print(uporabnik)