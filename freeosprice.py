#!/usr/bin/env python3
import json
import csv
import os
from urllib.request import urlopen
from datetime import datetime,timezone
from subprocess import Popen, PIPE

PRICEURL = "https://api.protonchain.com/v1/chain/exchange-rates/info"
ENDPOINT = "https://protontestnet.greymass.com"
CONTRACT = "dfinityclaim"
WEEK = 604800
DEBUG = True

def runcmd(cmd):
    try:
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        status = proc.returncode
        proc_output, proc_err = proc.communicate()
        proc_output = proc_output.strip()
        proc_err = proc_err.strip()
        if not status:
            if (not proc_output) or proc_err:
                status = -1
            else:
                status = 0
        return status, proc_output, proc_err
    except Exception as exp:
        return status, proc_output, proc_err


def usd_rate_equal(token1, token2):
    #return true if 2 tokens are equivalent in content i.e. they both have the same USD rate and volume
    #first find the USD rate object
    rates1 = token1['rates']
    for rate1 in rates1:
        if rate1['counterCurrency'] == 'USD':
            price1 = str(rate1['price'])
            volume1 = str(rate1['volume'])

    rates2 = token2['rates']
    for rate2 in rates2:
        if rate2['counterCurrency'] == 'USD':
            price2 = str(rate2['price'])
            volume2 = str(rate2['volume'])

    if price1 == price2 and volume1 == volume2:
        if DEBUG: print(f'token compare equal - prices: {price1},{price2} volumes: {volume1},{volume2}')
        return True
    else:
        if DEBUG: print(f'token compare not equal - prices: {price1},{price2} volumes: {volume1},{volume2}')
        return False


def writeprotonprice(histdata):
    # work out the weighted average price
    sumproduct = 0
    sumvolume = 0

    for token in histdata:
        rates = token['rates']
        for rate in rates:
            if rate['counterCurrency'] == 'USD':
                price = rate['price']
                volume = rate['volume']
                sumproduct += price * volume
                sumvolume += volume

    averageprice = sumproduct / sumvolume

    if DEBUG:
        freeostimestamp = int(datetime.now(timezone.utc).timestamp())
        auditfilename = f'{freeostimestamp}.csv'
        auditfile = open(auditfilename, "w")
        auditfile.write("price,volume,averageprice\n")
        for token in histdata:
            rates = token['rates']
            for rate in rates:
                price = rate['price']
                volume = rate['volume']
                ratecsvline = f'{price},{volume},{averageprice}\n'
                auditfile.write(ratecsvline)
        auditfile.close()

    command1 = f'cleos -u {ENDPOINT} push action {CONTRACT} currentrate \'[{averageprice}]\' -p freeosticker -x 600 -s -d -j >transaction0.json'
    command2 = f'cleos -u {ENDPOINT} sign transaction0.json -k $FREEOS_TICKER -p'
    if DEBUG: print(f'running: {command1}')
    if DEBUG: print(f'running: {command2}')
    runcmd(command1)
    runcmd(command2)

    
def pricestore(token):
    latestTimestamp = int(datetime.now(timezone.utc).timestamp())
    # write the timestamp into the token
    token['freeostimestamp'] = latestTimestamp
    if DEBUG: print(f'latest time = {latestTimestamp}')

    # temporary new list to write to file
    newhistdata = []

    # 1. maintain the history file containing one week of data
    jsonfile = "pricehist.json"
    if os.path.exists(jsonfile):
        # read the array of objects
        with open(jsonfile) as data_file:    
            histdata = json.load(data_file)
    else:        
        # initialise the history array
        histdata = []

    # work out if this is a record with new content as many records are repeats with a different timestamp
    # if the record is new (i.e. different than previous) then append it to the history array
    # also append if the history array is empty
    if not histdata or not usd_rate_equal(token, histdata[-1]):
        histdata.append(token)
    else:
        # if the latest record is not new (i.e. different than previous) then nothing else to do
        return False    # False indicates no new price record

    # prune the history file of old records
    if DEBUG: print(f'pruning {len} records...')
    for histtoken in histdata:
        rateTimestamp = histtoken['freeostimestamp']
        recordAge = latestTimestamp - rateTimestamp

        if recordAge < WEEK:
            newhistdata.append(histtoken)
        
    # write the array to file
    pricehistfile = open(jsonfile, "w")
    json.dump(newhistdata, pricehistfile)
    pricehistfile.close()

    # write the new price to the smart contract
    writeprotonprice(newhistdata)
    return True     # True indicates a price record was written


def freeosprice():
    pricejson = open("freeosprice.json", "a")  # append mode
    pricecsv = open("freeosprice.csv", "a")  # append mode

    # current unix time
    freeostimestamp = int(datetime.now(timezone.utc).timestamp())

    # store the response of URL
    response = urlopen(PRICEURL)
    
    # storing the JSON response from url in data
    data_json = json.loads(response.read())
    
    for token in data_json:
        if token['symbol'] == 'FREEOS':
            pricejson.write(json.dumps(token))
            pricejson.write("\n")
            rates = token['rates']
            for rate in rates:
                if rate['counterCurrency'] == 'USD':
                    # token has a USD exchange rate so store the token
                    if pricestore(token):   # if a new price is read and stored
                        price = str(rate['price'])
                        priceChangePercent = str(rate['priceChangePercent'])
                        volume = str(rate['volume'])
                        timestamp = str(rate['timestamp'])
                        price_csv = f'{freeostimestamp},{price},{priceChangePercent},{volume},{timestamp}\n'
                        pricecsv.write(price_csv)

    pricejson.close()
    pricecsv.close()


if __name__=='__main__':
    freeosprice()