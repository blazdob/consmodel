import pandas as pd
def extract_first_date_of_month(df):
    """Function returns list of first date of every month from the input dataframe."""
    # Convert the datetime column to datetime type
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Extract the first date of every month by grouping and resetting index
    first_dates = list(df.loc[df.groupby((df['datetime'] - pd.Timedelta(minutes=15)).dt.to_period('M'))['datetime'].idxmin()].reset_index(drop=True)["datetime"])

    # Display the result
    return first_dates