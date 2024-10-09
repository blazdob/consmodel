import pandas as pd
import numpy as np
import holidays
import datetime


def individual_tariff_times(dates: np.array) -> np.array:
    """
	Generates tariff masks for the given dates

    Takes an array of dates and returns a matrix of 5 tariff masks from block 1 to 5.
    Each mask is a vector of 1 and 0. 1 means that the time datetime falls into the block.

	Args:
	----------
		dates: np.array
            Array of dates

	Returns:
	----------
		tariff_mask: np.array
			Tariff mask
	"""
    # Prepare array of holidays
    si_holidays = holidays.SI(years=(dates[0].year, dates[-1].year))

    # Tariff blocks table http://www.pisrs.si/Pis.web/npb/2024-01-0154-2022-01-3624-npb5-p2.pdf
    high_season_working = [
        3, 3, 3, 3, 3, 3, 2, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 2, 2, 3, 3
    ]
    low_season_working = [
        4, 4, 4, 4, 4, 4, 3, 2, 2, 2, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 3, 3, 4, 4
    ]
    high_season_workoff = [
        4, 4, 4, 4, 4, 4, 3, 2, 2, 2, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 3, 3, 4, 4
    ]
    low_season_workoff = [
        5, 5, 5, 5, 5, 5, 4, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 4, 4, 5, 5
    ]

    # combine blocks into two seasons
    high_season = [high_season_working, high_season_workoff]
    low_season = [low_season_working, low_season_workoff]

    # combine both seasons
    blocks = [low_season, high_season]

    # np.array([block_1, block_2, block_3, block_4, block_5])
    tariff_mask = np.zeros((5, len(dates)), dtype=int)

    i = 0
    for date in dates:
        date -= datetime.timedelta(minutes=15)
        if date in si_holidays or date.weekday() > 4:
            workoff = 1
        else:
            workoff = 0

        if 2 < date.month < 11:
            high_season = 0
        else:
            high_season = 1

        hour = date.hour
        # takes the correct block and subtracts 1 because array indexing starts at 0
        j = blocks[high_season][workoff][hour] - 1
        tariff_mask[j][i] = 1

        i += 1

    return tariff_mask