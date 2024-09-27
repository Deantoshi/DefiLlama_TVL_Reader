import pandas as pd
import requests
from datetime import datetime, timezone
import time
from datetime import date
from pandas import json_normalize
import numpy as np
import json
from cloud_storage import cloud_storage as cs
from flask import Flask, send_from_directory, send_file, make_response, jsonify, url_for, Response, stream_with_context
from flask_cors import CORS
import os
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.auth import default
from google.oauth2 import service_account
import pandas as pd
import io
from io import BytesIO
import logging
import time
import zipfile
import datetime
import csv

COOLDOWN_TIME = 5
START_DATE = '2024-07-08'
PRICE_BLOCKCHAIN = 'optimism'
OPTIMISM_TOKEN_ADDRESS = '0x4200000000000000000000000000000000000042'
WETH_TOKEN_ADDRESS = '0x4200000000000000000000000000000000000006'

CLOUD_BUCKET_NAME = 'cooldowns2'
CLOUD_PRICE_FILENAME = 'token_prices.zip'
CLOUD_DATA_FILENAME = 'super_fest.zip'

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
        category = 'tokensInUsd'
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
    token_columns_2 = [col for col in df2.columns if col != 'timestamp']

    # # shared token columns
    token_columns = list(set(token_columns) & set(token_columns_2))

    df1 = df1[token_columns]
    df2 = df2[token_columns]


    # Add the dataframes
    result = df1[token_columns].add(df2[token_columns], fill_value=0)

    # Reset the index to make 'timestamp' a column again
    result = result.reset_index()

    return result

# # transposes our token columns
def transpose_df(df):
    token_columns = [col for col in df.columns if col not in ['timestamp', 'pool_type']]

    # Melt the DataFrame
    df_melted = pd.melt(df, 
                        id_vars=['timestamp', 'pool_type'],
                        value_vars=token_columns,
                        var_name='token',
                        value_name='token_amount')

    # Reorder columns
    df_melted = df_melted[['timestamp', 'token', 'token_amount', 'pool_type']]

    # Sort by timestamp and token
    df_melted = df_melted.sort_values(['timestamp', 'token'])

    # Reset index
    df_melted = df_melted.reset_index(drop=True)

    df = df_melted

    return df

# Define a function to get the first non-NaN value
def first_valid(series):
    return series.dropna().iloc[0] if not series.dropna().empty else np.nan

# # makes a new column for the starting_token_amount
def add_start_token_amount_column(df):

    # Create the start_token_amount column
    df['start_token_amount'] = df.groupby(['token', 'pool_type'])['token_amount'].transform(first_valid)

    # Fill NaN values with 0 in the entire DataFrame
    df = df.fillna(0)

    # Sort the DataFrame by timestamp, token, and pool_type for better readability
    df = df.sort_values(['timestamp', 'token', 'pool_type'])

    # Reset the index
    df = df.reset_index(drop=True)

    return df

def add_change_in_token_amounts(df):

    df['raw_change_in_usd'] = df['token_amount'] - df['start_token_amount']
    df['percentage_change_in_usd'] = (df['token_amount'] / df['start_token_amount'] - 1)

    # Fill NaN values with 0 in the entire DataFrame
    df = df.fillna(0)
                   
    return df

# # will return the price per token from usd amount / quantity amount
def find_token_prices(usd_df, data, protocol_blockchain):

    category = 'tokens'
    quantity_df = get_historic_protocol_tvl_df(data, protocol_blockchain, category)
    start_unix = int(date_to_unix_timestamp(START_DATE))

    quantity_df = filter_start_timestamp(quantity_df, start_unix)

    df = divide_dataframes(usd_df, quantity_df)

    return df

