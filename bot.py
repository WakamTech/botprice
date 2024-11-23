import asyncio
import ccxt
import os
import telegram
import websocket
import threading
import json
import time
import requests
from dotenv import load_dotenv
from pybit.unified_trading import WebSocket as BybitWebSocket
import asyncio
import websockets
import json
import websocket
import threading
import time
import requests
import os

# Charger les variables d'environnement
load_dotenv()

# --- Paramètres Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TOKEN")
TELEGRAM_CHANNEL_ID = int(os.getenv("CANAL_ID"))

# --- Paramètres Binance ---
# List of symbols to track for Binance
BINANCE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "SOLUSDT", "DOTUSDT", "MATICUSDT", "SHIBUSDT",
    "AVAXUSDT", "LTCUSDT", "UNIUSDT", "LINKUSDT", "BCHUSDT",
    "XLMUSDT", "ATOMUSDT", "ALGOUSDT", "VETUSDT", "ICPUSDT"
]

# List of symbols to track for Bybit (linear symbols)
BYBIT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "EOSUSDT", "LTCUSDT",
    "BCHUSDT", "TRXUSDT", "ETCUSDT", "LINKUSDT", "XLMUSDT",
    "ADAUSDT", "XMRUSDT", "DASHUSDT", "ZECUSDT", "XTZUSDT",
    "BNBUSDT", "ATOMUSDT", "ONTUSDT", "IOTAUSDT", "BATUSDT",
    "VETUSDT", "NEOUSDT", "QTUMUSDT", "IOSTUSDT", "THETAUSDT",
    "ALGOUSDT", "ONEUSDT", "FTMUSDT", "SOLUSDT", "AVAXUSDT",
    "CRVUSDT", "UNIUSDT", "SUSHIUSDT", "AAVEUSDT", "YFIUSDT",
    "COMPUSDT", "LUNAUSDT", "DOTUSDT", "KSMUSDT", "NEARUSDT",
    "FILUSDT", "RSRUSDT", "CHZUSDT", "MANAUSDT", "GRTUSDT",
    "SANDUSDT", "ENJUSDT", "AXSUSDT", "GALAUSDT", "ILVUSDT",
    "IMXUSDT", "APEUSDT", "GMTUSDT"
]


# --- Paramètres prix et images ---
SYMBOLS_PRICE_IMAGES = {
    "BTC/USDT": 1000,
    "ETH/USDT": 100,
    "SOL/USDT": 50,
    "BNB/USDT": 50,
}
last_notified_prices = {symbol: 0 for symbol in SYMBOLS_PRICE_IMAGES}

# Precision for symbols
PRECISION = {
    "BTC": 2, "1000PEPE": 4, "NOT": 4, "WIF": 3, "ETH": 2, "ORDI": 2, "IO": 3,
    "BTCUSD_PERP": 2, "BTCUSD_240628": 2, "BTCUSD_240927": 2, "SOL": 2, "EOS": 3,
    "XEM": 4, "LQTY": 3, "AI": 3, "DEFI": 2, "IMX": 3, "SOLUSD_PERP": 2, "ETC": 2,
    "BOME": 5, "DOGE": 3, "LDO": 3, "UNI": 3, "1000SATS": 6, "ZEC": 2, "1000FLOKI": 3,
    "BCH": 2, "SUI": 3, "BNB": 2, "JTO": 3, "HIFI": 3, "C98": 3
}


# --- Initialisations ---
exchange = ccxt.binance()
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)



# --- Fonctions utilitaires ---

async def send_telegram_message(message, photo_path=None):
    try:
        if photo_path:
            with open(photo_path, 'rb') as photo:
                await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=photo, caption=message)
        else:
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode="HTML")
    except telegram.error.TelegramError as e:
        print(f"Erreur Telegram : {e}")


async def get_price(symbol: str) -> float | None:
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except (ccxt.NetworkError, ccxt.ExchangeError) as e:
        print(f"Erreur prix {symbol}: {e}")
        return None



# --- Logique prix et images ---

