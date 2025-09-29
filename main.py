import json
import logging
from binance.client import Client

# Configuration saved to trading_bot log file
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# Load Api using Try and Exception
def load_api_key(file_path='settings.json'):

    try:
        with open(file_path, 'r') as f:
            keys = json.load(f)
        if not keys.get('api_key') or not keys.get('api_secret'):
            raise ValueError("Missing api_key or api_secret")
        return keys['api_key'], keys['api_secret']
    except Exception as e:
        logging.error(f"Failed to load API keys: {e}")

# From here, Actual Trading Bot is start
class TradingBot:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.client = Client(api_key, api_secret, testnet=testnet)
        self.exchange_info = self.client.futures_exchange_info()
        self.client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
        logging.info("Initialization")


    # Fetch Balance
    def get_balance(self, asset='USDT'):
        try:
            logging.info(f"[REQUEST] GET /fapi/v2/balance | asset={asset}")
            balance_info = self.client.futures_account_balance()
            logging.info(f"[RESPONSE] Balance Data: {balance_info}")

            for b in balance_info:
                if b['asset'] == asset:
                    return float(b['balance'])
            return 0.0
        except Exception as e:
            logging.error(f"[ERROR] Fetching balance failed: {e}")
            raise

    # Place order as per Symbols
    def place_order(
            self,
            symbol: str,
            side: str,
            order_type: str,
            quantity: float,
            price: float = None,
            stop_price: float = None
    ):
        side_up = side.upper()
        order_type_lower = order_type.lower()
        symbol_up = symbol.upper()

        if side_up not in ('BUY', 'SELL'):
            raise ValueError("side must be BUY or SELL")

        try:
            if side_up == 'BUY':
                balance = self.get_balance('USDT')
                if balance < quantity:  # very basic check
                    raise ValueError(f"Insufficient USDT balance: {balance}")

            payload = {
                "symbol": symbol_up,
                "side": side_up,
                "quantity": quantity,
                "recvWindow": 5000,
                "newOrderRespType": "RESULT"
            }

            if order_type_lower == 'market':
                payload["type"] = "MARKET"

            elif order_type_lower == 'limit':
                if price is None:
                    raise ValueError("Limit price required for LIMIT order")
                payload.update({
                    "type": "LIMIT",
                    "price": price,
                    "timeInForce": "GTC"
                })

            elif order_type_lower == 'stop-limit':
                if price is None or stop_price is None:
                    raise ValueError("Both price and stop_price required for STOP-LIMIT order")
                payload.update({
                    "type": "STOP",
                    "price": price,
                    "stopPrice": stop_price,
                    "timeInForce": "GTC"
                })

            else:
                raise ValueError("Unsupported order type. Use MARKET, LIMIT, or STOP-LIMIT.")

            logging.info(f"[REQUEST] POST /fapi/v1/order | Payload: {payload}")
            order = self.client.futures_create_order(**payload)
            logging.info(f"[RESPONSE] Order Response: {order}")

            important_keys = [
                "orderId", "symbol", "status", "side", "type",
                "price", "avgPrice", "origQty", "executedQty",
                "cumQuote", "updateTime"
            ]
            cleaned = {k: order[k] for k in important_keys if k in order}

            print("Order executed")
            print(json.dumps(cleaned, indent=4))

            return order

        except Exception as e:
            logging.error(f"[ERROR] General Exception: {e}")
            print(f"Error: {e}")
            raise

    # Fetch all Symbols
    def list_symbols(self):
        info = self.client.futures_exchange_info()
        symbols = [s['symbol'] for s in info['symbols']]
        return symbols


# driver Code
def main():
    api_key, api_secret = load_api_key()
    bot = TradingBot(api_key, api_secret, testnet=True)
    values = {'side':['BUY', 'SELL'], 'order_type':['MARKET', 'LIMIT', 'STOP-LIMIT']}

    symbols = set(bot.list_symbols())
    print("Available Symbols:", ", ".join(bot.list_symbols()[:5]), "...")
    try:
        symbol = input("Enter trading Symbol : ").strip().upper()

        if symbol not in symbols:
            print(f"Error: {symbol} Symbol not Found")
            return

        side = input("Order side (BUY/SELL): ").strip().upper()
        if side not in values['side']:
            print(f"Error: {side}, Invalid side")
            return

        order_type = input("Order type (MARKET/LIMIT/STOP-LIMIT): ").strip().upper()
        if order_type not in values['order_type']:
            print(f"Error: {order_type}, Invalid order_type")
            return

        quantity = float(input("Quantity: ").strip())
        if quantity <= 0:
            print("Quantity should be greater than 0")

        price = None
        stop_price = None
        if order_type == 'LIMIT':
            price = float(input("Limit Price: ").strip())
        elif order_type == 'STOP-LIMIT':
            price = float(input("Limit Price: ").strip())
            stop_price = float(input("Stop Price: ").strip())
        bot.place_order(symbol, side, order_type, quantity, price, stop_price)

    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
