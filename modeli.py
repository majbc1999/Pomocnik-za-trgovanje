from dataclasses import dataclass, field


@dataclass
class Uporabnik:
    id_user: int = field(default=0)
    name: str = field(default="")
    surname: str = field(default="")
    date_of_birth: str = field(default="")
    username: str = field(default="")
    password_hash: str = field(default="")


@dataclass
class Pair:
    symbol_id: str = field(default="")
    name: str = field(default="")


@dataclass
class Price:
    symbol_id: str = field(default="")
    date: str = field(default="")
    price: float = field(default=0)


@dataclass
class Asset:
    user_id: int = field(default=0)
    symbol_id: str = field(default="")
    amount: float = field(default=0)


@dataclass
class Trade:
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