# # finds tvl over time for each asset supply and borrow side
def find_tvl_over_time(df):
    # Convert timestamp to datetime
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.date

    # Group by date and pool_type, then sum token_usd_amount
    grouped_df = df.groupby(['date', 'pool_type'])['token_usd_amount'].sum().reset_index()

    # Rename the token_usd_amount column to daily_tvl
    grouped_df = grouped_df.rename(columns={'token_usd_amount': 'daily_tvl'})

    # Merge the daily_tvl back to the original dataframe
    df = df.merge(grouped_df[['date', 'pool_type', 'daily_tvl']], on=['date', 'pool_type'], how='left')

    df = df[['timestamp', 'date', 'token', 'pool_type', 'token_usd_amount', 'start_token_usd_amount', 'raw_change_in_usd', 'percentage_change_in_usd', 'daily_tvl']]

    return df

# # will only return rows for tokens specified in our protocol_pool.csv file for our desired protocol
def df_token_cleanup(protocol_df, df):

    unique_slugs = protocol_df['protocol_slug'].unique()

    df_list = []

    for unique_slug in unique_slugs:
        temp_df = df.loc[df['protocol'] == unique_slug]
        temp_protocol_df = protocol_df.loc[protocol_df['protocol_slug'] == unique_slug]
        unique_protocol_tokens = temp_protocol_df['token'].unique()

        temp_df = temp_df.loc[temp_df['token'].isin(unique_protocol_tokens)]

        df_list.append(temp_df)

    df = pd.concat(df_list)

    return df

# # gets our incentive history
def get_protocol_incentives_df():

    df = pd.read_csv('protocol_incentive_history.csv')
    return df

# Function to create new rows with incremented dates
def expand_rows(row):
    new_rows = [row.copy() for _ in range(7)]  # Create 7 copies (original + 6 new)
    for i in range(1, 7):
        new_rows[i]['date'] = row['date'] + pd.Timedelta(days=i)
    return pd.DataFrame(new_rows)

# # takes in a dataframe, and evenly distributes incentives accross the next 7 days
def fill_incentive_days(df):
    df['incentives_per_day'] = df['epoch_token_incentives'] / 7

    df['date'] = pd.to_datetime(df['date'])

    # Apply the function to each row and concatenate the results
    expanded_df = pd.concat([expand_rows(row) for _, row in df.iterrows()], ignore_index=True)

    # Sort the dataframe by date and other relevant columns if needed
    expanded_df = expanded_df.sort_values(['date', 'chain', 'platform', 'token', 'pool_type'])

    # Reset the index
    expanded_df = expanded_df.reset_index(drop=True)

    df = expanded_df
    
    return df

# # makes a unix timestamp column for our incentives
def get_incentives_unix_timestamps(df):
    df['timestamp'] = df['date'].apply(lambda x: pd.Timestamp(x).timestamp())

    df['timestamp'] = df['timestamp'].astype(int)
    return df

def make_dummy_cloud_price_df():

    df = pd.DataFrame()

    df['symbol'] = ['N/A']
    df['timestamp'] = [1776]
    df['date'] = ['2024-01-1']
    df['price'] = [1776]
    df['token_address'] = ['N/A']

    return df

