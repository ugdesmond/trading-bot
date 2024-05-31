from flask_login import UserMixin
from . import db, login_manager
from enum import Enum


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(long(user_id))


class DisplayMessage:
    is_error = False
    message = ''
    filename = ''


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', uselist=False,backref='role')


    def __repr__(self):
        return '<Role %r>' % self.name

class UsedBy(Enum):
    Internal = 1,
    External = 2
class RoleType(Enum):
    ADMIN = 1,
    USER = 2
class TransactionTypeEnum(Enum):
    DEPOSIT = 1
    WITHDRAW=2

class TransactionStatusEnum(Enum):
    BUY = 1
    SELL = 2

class StatusEnum(Enum):
    RUNNING = "Pending"
    NOTACTIVATED = "Not-Activated"
    COMPLETED = "Completed"
    CANCELLED="Cancelled"
    #for multiple orders==
    ACTIVATED="Running..."
    #for jobs
    STOPPED="Stopped"
    #arbitrage trade
    CREATED="Created"


class ExchangeTypeEnum(Enum):
    BITFINEX = 1
    BITTREX = 2
    #value
    BITFINEXVALUE = "bitfinex"
    BITTREXVALUE = "bittrex"

class CurrencyTypeSymbolEnum(Enum):
    Bittfinex_BCH="BCH"
    Bittrex_BCH="BCC"
class JobTask(Enum):
    UPDATETASK = "updatetask"
    ARBITRAGETASK = "arbitragetask"




class JobStatus(Enum):
    ADDJOB = True
    REMOVEJOB = False

class CurrencyTypeEnum(Enum):
    BTC = 1
    ETHERIUM = 2

class MarketTypeEnum(Enum):
    BTC_MARKET = 1
    ETHERUM_MARKET = 2
    USDT_MARKET=3


class OrderTypeEnum(Enum):
    SINGLE = "Single"
    MULTIPLE = "Multiple"

class ExchangeTypeUrl(Enum):
    BITFINEX = "https://api.bitfinex.com"
    BITTREX = "Multiple"


class ExchangeMarket(Enum):
    EXCHANGEMARKET = "exchange market"
    EXCHANGELIMIT = "exchange limit"

class WalletTypeEnum(Enum):
    EXCHANGE = "exchange"
    MARGIN = "margin"
class CurrencyTypeSymbolEnum(Enum):
    Bittfinex_BCH="BCH"
    Bittrex_BCH="BCC"



class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(64), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    person_id = db.Column(db.BigInteger, db.ForeignKey('persons.id'), nullable=False)
    account = db.relationship('Account',uselist=False, backref='user')
    ticker = db.relationship('Ticker', uselist=False, backref='user')
    arbitrageTrade = db.relationship('ArbitrageTrade', uselist=False, backref='user')


    def __repr__(self):
        return '<user %r>' % self.username

    @staticmethod
    def is_user_exisiting(email, password):
        user = User.query.filter_by(email=email, password_hash=password).first()
        if user is not None:
            return True
        return False


class Person(db.Model):
    __tablename__ = 'persons'
    id = db.Column(db.BigInteger, primary_key=True)
    firstname = db.Column(db.String(64), nullable=False)
    surname = db.Column(db.String(64), nullable=False)
    othernames = db.Column(db.String(64), nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    phone_number = db.Column(db.String(20))
    contact_address = db.Column(db.String(300))
    users = db.relationship('User',uselist=False, backref='person')


class ExchangeType(db.Model):
    __tablename__ = 'exchange_type'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(64))
    interval=db.Column(db.Integer)
    order = db.relationship('Order', backref='exchange_type')
    walletpaymentdetail = db.relationship('WalletPaymentDetail', backref='exchange_type')
    wallet = db.relationship('Wallet', backref='exchange_type')
    ticker = db.relationship('Ticker', uselist=False, backref='exchangetype')
    account = db.relationship('Account', uselist=False, backref='exchange_type')
    currencyexchange = db.relationship('CurrencyExchange', uselist=False, backref='exchange_type')
    orderPayementDetail = db.relationship('OrderPaymentDetail',uselist=False, backref='exchangetype')
    arbitrageTradeOrderDetail = db.relationship('ArbitrageTradeOrderDetail', backref='exchangetype', uselist=False)



