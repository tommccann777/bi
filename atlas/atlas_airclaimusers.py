
# TMC/MMC   - scans user records in airclaim contract and saves to csv file
# 1.0.1 - 3 Jun 2022 - TMC - added configurable kyc_contract, csv filename changed to airclaimusers_<datetime>.csv
# 2.0.0 - 7 Jun 2022 - TMC - directed output to an Atlas database

from datetime import datetime, timezone
import calendar
import json
from locale import currency
from subprocess import Popen, PIPE
from pymongo import MongoClient

version = '2.0.0'

# added these configurable fields, manipulate them here to change the function of 'get_users_table_data', 'get_freeos_balance',
# 'get_point_airclaim_balance', 'get_freeos_kyc', and 'get_users' please check each command for more information
# endpoint = "https://proton.greymass.com"
# freeos_contract = "freeosclaim"
# kyc_contract = "eosio.proton"
endpoint = "https://protontestnet.greymass.com"
freeos_contract = "freeos5"
kyc_contract = "freeosconfig"
sample_size = 10000


def get_unix_time():
    t = datetime.now(timezone.utc)
    unixtime = calendar.timegm(t.utctimetuple())
    return unixtime

def get_utcdatetime():
    t = datetime.now(timezone.utc)
    return t.strftime('%Y-%m-%dT%H:%M:%S')


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
        print(f"An error occurred: {proc_err}")
        return status, proc_output, proc_err


def get_users_table_data(account):
    # changed the command to include the configurable fields 'endpoint' and 'freeos_contract'
    # (original command was f"cleos -u https://proton.greymass.com get table freeosclaim {account} users")
    get_csv_cmd = f"cleos -u {endpoint} get table {freeos_contract} {account} users"
    status, response, error = runcmd(get_csv_cmd)
    json_data = json.loads(response)

    if len(json_data['rows']):
        user_record = json_data['rows'][0]
        user_stake = user_record['stake']
        user_stake = user_stake.split()[0]
        user_account_type = user_record['account_type']
        user_registered_in_week = user_record['registered_iteration']
        user_staked_in_week = user_record['staked_iteration']
        user_votes = user_record['votes']
        user_issuances = user_record['issuances']
        user_last_issuance = user_record['last_issuance']
    else:
        user_stake = '0.000000'
        user_account_type = 0
        user_registered_in_week = 0
        user_staked_in_week = 0
        user_votes = 0
        user_issuances = 0
        user_last_issuance = 0

    return user_stake, user_account_type, user_registered_in_week,\
        user_staked_in_week, user_votes, user_issuances, user_last_issuance

 
def get_freeos_balance(account):
    # changed the command to include the configurable field 'endpoint'
    # (original command was f'cleos -u https://proton.greymass.com/ get table freeostokens {account} accounts')
    get_freeos_balance_cmd = f'cleos -u {endpoint} get table freeostokens {account} accounts'
    status, response, error = runcmd(get_freeos_balance_cmd)
    json_data = json.loads(response)

    freeos_balance = 0

    if len(json_data['rows']):
        balance_record = json_data['rows'][0]
        user_balance_str = balance_record['balance']
        freeos_balance = float(user_balance_str.split()[0])

    return freeos_balance


def get_point_airclaim_balance(account):
    # changed the command to include the configurable fields 'endpoint' and 'freeos_contract'
    # (original command was f'cleos -u https://proton.greymass.com/ get table freeosclaim {account} accounts')
    get_point_airclaim_balance_cmd = f'cleos -u {endpoint} get table {freeos_contract} {account} accounts'
    status, response, error = runcmd(get_point_airclaim_balance_cmd)
    json_data = json.loads(response)

    point_balance = 0
    airkey_balance = 0

    if len(json_data['rows']):
        for balance_object in json_data['rows']:
            currency_balance = balance_object['balance']
            currencyName = currency_balance.split()[1]
            if 'POINT' in currencyName:
                point_balance = float(currency_balance.split()[0])
            elif 'AIRKEY' in currencyName:
                airkey_record = float(currency_balance.split()[0])

    return point_balance, airkey_balance


def get_freeos_kyc(account):
    # changed the command to include the configurable field 'endpoint'
    get_freeos_kyc_cmd = f'cleos -u {endpoint} get table {kyc_contract} {kyc_contract} usersinfo --lower {account} --upper {account}'
    status, response, error = runcmd(get_freeos_kyc_cmd)
    json_data = json.loads(response)

    # changed the default values for 'kyc_level', 'kyc_provider', and 'kyc_date' to empty fields
    kyc_level = ''
    kyc_provider = ''
    kyc_date = ''

    if len(json_data['rows']):
        if len(json_data['rows'][0]['kyc']):
            for balance_object in json_data['rows'][0]['kyc']:
                kyc_level = balance_object['kyc_level']
                kyc_provider = balance_object['kyc_provider']
                kyc_date = balance_object['kyc_date']

    return kyc_level, kyc_provider,kyc_date


def getusers():
    # changed the command to include the configurable fields 'endpoint', 'freeos_contract', and 'sample_size'
    get_table_cmd = f"cleos -u {endpoint} get scope {freeos_contract} -t users -l {sample_size}"
    status, response, error = runcmd(get_table_cmd)
    json_data = json.loads(response)
    scope_array = json_data['rows']

    batch_time = get_unix_time()
    batch_datetime = get_utcdatetime()

    print(f'Version {version} - Starting process at {batch_time}')

    client = MongoClient("mongodb+srv://fellenbrais:simpleCat8house@cluster0.u0z6l.mongodb.net/demofreeos")
    db=client.qa5users

    for scope_object in scope_array:
        user_scope = scope_object['scope']
        print(f'Processing record for {user_scope}')

        user_stake, user_account_type, user_registered_in_week,\
        user_staked_in_week, user_votes, user_issuances, user_last_issuance = get_users_table_data(user_scope)
        freeos_balance = get_freeos_balance(user_scope)
        point_balance, airkey_balance = get_point_airclaim_balance(user_scope)
        kyc_level, kyc_provider,kyc_date = get_freeos_kyc(user_scope)

        #create the dict to write away
        user = {
            'account': user_scope,
            'user_stake': user_stake,
            'user_account_type': user_account_type,
            'user_registered_in_week': user_registered_in_week,
            'user_staked_in_week': user_staked_in_week,
            'user_votes': user_votes,
            'user_issuances': user_issuances,
            'user_last_issuance': user_last_issuance,
            'freeos_balance': freeos_balance,
            'point_balance': point_balance,
            'airkey_balance': airkey_balance,
            'kyc_level': kyc_level,
            'kyc_provider': kyc_provider,
            'kyc_date': kyc_date
        }

        result=db.users.insert_one(user)
        
    end_time = get_unix_time()
    print(f'Ending process at {end_time}')

    time_taken = end_time - batch_time
    print(f'Process took {time_taken} seconds')


if __name__ == '__main__':
    getusers()
    #get_unix_time()
