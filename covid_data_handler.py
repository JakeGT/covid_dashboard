'''
This module handles the covid API, covid data, key statistics calculations and
scheduling covid updates.

'''
import logging
import sched
import datetime
import time
from re import match
import requests
from uk_covid19 import Cov19API
import uk_covid19

covid_data = {}
national_covid_data = {}
scheduled_updates = {}

config_covid_location = {}

scheduler = sched.scheduler(time.time, time.sleep)


def parse_csv_data(filename:str) -> list[str]:
    '''
    Take a csv file and return a list split by each row of data

        Parameters:
            filename (str): The name of the Covid data CSV file

        Returns:
            data_lines (list[str]): The list containing each row of data as a string
    '''
    headers = {
        "areaCode":"area_code",
        "areaName":"area_name",
        "areaType":"area_type",
        "date": "date",
        "cumDailyNsoDeathsByDeathDate":"cum_deaths",
        "hospitalCases":"hospital_cases",
        "newCasesBySpecimenDate":"new_cases"
    }
    try:
        with open(str(filename), encoding="ascii") as file:
            data_lines = file.read().splitlines() # file to list split by new lines (rows)
            logging.info("CSV file opened successfully: %s", filename)
    except IOError:
        logging.warning("Cannot open CSV file")
    else:
        file_headers = data_lines[0].split(",")
        new_headers = []
        for header in file_headers:
            if header in headers:
                new_headers.append(headers[header])
            else:
                logging.warning("Unknown header in the CSV file: %s", header)
                new_headers.append(header)
        data_lines[0] = ",".join(new_headers)
        # renaming headers - API does this automatically, but currently reading from CSV
        covid_data_local = convert_covid_csv_data_to_list_dict(data_lines)
        return covid_data_local


def convert_covid_csv_data_to_list_dict(covid_csv_data:list[str]) -> list[dict]:
    '''
    Takes the parsed csv covid data and split rows into lists appendding each row to a new list
    This function is only necessary when reading from a CSV. The function turns the CSV file into
    the same data structure that is returned from the API.

        Parameters:
            covid_csv_data (list[str]): Covid data parsed through the function parse_csv_data
            the data is each row of data as a string of the entire row

        Returns:
            covid_data_local (list[dict]): Covid data seperated in list by row and
            converted to a dictionary
    '''
    logging.info("""convert_covid_csv_data_to_list_dict called:
    Converting CSV file to list of dictionaries for further data processing.""")
    covid_data_headers = covid_csv_data[0].split(',') # save covid data headers for dict
    covid_csv_data_local = covid_csv_data[1:] # store data excluding headers in another list
    covid_data_local = []
    for row in covid_csv_data_local:
        row_data = row.split(',') # split row into individual pieces of data
        data = {}
        for header, data_entry in zip(covid_data_headers, row_data):
            data[header] = data_entry
            # take individual data and map header (data title) to data in dict
        covid_data_local.append(data)
        # add dict to list of Covid data
    covid_data_local.sort(key = lambda x: x['date'], reverse=True)
    # just in case data is not in order sort by date, most recent date as index 0.
    return covid_data_local

def process_covid_csv_data(covid_data_local:list[dict]) -> tuple[int|str, int|str, int|str]:
    '''
    Takes the Covid data processed from parse_csv_data and returns the number of cases for the past
    3 days, the number of hospital cases and the number of cumulative deaths

        Parameters:
            covid_data (list): The Covid data from parse_csv_data - Covid data in a list containing
                dictionaries in header:data form

        Returns:
            total_cases_last_7_days (int|str): The total number of cases in the past 7 days -
                ignoring empty data entries and the first day or N/A if not applicable
            hospital_cases (int|str): The number of hospital cases from most recent data
                or N/A if not applicable
            cum_deaths (int|str): The number of cumulative deaths from the most recent data
                or N/A if not applicable
    '''
    logging.info("""process_covid_csv_data called:
    Processing COVID data to generate 3 key statistics""")
    first_date = next(
        (index for index, item in enumerate(covid_data_local) if item['new_cases']), None
        ) # finding the index of the first non empty entry of data.
          # if there is valid entry, return none.
    if first_date is not None: # test to mkae sure there is data
        first_date += 1 # skip the first day
        if len(covid_data_local) - first_date > 7:
            days = 7 # if there are 7 days worth of data
        else:
            days = len(covid_data_local) - first_date
            # if not, then just calculate the remaining amounts of data
        total_cases_last_7_days = 0
        for days in range(days):
            total_cases_last_7_days += int(
                covid_data_local[first_date+days]['new_cases']
            ) # loop through 7 days and add all of them to total
    else: # if there is no data
        logging.info("There is no data to calculate the 7 day covid rate.")
        total_cases_last_7_days = "N/A"

    # The following is the while loop as above but for the next statistics, without adding 1 day
    first_date = next(
        (i for i, item in enumerate(covid_data_local) if item['hospital_cases']), None
        ) # this is the same as the next() statement as above but for hospital cases
    if first_date is not None: # makes sure data is there as some API calls don't have this data.
        hospital_cases = int(covid_data_local[first_date]['hospital_cases'])
    else: # if API call doesn't have this data, simply diplay N/A to user.
        logging.info("There is insufficient data to show hospital cases.")
        hospital_cases = "N/A"
    first_date = next(
        (i for i, item in enumerate(covid_data_local) if item['cum_deaths']), None
        ) # this is the same as the next() statement as above but for cumulative deaths
    if first_date is not None: # makes sure data is there as some API calls don't have this data.
        cum_deaths = int(covid_data_local[first_date]["cum_deaths"])
    else: # if API call doesn't have this data, simply display N/A to user.
        logging.info("There is insufficient data to show cumulative deaths.")
        cum_deaths = "N/A"
    return total_cases_last_7_days, hospital_cases, cum_deaths

