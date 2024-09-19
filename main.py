import pandas as pd
import requests
from datetime import datetime, timezone
import time
from datetime import date
from pandas import json_normalize
import numpy as np

COOLDOWN_TIME = 1
START_DATE = '2024-07-11'

def get_protocol_pool_config_df():

    df = pd.read_csv('protocol_pool.csv')

    return df

# # given a pool id, returns it's historic tvl and yield
def get_historic_protocol_pool_tvl_and_yield(pool_id):
    
    url = "https://yields.llama.fi/chart/" + pool_id

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


def get_historic_protocol_tvl_json(protocol_slug):
    url = "https://api.llama.fi/protocol/" + protocol_slug

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

# # makes a dataframe for our usd_supplied amounts
def get_historic_protocol_tvl_df(data, blockchain, category):
    # Extract the tokensInUsd list
    tokens_in_usd = data['chainTvls'][blockchain][category]
    # tokens_in_usd = data['chainTvls'][blockchain]['tokensInUsd']

    # Create a list of dictionaries with the correct structure
    formatted_data = [
        {
            'date': entry['date'],
            **entry['tokens']  # Unpack the tokens dictionary
        }
        for entry in tokens_in_usd
    ]

    # Create DataFrame directly from the formatted data
    df = pd.DataFrame(formatted_data)

    # Ensure 'date' is the first column
    columns = ['date'] + [col for col in df.columns if col != 'date']
    df = df[columns]

    # Sort the DataFrame by date
    df = df.sort_values('date')

    # Reset the index to have a standard numeric index
    df = df.reset_index(drop=True)

    df.rename(columns = {'date':'timestamp'}, inplace = True)

    # df['timestamp'] = pd.to_datetime(df['timestamp'])

    return df

# # simply turns our dataframe into a df adn goes ahead and casts our timestamp into a datetime data type
def turn_json_into_df(data):

    df = pd.DataFrame(data['data'])
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['tvlUsd'] = df['tvlUsd'].astype('float')

    df = df[['timestamp', 'tvlUsd', 'apy']]

    return df

def get_utc_start_day():
    # Create a datetime object for July 7th, 2024, at 00:00:00 UTC
    date = datetime(2024, 7, 10, 0, 0, 0, tzinfo=timezone.utc)

    return date

# # date string into unix timestamp
def date_to_unix_timestamp(date_string, format="%Y-%m-%d"):
    # Convert string to datetime object
    date_object = datetime.strptime(date_string, format)
    
    # Convert datetime object to Unix timestamp
    unix_timestamp = int(time.mktime(date_object.timetuple()))
    
    return unix_timestamp


# # only returns items that are greater than a certain day
def filter_start_timestamp(df, start_day):

    df = df.loc[df['timestamp'] >= start_day]
    
    return df

# # gives the tvl at the beginning of our tracking
def get_start_tvl(df):

    temp_df = df.loc[df['timestamp'] == df['timestamp'].min()]

    start_tvl = temp_df['tvlUsd'].min()

    df['start_tvl'] = start_tvl

    return df

def get_tvl_change_since_start(df):

    df['change_in_tvl'] = df['tvlUsd'] - df['start_tvl']

    return df

def run_all_apy():

    pool_df = get_protocol_pool_config_df()

    pool_id_list = pool_df['pool_id'].unique()

    df_list = []

    for pool_id in pool_id_list:

        data = get_historic_protocol_pool_tvl_and_yield(pool_id)
        df = turn_json_into_df(data)
        start_day = get_utc_start_day()
        df = filter_start_timestamp(df, start_day)
        df = get_start_tvl(df)
        df = get_tvl_change_since_start(df)
        df_list.append(df)
    
    df = pd.concat(df_list)

    return df


