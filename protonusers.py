from datetime import datetime, timezone
import calendar
from subprocess import Popen, PIPE
import json

endpoint = "https://proton.greymass.com"
page_size = 200
pages_to_fetch = 500000

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

def get_unix_time():
    t = datetime.now(timezone.utc)
    unixtime = calendar.timegm(t.utctimetuple())
    return unixtime

def getusers():

    pages = 0
    more_flag = False
    next_specifier = ""

    # open output file for writing
    unix_time = get_unix_time()

    with open(f"protonusers_{unix_time}.csv", "w") as csv_file:
        csv_file.write("acc,verified,verifier,kyc_level,kyc_provider,kyc_date,freedao_timestamp\n")

        start_time = unix_time
        print(f'Starting process at {start_time}')
    
        while True:
            if more_flag:
                next_specifier = f'--lower {next_key} '
            get_table_cmd = f"cleos -u {endpoint} get table eosio.proton eosio.proton usersinfo {next_specifier} -l {page_size}"
            print(f'running: {pages}: {get_table_cmd}')
            status, response, error = runcmd(get_table_cmd)
            json_data = json.loads(response)
            pages += 1
            user_array = json_data['rows']
            num_rows = len(user_array)
            print(f'{num_rows} rows fetched')
            for user_object in user_array:
                acc = user_object['acc']
                verified = user_object['verified']
                verifier = user_object['verifier']
                kyc_level = ''
                kyc_provider = ''
                kyc_date = ''
                for kyc_object in user_object['kyc']:
                    kyc_level = kyc_object['kyc_level']
                    kyc_provider = kyc_object['kyc_provider']
                    kyc_date = kyc_object['kyc_date']
                if len(user_object['kyc']) > 0:
                    unix_time = get_unix_time()
                    user_data = f'{acc},{verified},{verifier},"{kyc_level}",{kyc_provider},{kyc_date},{unix_time}'
                    csv_file.write(f'{user_data}\n')

            more_flag = json_data['more']
            next_key = json_data['next_key']
            # print(f'more: {more_flag}, next_key: {next_key}')
            
            if more_flag == False or pages == pages_to_fetch:
                break;

        csv_file.close()

        end_time = unix_time
        print(f'Ending process at {end_time}')

        time_taken = end_time - start_time
        print(f'Process took {time_taken} seconds')



if __name__ == '__main__':
    getusers()
