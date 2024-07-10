import pandas as pd
import requests
from datetime import datetime, timezone
import time
from datetime import date

COOLDOWN_TIME = 1

# # makes an api call to defillama to find the historic data for a given chain
def chain_tvl_tracker(chain_name):
    url = "https://api.llama.fi/v2/historicalChainTvl/" + chain_name

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Request was successful
        data = response.json()  # Parse the JSON response
    else:
        # Request failed
        print(f"Request failed with status code: {response.status_code}")
        print(response.text)  # Print the response content for more info on the error

    return data

def protocol_tvl_tracker(protocol_name):
    
    url = "https://api.llama.fi/protocol/" + protocol_name

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Request was successful
        data = response.json()  # Parse the JSON response
    else:
        # Request failed
        print(f"Request failed with status code: {response.status_code}")
        print(response.text)  # Print the response content for more info on the error

    return data

# # will only return data for our specific protocol's blockchain
def filter_protocol_blockchain(data, blockchain):
    
    filtered_data = data['chainTvls'].get(blockchain, [])
    
    return filtered_data

def get_utc_start_date():
    # Create a datetime object for July 7th, 2024, at 00:00:00 UTC
    date = datetime(2024, 7, 8, 0, 0, 0, tzinfo=timezone.utc)

    # Convert to Unix timestamp
    unix_timestamp = int(date.timestamp())

    return unix_timestamp

def filter_start_date(data, start_unix_timestamp):

    try:
        filtered_data = [item for item in data if item['date'] >= start_unix_timestamp]
    except:
        filtered_data = [item for item in data['tvl'] if item['date'] > start_unix_timestamp]
    
    return filtered_data

# # finds the tvl at the start
def find_tvl_start(df, category_column_name):
    unique_category_list = df[category_column_name].unique()

    for unique_category in unique_category_list:
        temp_df = df.loc[df[category_column_name] == unique_category]

        tvl_start = temp_df['tvl'].min()

        df.loc[df[category_column_name] == unique_category, 'tvl_start'] = tvl_start

    return df

# # finds the current tvl
def find_tvl_current(df, category_column_name):
    unique_category_list = df[category_column_name].unique()

    for unique_category in unique_category_list:
        temp_df = df.loc[df[category_column_name] == unique_category]

        temp_df = temp_df.loc[temp_df['date'] == temp_df['date'].max()]

        tvl_current = temp_df['tvl'].min()

        df.loc[df[category_column_name] == unique_category, 'tvl_current'] = tvl_current

    return df

# # finds the current tvl
def find_tvl_delta(df):

    df['tvl_delta'] = df['tvl_current'] - df['tvl_start']

    return df

# # will run the tvl tracker for all of our superfest chains
def run_all_chain_tvl():
    chain_list = ['Base', 'Fraxtal','Mode','Optimism']
    
    start_unix_timestamp = get_utc_start_date()

    df_list = []

    for chain_name in chain_list:
        data = chain_tvl_tracker(chain_name)
        data = filter_start_date(data, start_unix_timestamp)
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df['chain'] = chain_name

        df_list.append(df)

        time.sleep(COOLDOWN_TIME)
    
    chain_df = pd.concat(df_list)

    chain_df = find_tvl_start(chain_df, 'chain')

    chain_df = find_tvl_current(chain_df, 'chain')

    chain_df = find_tvl_delta(chain_df)

    current_day = str(date.today())

    csv_name = 'blockchain_level_tvl_' + current_day + '.csv'

    csv_name = csv_name.replace('-', '_')

    chain_df.to_csv(csv_name, index=False)

    return chain_df

# # will try to make a dataframe for our project
def try_to_make_protocol_df(protocol_name, chain_name, start_unix_timestamp):

    data = protocol_tvl_tracker(protocol_name)

    data = filter_protocol_blockchain(data, chain_name)

    data = filter_start_date(data, start_unix_timestamp)
    
    df = pd.DataFrame(data)

    return df

# # will run the tvl tracker for all of our superfest chains
def run_all_protocol_tvl():

    protocol_blockchain_legend = pd.read_csv('protocol_blockchain_legend.csv')
    
    start_unix_timestamp = get_utc_start_date()

    df_list = []
    
    no_defi_llama_protocol_name_list = []
    no_defi_llama_chain_name_list = []

    i = 0

    while i < len(protocol_blockchain_legend):
        protocol_name = protocol_blockchain_legend['protocol'][i]
        chain_name = protocol_blockchain_legend['chain'][i]
        
        try:
            df = try_to_make_protocol_df(protocol_name, chain_name, start_unix_timestamp)
        except:
            df = pd.DataFrame()
            df_list.append(df)
        
        # # if the data exists defillama we will store this info
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['date'], unit='s')
            df['chain'] = chain_name
            df['protocol'] = protocol_name

            df_list.append(df)
        
        # # if the data DOES NOT exist in defillama, we will take note of the protocol name and the blockchain name combo of each to return later
        else:
            no_defi_llama_protocol_name_list.append(protocol_name)
            no_defi_llama_chain_name_list.append(chain_name)

        time.sleep(COOLDOWN_TIME)

        i += 1

    current_day = str(date.today())

    # # will only save our csv if our run has any data in it
    if len(df_list) > 0:

        chain_df = pd.concat(df_list)

        chain_df.rename(columns = {'totalLiquidityUSD':'tvl'}, inplace = True)

        chain_df = find_tvl_start(chain_df, 'chain')

        chain_df = find_tvl_current(chain_df, 'chain')

        chain_df = find_tvl_delta(chain_df)

        # # re-organizes our dataframe columns
        chain_df = chain_df[['date', 'protocol', 'chain', 'tvl', 'tvl_start', 'tvl_current', 'tvl_delta']]

        csv_name = current_day + '_protocol_level_tvl' + '.csv'

        csv_name = csv_name.replace('-', '_')

        chain_df.to_csv(csv_name, index=False)

    # # will only make our missing protocol data csv if we defillama doesn't have any in our specified list
    if len(no_defi_llama_protocol_name_list) > 0:
        # # will make a csv for protocol info that isn't available on defillama
        missing_protocol_blockchain_df = pd.DataFrame()
        missing_protocol_blockchain_df['protocol'] = no_defi_llama_protocol_name_list
        missing_protocol_blockchain_df['chain'] = no_defi_llama_chain_name_list
        missing_info_csv_name = current_day + '_missing_protocol_info' + '.csv'
        missing_info_csv_name = missing_info_csv_name.replace('-', '_')
        missing_protocol_blockchain_df.to_csv(missing_info_csv_name, index=False)
    
    try:
        return chain_df
    except:
        return 'Protocol Data is Missing from DefiLlama'

# chain_df = run_all_chain_tvl()
# print(chain_df)

protocol_df = run_all_protocol_tvl()
print(protocol_df)

# chain_name = 'Renzo'
# blockchain = 'Base'

# start_unix_timestamp = get_utc_start_date()

# data = protocol_tvl_tracker(chain_name)

# data = filter_protocol_blockchain(data, blockchain)

# data = filter_start_date(data, start_unix_timestamp)

# df = pd.DataFrame(data)
# df['date'] = pd.to_datetime(df['date'], unit='s')

# df.rename(columns = {'totalLiquidityUSD':'tvl'}, inplace = True)

# print(df)