# # will manage pinging our api for us and making a subsequent df
def get_pool_type_df(data, protocol_blockchain, pool_type):

    df = pd.DataFrame()

    # # if it is a supply pool, then we make sure to add borrows to it to get a better total market size
    if pool_type == 'supply':
        category = 'tokensInUsd'
        df = get_historic_protocol_tvl_df(data, protocol_blockchain, category)
        pool_type = 'borrow'
        protocol_blockchain += '-borrowed'
        borrow_df = get_historic_protocol_tvl_df(data, protocol_blockchain, category)

        df = add_dataframes(df, borrow_df)

    elif pool_type == 'borrow':
        protocol_blockchain += '-borrowed'
        df = get_historic_protocol_tvl_df(data, protocol_blockchain, category)

    return df

# # divides our dataframe columns to essentially find the token prices
def divide_dataframes(df_top, df_bottom):
    # Ensure both dataframes have the same index
    df_top = df_top.set_index('timestamp')
    df_bottom = df_bottom.set_index('timestamp')

    # List of token columns (excluding 'timestamp' and 'pool_type')
    token_columns = [col for col in df_bottom.columns if col not in ['timestamp', 'pool_type']]

    # Perform element-wise division
    result = df_top[token_columns] / df_bottom[token_columns]

    # Reset the index to make 'timestamp' a column again
    result = result.reset_index()

    return result

# # adds our two dataframes together
def add_dataframes(df1, df2):
    # Ensure both dataframes have the same index
    df1 = df1.set_index('timestamp')
    df2 = df2.set_index('timestamp')

    # List of token columns (excluding 'timestamp')
    token_columns = [col for col in df1.columns if col != 'timestamp']

    # Add the dataframes
    result = df1[token_columns].add(df2[token_columns], fill_value=0)

    # Reset the index to make 'timestamp' a column again
    result = result.reset_index()

    return result

# # will the first numeric tvl for each token as their own columns
def add_min_token_columns(df):
    # List of token columns (excluding 'timestamp' and 'pool_type')
    token_columns = [col for col in df.columns if col not in ['timestamp', 'pool_type']]

    # Find the first non-NaN value for each token column
    min_values = df[token_columns].apply(lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan)

    # Create new columns with the minimum values
    for col in token_columns:
        df[f'min_{col}'] = min_values[col]

    return df

# # will return the price per token from usd amount / quantity amount
def find_token_prices(usd_df, data, protocol_blockchain):

    category = 'tokens'
    quantity_df = get_historic_protocol_tvl_df(data, protocol_blockchain, category)
    start_unix = int(date_to_unix_timestamp(START_DATE))

    quantity_df = filter_start_timestamp(quantity_df, start_unix)

    df = divide_dataframes(usd_df, quantity_df)

    return df

def run_all():
    protocol_df = get_protocol_pool_config_df()
    protocol_slug_list = protocol_df['protocol_slug'].tolist()
    protocol_blockchain_list = protocol_df['chain'].tolist()
    pool_type_list = protocol_df['pool_type'].tolist()
    token_list = protocol_df['token'].tolist()

    df_list = []

    start_unix = int(date_to_unix_timestamp(START_DATE))

    last_slug = ''
    last_token = ''
    last_pool_type = ''
    i = 0

    while i < len(protocol_slug_list):

        protocol_slug = protocol_slug_list[i]
        protocol_blockchain = protocol_blockchain_list[i]
        pool_type = pool_type_list[i]
        token = token_list[i]

        # # we will only send another api ping if we are using a new slug
        if (last_slug != protocol_slug) and (last_pool_type != pool_type):
            data = get_historic_protocol_tvl_json(protocol_slug)

            df = get_pool_type_df(data, protocol_blockchain, pool_type)

            df = filter_start_timestamp(df, start_unix)
            df['pool_type'] = pool_type
            df = add_min_token_columns(df)

            df_list.append(df)
        
        else:
            continue

        # # updates our last known values to reduce api calls and computation needs
        last_slug = protocol_slug
        last_pool_type = pool_type

        i += 1

    df = pd.concat(df_list)

    return df

df = run_all()

print(df)