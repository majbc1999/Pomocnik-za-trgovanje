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
    anl_stats: tuple = field(default=(0, 0, 0, 0, 0, 0))
    stats_tuple: tuple = field(default=(0, 0, 0, 0, 0, 0, 0))