def parse_date(date_string):
    try:
        # Try parsing with microseconds
        return datetime.strptime(str(date_string), '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d')
    except ValueError:
        try:
            # If that fails, try parsing without microseconds
            return datetime.strptime(str(date_string), '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
        except ValueError:
            # If both fail, return the original string
            return str(date_string)
        
# # will use the defillama price api to get the price of our token over time
# # returns a list of jsons
# # look here ** may need to remove the pricing functinoality that averages the two prices toghether
def get_token_price_json_list(df, blockchain, token_address):
    # url = "https://coins.llama.fi/batchHistorical?coins=%7B%22optimism:0x4200000000000000000000000000000000000042%22:%20%5B1666876743,%201666862343%5D%7D&searchWidth=600"
    # url = "https://coins.llama.fi/batchHistorical?coins=%7B%22optimism:0x4200000000000000000000000000000000000042%22:%20%5B1686876743,%201686862343%5D%7D&searchWidth=600"

    try:
        cloud_price_df = cs.read_zip_csv_from_cloud_storage(CLOUD_PRICE_FILENAME, CLOUD_BUCKET_NAME)
    except:
        cloud_price_df = make_dummy_cloud_price_df()

    cloud_price_df = cloud_price_df.loc[cloud_price_df['token_address'].str.upper() == token_address.upper()]

    if len(cloud_price_df) < 1:
        cloud_price_df = make_dummy_cloud_price_df()

    # If you want it as a string in 'YYYY-MM-DD' format instead of a date object
    cloud_price_df['date'] = pd.to_datetime(cloud_price_df['date']).dt.strftime('%Y-%m-%d')
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    # # finds any unique dates from the cloud
    cloud_date_list = cloud_price_df['date'].unique()
    # # finds all the unique dates from our defillama df
    df_date_list = df['date'].unique()

    # unique_incentive_timestamps = [ts for ts in unique_incentive_timestamps if ts not in cloud_price_df['timestamp'].values]

    # # finds the unique dates from defillama that are not present in the cloud
    dates_to_check_list = [unique_date for unique_date in df_date_list if unique_date not in cloud_date_list]
    # # turns these unique dates into unix timestamps
    unique_timestamp_to_check = [date_to_unix_timestamp(str(unique_date)) for unique_date in dates_to_check_list]

    # # placeholder timestamp to use
    if len(unique_timestamp_to_check) < 1:
        unique_timestamp_to_check = [date_to_unix_timestamp(df_date_list[0])]


    data_list = []
    for unique_timestamp in unique_timestamp_to_check:

        start_timestamp = unique_timestamp
        end_timestamp = start_timestamp + 14400

        url = "https://coins.llama.fi/batchHistorical?coins=%7B%22" + blockchain + ":" + token_address + "%22:%20%5B" + str(end_timestamp) + ",%20" + str(start_timestamp) + "%5D%7D&searchWidth=600"
        # Send a GET request to the URL
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            # Request was successful
            data = response.json()  # Parse the JSON response
            if len(data['coins']) > 0:
                data_list.append(data)
            else:
                unique_timestamp_to_check.append(1720569600)
                pass
        else:
            # Request failed
            print(f"Request failed with status code: {response.status_code}")
            print(response.text)  # Print the response content for more info on the error

        time.sleep(COOLDOWN_TIME)

    return data_list

# # makes a dataframe representation of our historic pricing info
def make_prices_df(data_list):
    
    df_list = []

    for data_json in data_list:
        if 'coins' in data_json and data_json['coins']:
            for token_address, coin_data in data_json['coins'].items():
                symbol = coin_data['symbol']
                prices = coin_data['prices']

                # Create DataFrame
                df = pd.DataFrame(prices)

                # Add symbol and token_address columns
                df['symbol'] = symbol
                df['token_address'] = token_address.split(':')[-1]  # Remove 'optimism:' prefix

                # Reorder columns
                df = df[['symbol', 'token_address', 'timestamp', 'price', 'confidence']]
                df['timestamp'] = df['timestamp'].astype(int)
                df['date'] = df['timestamp'].apply(unix_timestamp_to_date)
                # Calculate average price if there are multiple prices
                # if len(df) > 1:
                #     df = df.groupby(['symbol', 'token_address', 'timestamp'], as_index=False).agg({
                #         'price': 'mean',
                #         'confidence': 'mean'
                #     })

                df_list.append(df)

    # # will try combining our dataframe with our existing cloud one and dropping duplicates
    try:
        cloud_df = cs.read_zip_csv_from_cloud_storage(CLOUD_PRICE_FILENAME, CLOUD_BUCKET_NAME)
    except:
        cloud_df = make_dummy_cloud_price_df()

    if len(df_list) > 0:
        df = pd.concat(df_list, ignore_index=True)

        df = pd.concat([df, cloud_df])
        df = df.drop_duplicates(subset=['symbol', 'timestamp'])


    if len(df) > 0:
        df['timestamp'] = df['timestamp'].astype(int)
        df['date'] = df['timestamp'].apply(unix_timestamp_to_date)
        df = df[['symbol', 'token_address', 'timestamp', 'date','price']]
        cs.df_write_to_cloud_storage_as_zip(df, CLOUD_PRICE_FILENAME, CLOUD_BUCKET_NAME)
        return df
    else:
        return pd.DataFrame()  # Return an empty DataFrame if no valid data

# # takes in our incentives_per_day_df + incentives_timeseries_price_df
# # returns incentives_per_day_df with a new incentives_per_day_usd column that is the incentives_per day quantity * price
def find_daily_incentives_usd(incentives_per_day_df, incentives_timeseries_price_df):

    incentives_per_day_df['timestamp'] = incentives_per_day_df['timestamp'].astype(int)
    incentives_timeseries_price_df['timestamp'] = incentives_timeseries_price_df['timestamp'].astype(int)
    incentives_timeseries_price_df['price'] = incentives_timeseries_price_df['price'].astype(float)

    incentives_per_day_df = incentives_per_day_df.sort_values(by='timestamp')
    incentives_timeseries_price_df = incentives_timeseries_price_df.sort_values(by='timestamp')

    # Perform the merge_asof operation
    df_result = pd.merge_asof(incentives_per_day_df, incentives_timeseries_price_df[['timestamp', 'price']], 
                            on='timestamp', 
                            direction='nearest')
    
    # If you want to keep the original df_1 and just add the new 'price' column:
    incentives_per_day_df['price'] = df_result['price']


    incentives_per_day_df['incentives_per_day_usd'] = incentives_per_day_df['incentives_per_day'] * incentives_per_day_df['price']

    return incentives_per_day_df

# # runs all of our incentive data gathering functions and returns a dataframe of the info
def get_incentive_df():

    df = get_protocol_incentives_df()
    df = fill_incentive_days(df)
    df = get_incentives_unix_timestamps(df)
    data_list = get_token_price_json_list(df, PRICE_BLOCKCHAIN, OPTIMISM_TOKEN_ADDRESS)
    incentives_timeseries_price_df = make_prices_df(data_list)
    df = find_daily_incentives_usd(df, incentives_timeseries_price_df)

    return df

# # merges our two dataframes together
def combine_incentives_with_tvl(tvl_df, incentive_df):
    # Ensure 'date' columns are in the same format in both dataframes
    tvl_df['date'] = pd.to_datetime(tvl_df['date'])
    incentive_df['date'] = pd.to_datetime(incentive_df['date'])

    # Perform the left join
    result_df = pd.merge(
        tvl_df,
        incentive_df[[ # 'chain', 'platform', 'segment', 'partner', 'token', 'pool_type', 'protocol_slug', 'date', 
                      'protocol_slug', 'token', 'pool_type', 'date', 'epoch_token_incentives', 'incentives_per_day', 'price', 'incentives_per_day_usd']],
        how='left',
        left_on=['protocol', 'token', 'pool_type', 'date'],
        right_on=['protocol_slug', 'token', 'pool_type', 'date']
    )

    result_df = result_df.drop(['protocol_slug'], axis=1)

    result_df.fillna(0, inplace=True)

    return result_df

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
        if last_slug != protocol_slug:
            data = get_historic_protocol_tvl_json(protocol_slug)
            time.sleep(COOLDOWN_TIME)
        
        else:
            pass

        # if last_pool_type != pool_type:
        df = get_pool_type_df(data, protocol_blockchain, pool_type)
        df = filter_start_timestamp(df, start_unix)
        df['pool_type'] = pool_type
        df = transpose_df(df)
        df = add_start_token_amount_column(df)
        df = add_change_in_token_amounts(df)

        df.rename(columns = {'token_amount':'token_usd_amount', 'start_token_amount': 'start_token_usd_amount'}, inplace = True)

        df = find_tvl_over_time(df)

        df['protocol'] = protocol_slug

        df_list.append(df)
        
        # else:
        #     pass

        # # updates our last known values to reduce api calls and computation needs
        last_slug = protocol_slug
        last_pool_type = pool_type

        i += 1

    df = pd.concat(df_list)
    df = df_token_cleanup(protocol_df, df)
    incentive_df = get_incentive_df()
    df = combine_incentives_with_tvl(df, incentive_df)

    tvl_df = df
    df = get_weth_price_over_time(df)

    df = get_weth_price_change_since_start(df)

    merged_df = merge_tvl_and_weth_dfs(tvl_df, df)

    cs.df_write_to_cloud_storage_as_zip(merged_df, CLOUD_DATA_FILENAME, CLOUD_BUCKET_NAME)
    return merged_df

# # returns a dataframe of weth's price over time
def get_weth_price_over_time(df):

    data_list = get_token_price_json_list(df, PRICE_BLOCKCHAIN, WETH_TOKEN_ADDRESS)
    df = make_prices_df(data_list)

    return df

# # finds our start price, change in price usd, and change in price percentage per day relative to the start price
def get_weth_price_change_since_start(df):
    df[['timestamp']] = df[['timestamp']].astype(int)
    df['price'] = df['price'].astype(float)
    df = df.loc[df['symbol'] == 'WETH']
    temp_df = df.loc[df['timestamp'] == df['timestamp'].min()]
    start_price = temp_df['price'].min()
    df['weth_start_price'] = start_price

    df['weth_change_in_price_usd'] = df['price'] - df['weth_start_price']
    df['weth_change_in_price_percentage'] = (df['price'] / df['weth_start_price'] - 1)

    df = df.groupby('date').agg({
    'symbol': 'first',
    'token_address': 'first',
    'timestamp': 'first',
    'price': 'mean',
    'weth_start_price': 'first',
    'weth_change_in_price_usd': 'mean',
    'weth_change_in_price_percentage': 'mean'
    }).reset_index()
    
    df = df.sort_values(by='timestamp')

    return df

# # converts a unix into a date
def unix_timestamp_to_date(unix_timestamp):
    # Convert Unix timestamp to datetime object
    date_object = datetime.fromtimestamp(unix_timestamp)
    
    # Convert datetime object to string in desired format
    date_string = date_object.strftime("%Y-%m-%d")
    
    return date_string

# # merges those dataframes as the name implies
def merge_tvl_and_weth_dfs(tvl_df, weth_df):
    # Perform the left merge
    merged_df = tvl_df.merge(weth_df, on='date', how='left', suffixes=('', '_weth'))

    # Optionally, reorder the columns for better readability
    column_order = [
        'date', 'timestamp', 'token', 'pool_type', 'protocol',
        'token_usd_amount', 'start_token_usd_amount', 'raw_change_in_usd', 'percentage_change_in_usd',
        'daily_tvl', 'epoch_token_incentives', 'incentives_per_day', 'price',
        'incentives_per_day_usd', 'symbol', 'token_address', 'timestamp_weth',
        'price_weth', 'weth_start_price', 'weth_change_in_price_usd', 'weth_change_in_price_percentage'
    ]
    merged_df = merged_df[column_order]

    # Reset the index if needed
    merged_df = merged_df.reset_index(drop=True)

    print(merged_df)

    merged_df = merged_df.ffill()  # Forward fill: uses the last known value

    return merged_df

start_time = time.time()
df = run_all()
# tvl_df = df
# df = get_weth_price_over_time(df)

# df = get_weth_price_change_since_start(df)

# merged_df = merge_tvl_and_weth_dfs(tvl_df, df)
# df = cs.read_zip_csv_from_cloud_storage(CLOUD_PRICE_FILENAME, CLOUD_BUCKET_NAME)

print(df)
end_time = time.time()
print('Completed looking in: ', end_time - start_time, ' Seconds')

df.to_csv('test_test.csv', index=False)