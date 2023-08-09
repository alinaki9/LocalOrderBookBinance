from websocket import WebSocketApp
import time
import hmac
import hashlib
import json
import ccxt
import requests
from collections import OrderedDict

true = True
false = False
lastToken = None
symbol = "PYRUSDT"

# ORDER_BOOK = {}

class LocalOrderBook():
    def __init__(self, symbol, pricePrecision) -> None:
        self.ORDER_BOOK = {}
        self.symbol = symbol
        self.pricePrecision = pricePrecision
        self.order_book_initialization = False
        pass

    def get_order_book(self):
        return self.ORDER_BOOK

    def get_symbol(self):
        return self.symbol

    def get_price_key(self, price):
        price = float(price)
        return format(price, ".{}f".format(self.pricePrecision))

    def initialize_order_book(self):
        url = f"https://api.binance.com/api/v3/depth?symbol={self.symbol}&limit=10"
        try:
            response = requests.get(url)
            snapshot = response.json()
            self.ORDER_BOOK = {
                'lastUpdateId': snapshot['lastUpdateId'],
                'bids': {self.get_price_key(price): str(quantity) for price, quantity in snapshot['bids']},
                'asks': {self.get_price_key(price): str(quantity) for price, quantity in snapshot['asks']}
            }
            print(self.ORDER_BOOK)
            self.order_book_initialization = True
        except Exception as e:
            print(f"Failed initializaing the Binance Order Book for Symbol: {symbol}. Error: {e}")
            pass

    def ordain_order_book(self):
        sorted_bids = dict(sorted(self.ORDER_BOOK["bids"].items(), key=lambda item: float(item[0]), reverse=True))
        sorted_asks = dict(sorted(self.ORDER_BOOK["asks"].items(), key=lambda item: float(item[0]), reverse=False))
        self.ORDER_BOOK["bids"] = sorted_bids
        self.ORDER_BOOK["asks"] = sorted_asks


    def update_order_book(self, event):

        if self.order_book_initialization is False:
            self.initialize_order_book()
            print("Order Book Initialized: {}".format(self.ORDER_BOOK))
            

        print("Initial Order Book: ", self.ORDER_BOOK)
        print("This is the update:::::", event)

        if int(event["u"]) <= int(self.ORDER_BOOK["lastUpdateId"]):
            print("u: {} is smaller or equal to the lastUpdateId: {} of the Local Order Book. RETURNING!!!".format(event["u"], self.ORDER_BOOK["lastUpdateId"]))
            return
            
        if int(event["U"]) <= int(self.ORDER_BOOK["lastUpdateId"]) + 1 and int(event["u"]) >= int(self.ORDER_BOOK["lastUpdateId"]) + 1:
            print("Will update the local order book!")

            self.ORDER_BOOK["lastUpdateId"] = int(event["u"])
            
            for bid in event["b"]:
                bidPrice = self.get_price_key(bid[0])
                bidQuantity = float(bid[1])

                if bidPrice in self.ORDER_BOOK["bids"]:
                    if bidQuantity == 0:
                        del self.ORDER_BOOK["bids"][bidPrice]
                    else:
                        self.ORDER_BOOK["bids"][bidPrice] = str(bidQuantity)
                else:
                    if bidQuantity != 0:
                        self.ORDER_BOOK["bids"][bidPrice] = str(bidQuantity)

            for ask in event["a"]:
                askPrice = self.get_price_key(ask[0])
                askQuantity = float(ask[1])

                if askPrice in self.ORDER_BOOK["asks"]:
                    if askQuantity == 0:
                        del self.ORDER_BOOK["asks"][askPrice]
                    else:
                        self.ORDER_BOOK["asks"][askPrice] = str(askQuantity)
                else:
                    if askQuantity != 0:
                        self.ORDER_BOOK["asks"][askPrice] = str(askQuantity)

        # ORDER_BOOK[symbol]["asks"] = OrderedDict(sorted(ORDER_BOOK[symbol]["asks"].items()))
        # ORDER_BOOK[symbol]["bids"] = OrderedDict(sorted(ORDER_BOOK[symbol]["bids"].items()))
        self.ordain_order_book()
        print("Final Order Book: ", self.ORDER_BOOK)

