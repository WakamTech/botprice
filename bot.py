import ccxt
import asyncio
import os
from dotenv import load_dotenv
import telegram

# Charger les variables d'environnement
load_dotenv()

# Initialiser l'exchange (Binance)
exchange = ccxt.binance()

# Récupérer le token et l'ID du canal depuis les variables d'environnement
TOKEN = os.getenv("TOKEN")
CANAL_ID = int(os.getenv("CANAL_ID"))

# Initialiser le bot Telegram
bot = telegram.Bot(token=TOKEN)

# Dictionnaire pour stocker les derniers prix notifiés (inutile pour ce test, mais le gardons pour la cohérence avec le code complet)
last_notified_prices = {
    "BTC/USDT": 0,
    "ETH/USDT": 0,
    "SOL/USDT": 0,
}

async def get_price(symbol: str) -> float | None:
    """Récupère le prix d'une cryptomonnaie (non utilisé dans ce test)."""
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except (ccxt.NetworkError, ccxt.ExchangeError) as e:
        print(f"Erreur lors de la récupération du prix de {symbol}: {e}")
        return None

async def send_telegram_photo(photo_path: str, price: int, symbol: str):  # Ajout du symbole
    try:
        # Adaptez l'emoji en fonction du symbole si nécessaire
        emoji = "\U0001F384"  # Sapin de Noël par défaut
        if symbol == "ETH/USDT":
            emoji = "💎"  # Diamant pour ETH
        elif symbol == "SOL/USDT":
            emoji = " Solana"  # Texte pour SOL car l'image contient déja l'emoji SOL



        caption = f"{emoji} ${price:,} @{bot.username}"
        with open(photo_path, 'rb') as photo:
            await bot.send_photo(chat_id=CANAL_ID, photo=photo, caption=caption)


    except telegram.error.TelegramError as e:
        print(f"Erreur lors de l'envoi de la photo : {e}")

async def display_prices():
    """Affiche les prix et envoie un message Telegram avec la logique "pas de répétition"."""


    symbols = {
        "BTC/USDT": 1000,
        "ETH/USDT": 100,
        "SOL/USDT": 50,
    }




    while True:
        for symbol, interval in symbols.items():
            price = await get_price(symbol)
            if price is not None:
                rounded_price = int(price // interval * interval)
                price_diff = rounded_price - last_notified_prices[symbol]
                if abs(price_diff) >= interval:
                    if rounded_price > last_notified_prices[symbol] + interval or rounded_price < last_notified_prices[symbol] - interval:
                        image_path = f"images/{symbol.lower().replace('/', '')}/{symbol.lower().replace('/', '')}_{rounded_price}.jpg" # Construction du chemin
                        if os.path.exists(image_path):
                            await send_telegram_photo(image_path, rounded_price, symbol) #  Passage du prix et symbole
                            last_notified_prices[symbol] = rounded_price

        await asyncio.sleep(20)  # Vérification toutes les 20 secondes

async def main():


  await bot.initialize()  # Initialiser une seule fois avant display prices
  await display_prices()


if __name__ == "__main__":

    asyncio.run(main())