def covid_API_request(location:str = "Exeter", location_type:str = "ltla") -> dict:
    '''
    This requests information from the UK Covid API

        Parameters:
            location (str): The location for information to be request about, default=Exeter
            location_type (str): The type of location, default=ltla (Lower-tier local
            authority data)

         Returns:
            data (dict): The data the API returns based on the filter and structure provided
    '''
    logging.info("Beginning API request to update COVID data.")
    if location_type != "overview":
        location_data = [
            "areaType="+location_type,
            "areaName="+location
            ]
    else: # if areaType is overview, there is no need for areaName in request
        location_data = ["areaType=overview"]
     # generate a filter as required by covid API
    structure_data = {
        "area_name": "areaName",
        "date": "date",
        "cum_deaths": "cumDailyNsoDeathsByDeathDate",
        "hospital_cases": "hospitalCases",
        "new_cases": "newCasesBySpecimenDate"
    } # information needed from API and renaming as per API parameters
    try:
        api = Cov19API(filters=location_data, structure=structure_data)
        data = api.get_json() # json data already processed by API.
        logging.info("API call completed")
        return data
    except uk_covid19.exceptions.FailedRequestError as error:
        # may occur if there is a connection error
        logging.warning("COVID API call failed: %s", error)
        print("COVID API call failed: Check internet connection")
        print("Retrying in 30 seconds...")
        schedule_covid_updates(30, "API Retry")
        return {"data": None}
    except requests.exceptions.ConnectionError as error:
        # may occur if there is a connection error
        logging.warning("COVID API call failed: %s", error)
        print("COVID API call failed: Check internet connection")
        print("Retrying in 30 seconds...")
        schedule_covid_updates(30, "API Retry")
        return {"data": None}

def sch_update_covid_data(update_time: datetime.datetime, update_name: int, repeat: bool) -> None:
    '''
    This procedure is called by the scheduler to run an update and determine whether to schedule
    a new update depending on whether this was a repeating update

        Parameters:
            update_interval (int|datetime.datetime): the datetime object of the update time
            update_name (str): the name of the scheduled update
            repeat (bool): whether the update is repeating
    '''
    global covid_data
    global national_covid_data
    # no way around using global variables here. They needs to be assigned on update
    logging.info("Running scheduled COVID update %s", update_name)
    del scheduled_updates[update_name] # scheduled update called, delete from dict
    if config_covid_location: # make sure that covid API requests use config data if it is there
        location_type = config_covid_location["area_type"]
        location = config_covid_location["area_name"]
        api_response = covid_API_request(location, location_type)
    else:
        api_response = covid_API_request()
    national_api_response = covid_API_request(location_type="overview")
    if api_response:
        covid_data = api_response
    if national_api_response:
        national_covid_data = national_api_response
    if repeat: # this is for if the user requested a repeating update
        update_time = update_time + datetime.timedelta(days=1)
        logging.info("Covid update (%s) to be repeated. Scheduling next update", update_name)
        schedule_covid_updates(update_time, update_name, repeat)

def cancel_scheduled_update(update_name:str) -> None:
    '''
    This procedure simply cancels a scheduled update and remoevd it from the scheduled update dict

        Parameters:
            update_name(str): The key of the scheduled update in dict
    '''
    logging.info("Cancelling schduled COVID update named: %s", update_name)
    if update_name in scheduled_updates:
        # if the update exists, then find the event and remove it from the scheduler and
        # list of scheduled updates
        event = scheduled_updates[update_name]["event"]
        scheduler.cancel(event)
        del scheduled_updates[update_name]
        logging.info("%s successfully removed from scheduled COVID updates", update_name)
        logging.debug("COVID scheduled_updates = %s", scheduled_updates)
        logging.debug("COVID Scheduler queue = %s", scheduler.queue)
    else:
        logging.warning("""Attempted to remove scheduled update event from scheduler
        but event does not exist: %s""", update_name)


