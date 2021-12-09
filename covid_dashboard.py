'''
NAME
    covid_dashboard

FUNCTIONS
    home(): Main function that runs when accessing the dashboard
    collate_update_lists():  Merges the two scheduled updates list from covid news and data
    format_update_toasts(): Generates and returns a list containing the scheduled updates
    data_init(): Loads data from APIs
    load_config(str): Loads config file and sets correct variables accordingly
'''

import logging
import json
from flask import Flask, render_template, request
import covid_data_handler as cdh
import covid_news_handling as cnh

logging.basicConfig(filename="logs.log", level=logging.DEBUG)

app = Flask(__name__)

scheduled_updates = {}

@app.route("/index", methods = ['POST', 'GET'])
@app.route("/", methods = ['POST', 'GET'])
def home():
    '''
    The homepage of the covid dashboard. This will call scheduler polls,
    collect input data, and take removed news articles and scheduled updates.

        Returns:
            str: HTML code for browser to render dashboard.
    '''
    
    # Run schedulers in non-blocking mode everytime page is refreshed to poll events
    # This should really be a theading.Timer()
    logging.info("Polling schedulers")
    cdh.scheduler.run(blocking=False)
    cnh.scheduler.run(blocking=False)
    
    logging.info("User requested home page.")
    if cdh.covid_data["data"] and cdh.national_covid_data["data"]:
        # if data loaded from API successfully
        national_stats = cdh.process_covid_csv_data(cdh.national_covid_data["data"])
        local_7_day_infections = cdh.process_covid_csv_data(cdh.covid_data["data"])[0]
        # we only want the first value in the tuple returned from this function hence the [0]
        location = cdh.covid_data["data"][0]["area_name"]
        nation_location = cdh.national_covid_data["data"][0]["area_name"]
        national_7day_infections = f"{national_stats[0]} cases"
        hospital_cases = f"{national_stats[1]} hospital cases"
        deaths_total = f"{national_stats[2]} total deaths"
    else: # if the internet is down or the covid API fails, just display N/A
        local_7_day_infections = "N/A"
        location = "N/A"
        nation_location = "N/A"
        national_7day_infections = "N/A"
        hospital_cases = "N/A"
        deaths_total = "N/A"

    remove_news_notif = request.args.get("notif")
    update_time = request.args.get("update")
    update_name = request.args.get("two")
    update_repeat = request.args.get("repeat")
    update_covid_data = request.args.get("covid-data")
    update_news = request.args.get("news")
    repeat = bool(update_repeat)
    remove_scheduled_update = request.args.get("update_item")
    if update_covid_data or update_news:
        logging.info("User has requested to schedule an update.")
        update_title = f"{update_name} - {update_time}"
        logging.debug("update_title = %s", update_title)
        if update_title not in scheduled_updates:
            if update_covid_data:
                cdh.schedule_covid_updates(update_time, update_title, repeat)
            if update_news:
                cnh.schedule_news_updates(update_time, update_title, repeat)
        else:
            logging.warning("""Attempted to add scheduled update with
            same name and time as existing scheduled update.""")
    if remove_scheduled_update:
        logging.info("User has requested to removed a scheduled update.")
        logging.debug("removed_scheduled_update = %s", remove_scheduled_update)
        update = scheduled_updates[remove_scheduled_update]
        if update["news"]:
            cnh.cancel_scheduled_update(remove_scheduled_update)
        if update["covid"]:
            cdh.cancel_scheduled_update(remove_scheduled_update)

    if remove_news_notif:
        logging.info("User has request article be removed")
        cnh.add_removed_article(remove_news_notif)

    logging.info("Updating scheduled updates toasts")
    collate_update_lists()
    updates = format_update_toasts()

    logging.info("Rendering webpage")
    return render_template(
        "index.html",
        title = "Covid Dashboard",
        location = location,
        local_7day_infections = f"{local_7_day_infections} cases",
        nation_location = nation_location,
        national_7day_infections = national_7day_infections,
        hospital_cases = hospital_cases,
        deaths_total = deaths_total,
        news_articles = cnh.formatted_news,
        updates = updates
    )

def collate_update_lists() -> None:
    '''
    This collects the scheduled update lists from the covid data handler and the
    covid news handler, merges them into another dictionary to be presented to the user.
    It will combine updates with the same name/title.
    '''
    logging.info("Collating lists of scheduled updates")
    scheduled_updates.clear()
    for covid_update in cdh.scheduled_updates:
        if covid_update in cnh.scheduled_updates:
            scheduled_updates[covid_update] = {"covid":True, "news":True,
                "time":cdh.scheduled_updates[covid_update]["update_time"],
                "repeat": cdh.scheduled_updates[covid_update]["repeat"]}
        else:
            scheduled_updates[covid_update] = {"covid":True, "news":False,
                "time":cdh.scheduled_updates[covid_update]["update_time"],
                "repeat": cdh.scheduled_updates[covid_update]["repeat"]}
    for news_update in cnh.scheduled_updates:
        if news_update not in scheduled_updates:
            scheduled_updates[news_update] = {"covid":False, "news":True,
                "time":cnh.scheduled_updates[news_update]["update_time"],
                "repeat": cnh.scheduled_updates[news_update]["repeat"]}


def format_update_toasts() -> list:
    '''
    This will take the scheduled updates dictionary and generate a list to be
    rendered in the HTML in a way that is nicely visible to the user.
    '''
    logging.info("Formatting scheduled updates for toasts")
    formatted_updates = []
    for update_name, update_details in scheduled_updates.items():
        update_time = update_details['time'].strftime("%H:%M")
        formatted_updates.append(
            {"title": update_name,
             "content": f"""Updating {'COVID Data'*update_details['covid']}
             {'and' * update_details['covid'] * update_details['news']} 
             {'Covid News'*update_details['news']}
             at {update_time} {'every day'*update_details['repeat']}"""}
        )
    return formatted_updates


def data_init() -> None:
    '''
    This makes the first API call before the Flask app is loaded.
    '''
    logging.info("Making API requests before webpage starts")
    if cdh.config_covid_location:
        cdh.covid_data = cdh.covid_API_request(cdh.config_covid_location["area_name"],
                                               cdh.config_covid_location["area_type"])
    else:
        cdh.covid_data = cdh.covid_API_request()
    cdh.national_covid_data = cdh.covid_API_request(location_type="overview")
    cnh.update_news()
    if cdh.covid_data and cnh.news:
        logging.info("All data loaded from APIs. Data init finished.")

def load_config(filename="config.json") -> None:
    '''
    Loads the config file and sets the corresponding values in the covid data handler
    and the covid news handler.
    '''
    try:
        with open(filename, encoding="ascii") as config_file:
            config = json.load(config_file)
    except IOError:
        logging.info("Config file could not be loaded. Using default values.")
        print("A config file cannot be found. Using default values.")
    else:
        try:
            cnh.config_covid_terms = config["news"]["covid_terms"]
            cdh.config_covid_location = config["covid"]
        except KeyError:
            logging.warning("Config file values invalid. Using default values")
            print("The config file is invalid. Please check the values in the config file.")
        try:
            cnh.api_key = config["news"]["api_key"]
        except KeyError:
            logging.warning("API key cannot be loaded from config. News will not be loaded.")
            print("""The config file does not have an API key.
            You will not be able to load any news articles.""")



# stream-line starting of Flask server - load data on start so when user requests home page, they
# don't have to wait for the completion of an API call.
# No need to prevent home page request manually as when data is being loaded, no other requests are
# processed as program is single-threadded


if __name__ == "__main__":
    load_config()
    data_init()
    app.run()
