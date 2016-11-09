import json
import time
import dateutil.parser
import requests
from steemapi import SteemWalletRPC

# Config
witness = "pharesim"
numberoftrades = 25
minchange = 0.03
maxchange = 0.5
offset = 0.00

rpc = SteemWalletRPC("localhost", 8092, "", "")

def btc_usd():
  prices = {}
  exchanges = {
    'bitfinex': {
      'url': 'https://api.bitfinex.com/v1/pubticker/BTCUSD',
      'price': 'last_price',
      'volume': 'volume'
    },
    'coinbase': {
      'url': 'https://api.exchange.coinbase.com/products/BTC-USD/ticker',
      'price': 'price',
      'volume': 'volume'
    },
    'okcoin': {
      'url': 'https://www.okcoin.com/api/v1/ticker.do?symbol=btc_usd',
      'price': 'last',
      'volume': 'vol'
    },
    'bitstamp': {
      'url': 'https://www.bitstamp.net/api/v2/ticker/btcusd/',
      'price': 'price',
      'volume': 'volume'
    }
  }
  for key, value in exchanges.items():
    try:
      r = json.loads(requests.request("GET",value['url']).text)
      prices[key] = {'price': float(r[value['price']]), 'volume': float(r[value['volume']])};
    except:
      pass

  if not prices:
    raise Exception("All BTC price feeds failed.")
  avg_price    = 0
  total_volume = 0
  for p in prices.values():
    avg_price    += p['price'] * p['volume']
    total_volume += p['volume']
  avg_price = avg_price / total_volume
  return avg_price

if __name__ == '__main__':
  quantities = {'steem':0,'steembtc':0,'sbd':0,'sbdbtc':0}
  hist = json.loads(requests.request("GET","https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-STEEM").text)
  for i in range(numberoftrades):
    quantities['steem'] += hist["result"][i]["Quantity"]
    quantities['steembtc'] += hist["result"][i]["Total"]

  hist = json.loads(requests.request("GET","https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_STEEM").text)
  for i in range(numberoftrades):
    quantities['steem'] += float(hist[i]['amount'])
    quantities['steembtc'] += float(hist[i]['total'])

  if quantities['steem'] > 0:
    price = round((quantities['steembtc']/quantities['steem']*btc_usd())*(1+offset),3)
    curr = float(rpc.get_witness(witness)['sbd_exchange_rate']['base'][:5])
    if (price > (curr * (1 + minchange)) and price < (curr * (1 + maxchange))) or (price < (curr * (1 - minchange)) and price > (curr * (1 - maxchange))):
      hist = json.loads(requests.request("GET","https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-SBD").text)
      for i in range(numberoftrades):
        quantities['sbd'] += hist["result"][i]["Quantity"]
        quantities['sbdbtc'] += hist["result"][i]["Total"]

      hist = json.loads(requests.request("GET","https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_SBD").text)
      for i in range(numberoftrades):
        quantities['sbd'] += float(hist[i]['amount'])
        quantities['sbdbtc'] += float(hist[i]['total'])

      bias = 1 / (quantities['sbdbtc']/quantities['sbd']*btc_usd())

      price = format(price, ".3f")
      bias = format(bias, ".3f")
      rpc.publish_feed(witness, {"base": price +" SBD", "quote": bias + " STEEM"}, True)
      print("Published price feed: " + price + " USD/STEEM with a bias of " + bias + " at " + time.ctime())