#deposited or withdrawn
class TransactionType(db.Model):
    __tablename__ = 'transaction_type'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(64))
    walletpaymentdetail = db.relationship('WalletPaymentDetail',uselist=False, backref='transactiontype')


# buying and selling
class TransactionStatus(db.Model):
    __tablename__ = 'transaction_status'
    id=db.Column(db.Integer,primary_key=True)
    description = db.Column(db.String(64))
    order = db.relationship('Order',uselist=False, backref='transactionstatus')
    orderPaymentDetail = db.relationship('OrderPaymentDetail', uselist=False, backref='transactionstatus')
    arbitrageTradeOrderDetail = db.relationship('ArbitrageTradeOrderDetail', backref='transactionstatus', uselist=False)




class Ticker(db.Model):
    __tablename__='tickers'
    id=db.Column(db.BigInteger,primary_key=True)
    date_time=db.Column(db.DateTime,nullable=False)
    min_amount =db.Column(db.Float,nullable=True)
    max_amount=db.Column(db.Float,nullable=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    markettype_id = db.Column(db.Integer, db.ForeignKey('market_type.id'))
    currencytype_id = db.Column(db.Integer, db.ForeignKey('currency_type.id'))
    exchangetype_id = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))


class MarketType(db.Model):
    __tablename__='market_type'
    id=db.Column(db.Integer,primary_key=True)
    description=db.Column(db.String(255))
    order = db.relationship('Order', uselist=False, backref='markettype')
    ticker = db.relationship('Ticker', uselist=False, backref='markettype')
    currencymarket = db.relationship('CurrencyMarket', uselist=False, backref='markettype')



class CurrencyType(db.Model):
    __tablename__='currency_type'
    id=db.Column(db.Integer,primary_key=True)
    description=db.Column(db.String(60))
    method= db.Column(db.String(20))
    symbol= db.Column(db.String(20))
    wallet = db.relationship('Wallet', backref='currencytype', uselist=False)
    order = db.relationship('Order', uselist=False, backref='currencytype')
    ticker = db.relationship('Ticker', uselist=False, backref='currencytype')
    currencymarket = db.relationship('CurrencyMarket', uselist=False, backref='currencytype')
    # currencyexchange = db.relationship('CurrencyExchange', uselist=False, backref='currencytype')
    arbitrageTrade = db.relationship('ArbitrageTrade', uselist=False, backref='currencytype')

class Account(db.Model):
    __tablename__='accounts'
    id=db.Column(db.BigInteger,primary_key=True)
    api_key = db.Column(db.String(100), nullable=True)
    api_secret_key = db.Column(db.String(100), nullable=True)
    user_id=db.Column(db.BigInteger, db.ForeignKey('users.id'))
    exchange_type_id = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))
    wallet = db.relationship('Wallet', backref='account',uselist=False)
    order=db.relationship('Order', backref='account',uselist=False)
    orderpaymentdetail = db.relationship('OrderPaymentDetail', backref='account', uselist=False)
    arbitrageTradeOrderDetail = db.relationship('ArbitrageTradeOrderDetail', backref='account', uselist=False)

class CurrencyMarket(db.Model):
    __tablename__='currency_market'
    id=db.Column(db.BigInteger,primary_key=True)
    currency_type_id = db.Column(db.Integer, db.ForeignKey('currency_type.id'))
    market_type_id=db.Column(db.Integer, db.ForeignKey('market_type.id'))
    symbol=db.Column(db.String(100), nullable=True)



class CurrencyExchange(db.Model):
    __tablename__ = 'currency_excahnge'
    id=db.Column(db.BigInteger,primary_key=True)
    currency_type = db.Column(db.BigInteger, db.ForeignKey('currency_type.id'))
    exchange_type_id = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))