# localOrderBook = LocalOrderBook(symbol)
        

class BinanceWebSocketApp(WebSocketApp):

    def __init__(self, url, api_key, api_secret, **kwargs):
        super(BinanceWebSocketApp, self).__init__(url, **kwargs)
        self.url = 'wss://stream.binance.com:9443/ws'
        self._api_key = api_key
        self._api_secret = api_secret

    def _send_ping(self, interval, event, callback):
        while not event.wait(interval):
            self.last_ping_tm = time.time()
            if self.sock:
                try:
                    self.sock.pong()
                    print('Binance: Sent ping!')
                except Exception as ex:
                    print("Binance: send_ping routine terminated: {}".format(ex))
                    break

    def _request(self, channel, event=None, payload=None, auth_required=True):
        current_time = int(time.time())
        data = {
            "time": current_time,
            "channel": channel,
            "event": event,
            "payload": payload,
        }
        if auth_required:
            message = 'channel=%s&event=%s&time=%d' % (channel, event, current_time)
            data['auth'] = {
                "method": "api_key",
                "KEY": self._api_key,
                "SIGN": self.get_sign(message),
            }
        data = json.dumps(data)
        print('request: %s', data)
        self.send(data)

    def get_sign(self, message):
        h = hmac.new(self._api_secret.encode("utf8"), message.encode("utf8"), hashlib.sha512)
        return h.hexdigest()

    def subscribe(self, channel, payload=None, auth_required=True):
        self._request(channel, "subscribe", payload, auth_required)

    def unsubscribe(self, channel, payload=None, auth_required=True):
        self._request(channel, "unsubscribe", payload, auth_required)

def on_message(ws, message):
    global params_, lastToken, order_book_initialization, symbol
    message = eval(message)
    # print(message)

    try:
        
        if "asks" in message.keys():
            print("Received individual order book! Best Bid: {}, Best Ask: {}".format(message["bids"][0], message["asks"][0]))
        elif "e" in message.keys() and message["e"] == "trade":
            print("Received trades! TOKEN: {}. LTP: {}".format(message["s"], message["p"]))

        elif "e" in message.keys() and message["e"] == "depthUpdate":
            print("U: {}. u: {}".format(message["U"], message["u"]))

            # if order_book_initialization is True:
            #     # if int(message["U"]) <= ORDER_BOOK[symbol]["lastUpdateId"] and int(message["u"]) >= ORDER_BOOK[symbol]["lastUpdateId"]:
            #     #     print(message)
            #     localOrderBook.update_order_book(message)

            # if order_book_initialization is False:
            #     localOrderBook.initialize_order_book()
            #     print(localOrderBook.get_order_book())
            #     order_book_initialization = True
            # localOrderBook.update_order_book(message)

        else:
            print("Received Something! {}".format(message))

    except Exception as e:
        print('Something bad happened! : {}'.format(e))

def on_error(ws, message):
    print("App 1: Error: {}".format(message))

def getTokens():
    exchange = ccxt.binance()
    try:
        markets = exchange.fetch_markets()
        tokens = [i["lowercaseId"] for i in markets][:999]
    except:
        print("failedddddd")
    return tokens

def on_open(ws):
    depth_stream =  "{}@depth@100ms".format(symbol.lower())
    # params = ["{}@depth20@100ms".format(i) for i in tokens]


    subscribe_payload1 = {
        "method" : "SUBSCRIBE",
        "params" : [depth_stream],
        "id" : 1
    }

    # subscribe_payload2 = {
    #     "method" : "SUBSCRIBE",
    #     "params" : [depth_stream, trade_stream],
    #     "id" : 1
    # }

    ws.send(json.dumps(subscribe_payload1))
    # ws.send(json.dumps(subscribe_payload1))



api_key = "your_api_key"
api_secret = "your_api_secret"
app = BinanceWebSocketApp(url = None, api_key=api_key, api_secret=api_secret, on_message = on_message, on_open = on_open, on_error = on_error)
app.run_forever(ping_interval=5)