async def display_prices():
    first_run = True
    while True:
        for symbol, interval in SYMBOLS_PRICE_IMAGES.items():
            price = await get_price(symbol)
            if price:
                rounded_price = int(price // interval * interval)
                if first_run or (int(price) == rounded_price and rounded_price != last_notified_prices[symbol]):
                    image_path = f"images/{symbol.lower().replace('/', '')}/{symbol.lower().replace('/', '')}_{rounded_price}.jpg"
                    if os.path.exists(image_path):
                        emoji = "\U0001F384"
                        if symbol == "ETH/USDT": emoji = "💎"
                        elif symbol == "SOL/USDT": emoji = " Solana"
                        elif symbol == "BNB/USDT": emoji = " BNB"
                        caption = f"{emoji} ${rounded_price:,} @{bot.username}"
                        await send_telegram_message(caption, image_path)
                        last_notified_prices[symbol] = rounded_price
        first_run = False
        await asyncio.sleep(20)

def format_number(num):
    if num < 1000:
        return str(num)
    elif num >= 1000 and num < 1000000:
        return f"{num/1000:.1f}K"
    else:
        return f"{num/1000000:.1f}M"

def format_price(symbol, price):
    precision = PRECISION.get(symbol, 2)
    return f"{price:.{precision}f}"

class BinanceSocketConn:
    def __init__(self):
        self.url = f'wss://fstream.binance.com/ws/!forceOrder@arr'
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            url=self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def on_open(self, ws):
        print('Websocket was opened')

    def on_message(self, ws, message):
        data = json.loads(message)
        self.handle_message(data)

    def on_error(self, ws, error):
        print('Error', error)

    def on_close(self, ws, close_status_code, close_msg):
        print('Closing')
        # Implement reconnection logic
        self.reconnect()

    def reconnect(self):
        print("Reconnecting to Binance WebSocket...")
        time.sleep(5)
        self.__init__()

    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            print(f"Message sent: {message}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send message: {e}")
            print(f"Response: {response.text}")

    def handle_message(self, data):
        order = data['o']
        symbol = order['s'].replace("USDT", "")
        side = order['S']
        price = float(order['p'])
        quantity = float(order['q'])
        notional_value = quantity * price
        formatted_value = format_number(notional_value)
        formatted_price = format_price(symbol, price)

        if notional_value > 1000000:
            emoji = "🟢" if side != "SELL" else "🔴"
            side_text = "Long" if side == "SELL" else "Short"
            message = (
                f"{emoji} #{symbol} Liquidated {side_text}: ${formatted_value} at ${formatted_price}  (Binance)"
            )
            self.send_telegram_message(message)
            #print(message)

class BybitSocketConn:
    def __init__(self):
        self.url = "wss://stream.bybit.com/contract/usdc/public/v3"
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    async def connect_and_subscribe(self):
        async with websockets.connect(self.url) as websocket:
            subscribe_message = {
                "op": "subscribe",
                "args": [f"liquidation.{symbol}" for symbol in BYBIT_SYMBOLS],
                "req_id": "test"
            }
            await websocket.send(json.dumps(subscribe_message))
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                self.handle_message(data)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect_and_subscribe())

    def handle_message(self, message):
        # Check if message contains 'data'
        if 'data' in message:
            order = message['data']
            symbol = order['symbol'].replace("USDT", "")
            side = order['side']
            price = float(order['price'])
            quantity = float(order['size'])
            notional_value = price * quantity
            formatted_value = format_number(notional_value)
            formatted_price = format_price(symbol, price)

            if notional_value > 1000000:
                emoji = "🟢" if side == "Sell" else "🔴"
                side_text = "Long" if side != "Sell" else "Short"
                telegram_message = (
                    f"{emoji} #{symbol} Liquidated {side_text}: ${formatted_value} at ${formatted_price} (Bybit)"
                )
                binance_socket.send_telegram_message(telegram_message)
                #print(telegram_message)
        else:
            print(f"Unexpected message format: {message}")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.reconnect()

    def reconnect(self):
        print("Reconnecting to Bybit WebSocket...")
        time.sleep(5)
        self.__init__()

# --- Fonction principale ---

async def main():
    await bot.initialize()

    # Threads pour les WebSockets
    binance_thread = threading.Thread(target=BinanceSocketConn)
    bybit_thread = threading.Thread(target=BybitSocketConn)
    binance_thread.daemon = True
    bybit_thread.daemon = True
    binance_thread.start()
    bybit_thread.start()

    # Boucle principale pour les prix/images (asyncio)
    await display_prices()

if __name__ == "__main__":
    asyncio.run(main())