class Wallet(db.Model):
    __tablename__='wallet'
    id = db.Column(db.BigInteger, primary_key=True)
    total_amount=db.Column(db.Float,nullable=False)
    available_amount=db.Column(db.Float,nullable=False)
    transaction_amount=db.Column(db.Float,nullable=True)
    currency_type=db.Column(db.BigInteger, db.ForeignKey('currency_type.id'))
    account_id=db.Column(db.BigInteger, db.ForeignKey('accounts.id'))
    exchange_type_id = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))
    walletpaymentdetail = db.relationship('WalletPaymentDetail', backref='wallet', uselist=False)
    order = db.relationship('Order', backref='wallet', uselist=False)

class WalletPaymentDetail(db.Model):
    __tablename__='wallet_payment_detail'
    id = db.Column(db.BigInteger, primary_key=True)
    transaction_type = db.Column(db.Integer, db.ForeignKey('transaction_type.id'))
    transaction_fee=db.Column(db.Float)
    amount=db.Column(db.Float)
    date_time=db.Column(db.DateTime, nullable=False)
    wallet_id=db.Column(db.BigInteger, db.ForeignKey('wallet.id'))
    exchange_type_id = db.Column(db.Integer, db.ForeignKey('exchange_type.id'), nullable=True)
    withdrawal_id = db.Column(db.String(200))
    payment_status = db.Column(db.String(45))
    currency = db.Column(db.String(10))
    method = db.Column(db.String(20))
    description = db.Column(db.String(250))
    address = db.Column(db.String(200))
    transactionId = db.Column(db.BigInteger())
    flag = db.Column(db.Integer(), nullable=True)




class WalletType(db.Model):
    __tablename__= 'wallet_type'
    id = db.Column(db.Integer, primary_key=True)
    wallet_type_name = db.Column(db.String(20), nullable=False)


class Order(db.Model):
    __tablename__='orders'
    id=db.Column(db.BigInteger,primary_key=True)
    account_id=db.Column(db.BigInteger, db.ForeignKey('accounts.id'))
    symbol_exchange=db.Column(db.String(60))
    status=db.Column(db.String(40))
    order_type = db.Column(db.String(40))
    transaction_status=db.Column(db.Integer,db.ForeignKey('transaction_status.id'))
    currency_type = db.Column(db.BigInteger, db.ForeignKey('currency_type.id'))
    price=db.Column(db.Float,nullable=False)
    currency_amount=db.Column(db.Float,nullable=False)
    date_time=db.Column(db.DateTime, nullable=False)
    order_ref = db.Column(db.String(40), unique=True)
    tickers_min=db.Column(db.Float,nullable=True)
    tickers_max=db.Column(db.Float,nullable=True)
    price_to_pay = db.Column(db.Float, nullable=True)
    exchange_type_id = db.Column(db.Integer, db.ForeignKey('exchange_type.id'), nullable=True)
    wallet_id = db.Column(db.BigInteger, db.ForeignKey('wallet.id'), nullable=True)
    market_type_id = db.Column(db.Integer, db.ForeignKey('market_type.id'))
    market_exchange = db.Column(db.String(200))
    orderpaymentdetail = db.relationship('OrderPaymentDetail', backref='orders', uselist=False)


class OrderPaymentDetail(db.Model):
    __tablename__='order_payment_detail'
    id=db.Column(db.BigInteger,primary_key=True)
    order_id=db.Column(db.BigInteger,db.ForeignKey('orders.id'))
    transaction_fee=db.Column(db.Float,nullable=True)
    uuid=db.Column(db.String(200),nullable=True)
    original_amount=db.Column(db.Float,nullable=True)
    remaining_amount = db.Column(db.Float, nullable=True)
    executed_amount = db.Column(db.Float, nullable=True)
    order_ref=db.Column(db.String(40),nullable=False)
    payment_status=db.Column(db.String(45))
    is_cancelled=db.Column(db.Boolean)
    is_live=db.Column(db.Boolean)
    date_time = db.Column(db.DateTime, nullable=False)
    order_type = db.Column(db.String(40))
    account_id = db.Column(db.BigInteger, db.ForeignKey('accounts.id'))
    status = db.Column(db.String(40))
    exchange_type = db.Column(db.Integer, db.ForeignKey('exchange_type.id'), nullable=True)
    transaction_status = db.Column(db.Integer, db.ForeignKey('transaction_status.id'))