def schedule_covid_updates(update_interval: int|str|datetime.datetime,
                           update_name: int, repeat=False) -> None:
    '''
    This procedure is called when the user requests to schedule an update. All scheduled events
    are added to the scheduled_updates dictionary with the name as the key.

        Parameters:
            update_interval (int|str|datetime.datetime):
                if int, time to update in seconds
                if str, time of next update in the format HH:MM
                if datetime.datetime, the datetime of next update

            update_name (str): the name of the scheduled update
            repeat (bool): whether the update is repeating
    '''
    logging.info("Scheduling covid update: %s", update_name)
    if isinstance(update_interval, str):
        logging.info("Recieved string. Attempting to parse...")
        # if it's a string, test if its coming from the dashboard and therefore HH:MM format
        if match("^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", update_interval):
            time_to_update, update_time = time_to_update_interval(update_interval)
            logging.debug("time_to_update = %s", str(time_to_update))
            logging.debug("update_time = %s", str(update_time))
        elif update_interval.isdigit():
            update_interval = int(update_interval)
            # this will trigger the if statement below for int types
        else:
            logging.warning("Can't parse update time. Cancelling update scheduling")
            # If we can't parse the update time parameter, cancel and exit function
            return None
    if isinstance(update_interval, datetime.datetime):
        # if datetime object, calcuate time to next update
        logging.info("Recieved datetime object.")
        update_time = update_interval
        if update_time < datetime.datetime.now():
            update_time = datetime.datetime.now().replace(
                hour=update_time.hour, minute=update_time.minute, second=0, microsecond=0
                )
            if update_time < datetime.datetime.now():
                update_time += datetime.timedelta(days=1)
            # if the datetime object is in the past, we assume the next point where that
            # hour and minute occur
        time_to_update = (update_time - datetime.datetime.now()).total_seconds()
    if isinstance(update_interval, int):
        # if int, calculate datetime object of update
        logging.info("Recieved int. Parsing as seconds from now.")
        time_to_update = abs(update_interval)
        # if number is negative, assume absolute value anyways
        update_time = datetime.datetime.now() + datetime.timedelta(seconds = update_interval)
    logging.info("Covid update time has been parsed")
    logging.debug("Update time parsed as %s", str(update_time))

    if update_name not in scheduled_updates:
        # make sure we are not trying to create an update with a duplicate name
        event = scheduler.enter(
            time_to_update,1,sch_update_covid_data,(update_time, update_name, repeat, )
            )
        scheduled_updates[update_name] = {
            "event": event,
            "update_time":update_time,
            "repeat":repeat
            }
        logging.info("Scheduled COVID update: %s", update_name)
        logging.debug("Scheduler Queue (covid): %s", str(scheduler.queue))
    else:
        # should modify HTML to tell user that the app cannot schedule update as the
        # update name is already in use but outside bounds of CA
        logging.warning("Tried to schedule update with same name as existing update")
        logging.debug("Update Name: %s", update_name)
        logging.debug("Scheduler Queue (covid): %s", str(scheduler.queue))

def time_to_update_interval(update_interval:str) -> tuple[int, datetime.datetime]:
    '''
    Function to convert the data taken from the website form into a datetime object and
    a integer variable with the amount of time from now to the update time recieved.

        Parameters:
            update_interval (str): The time in "HH:MM" format.

        Returns:
            time_to_update (int): The amount of seconds from now to the update time
            update_time (datetime.datetime): datetime object that corresponds to the update time
    '''
    logging.info("Converting string to datetime object and seconds to update")
    logging.debug("update_interval = %s", str(update_interval))
    hrs, mins = map(int, update_interval.split(":"))
    update_time = datetime.datetime.now().replace(hour=hrs, minute=mins, second=0, microsecond=0)
    if update_time < datetime.datetime.now():
        update_time = update_time + datetime.timedelta(days=1)
    time_to_update = (update_time - datetime.datetime.now()).total_seconds()
    return time_to_update, update_time


if __name__ == "__main__":
    # if file is run individually, run these tests.
    print("Running self tests")
    TEST_FILE = "nation_2021-10-28.csv"
    data_covid = parse_csv_data(TEST_FILE)
    last_7_days_cases, current_hospital_cases, total_deaths = (
        process_covid_csv_data(data_covid)
    )
    print(f"""{last_7_days_cases = :,} (expected 240,299)\n
{current_hospital_cases = :,} (expeced 7,019)\n
{total_deaths = :,} (expected 141,544)""")
