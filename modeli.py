from dataclasses import dataclass, field
from datetime import date

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
    symbol_id: str = field(default="")
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
    id_trade: int = field(default=0)
    user_id: int = field(default=0)
    symbold_id: str = field(default="")
    type: str = field(default="")
    strategy: str = field(default="")
    rr: float = field(default=0)
    target: float = field(default=0)
    date: str = field(default="")
    duration: str = field(default="")
    tp: int = field(default=0)
    pnl: str = field(default="")