class BackgroundSchedule(db.Model):
    __tablename__ = 'background_schedular'
    id=db.Column(db.BigInteger,primary_key=True)
    job=db.Column(db.String(100),nullable=False)
    interval=db.Column(db.Integer,nullable=False)
    status=db.Column(db.Integer,nullable=False)


class ArbitrageTrade(db.Model):
    __tablename__='arbitrage_trade'
    id = db.Column(db.BigInteger, primary_key=True)
    date_time = db.Column(db.DateTime, nullable=False)
    exchange_type_from = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))
    exchange_type_to = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))
    crypto_amount=db.Column(db.Float,nullable=False)
    price=db.Column(db.Float, nullable=True)
    transaction_status=db.Column(db.Float, nullable=True)
    user_id=db.Column(db.BigInteger, db.ForeignKey('users.id'))
    withdrawal_status = db.Column(db.String(100),nullable=True)
    order_status=db.Column(db.String(100),nullable=True)
    do_round_trip=db.Column(db.Boolean,nullable=True)
    ref_number=db.Column(db.String(100), nullable=False)
    withdrawal_id=db.Column(db.BigInteger, nullable=True)
    currency_type = db.Column(db.BigInteger, db.ForeignKey('currency_type.id'))
    arbitrageTradeOrderDetail = db.relationship('ArbitrageTradeOrderDetail', backref='arbitragetrade', uselist=False)
    arbitrageTrade = db.relationship("ExchangeType", foreign_keys="[ArbitrageTrade.exchange_type_from]")
    arbitrageTrade1 = db.relationship("ExchangeType", foreign_keys="[ArbitrageTrade.exchange_type_to]")



class ArbitrageTradeOrderDetail(db.Model):
    __tablename__ = 'arbitrage_trade_order_detail'
    id = db.Column(db.BigInteger, primary_key=True)
    arbitrage_trade_id = db.Column(db.BigInteger, db.ForeignKey('arbitrage_trade.id'))
    uuid = db.Column(db.BigInteger)
    original_amount = db.Column(db.Float, nullable=True)
    remaining_amount = db.Column(db.Float, nullable=True)
    executed_amount = db.Column(db.Float, nullable=True)
    order_ref = db.Column(db.String(40), nullable=False)
    is_cancelled = db.Column(db.Boolean)
    is_live = db.Column(db.Boolean)
    date_time = db.Column(db.DateTime,nullable=False)
    account_id = db.Column(db.BigInteger, db.ForeignKey('accounts.id'),nullable=True)
    status = db.Column(db.String(40))
    exchange_type = db.Column(db.Integer, db.ForeignKey('exchange_type.id'), nullable=True)
    transaction_status = db.Column(db.Integer, db.ForeignKey('transaction_status.id'))





class RoundTripOrderDetail(db.Model):
    __tablename__ = 'round_trip_order_detail'
    id = db.Column(db.BigInteger, primary_key=True)
    date_time = db.Column(db.DateTime, nullable=False)
    exchange_type_from = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))
    exchange_type_to = db.Column(db.Integer, db.ForeignKey('exchange_type.id'))
    crypto_amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=True)
    withdrawal_amount=db.Column(db.Float)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    ref_number = db.Column(db.String(100), nullable=False)
    withdrawal_id = db.Column(db.BigInteger, nullable=True)
    status = db.Column(db.String(40))
    currency_type = db.Column(db.BigInteger, db.ForeignKey('currency_type.id'))
    arbitrageTrade = db.relationship("ExchangeType", foreign_keys="[RoundTripOrderDetail.exchange_type_from]")
    arbitrageTrade1 = db.relationship("ExchangeType", foreign_keys="[RoundTripOrderDetail.exchange_type_to]")

















