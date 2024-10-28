import pandas as pd

def extract_first_date_of_month(df):
    """Function returns list of first date of every month from the input dataframe."""
    # Convert the datetime column to datetime type
    df['date_time'] = pd.to_datetime(df['date_time'])
    # Extract the first date of every month by grouping and resetting index
    first_dates = list(df.loc[df.groupby((df['date_time'] - pd.Timedelta(minutes=15)).dt.to_period('M'))['date_time'].idxmin()].reset_index(drop=True)["datetime"])

    # Display the result
    return first_dates