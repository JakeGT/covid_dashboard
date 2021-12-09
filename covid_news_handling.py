'''
NAME
    covid_news_handling - Handles news API calls and scheduling

FUNCTIONS
    news_API_request: Makes an API request and loads the data
    update_news: Calls news_API_request and updates articles data
    news_formatter: Generates a list of title and article dictionaries
    add_removed_articles: Called when a user removes an article: needs to be remembered
    sch_update_news: Scheduler calls this function during scheduled update
    cancel_scheduled_update: Removes scheduled update from queue
    schedule_news_updates: Adds events to scheduler queue
    time_to_update_interval: Takes str to create datetime object and time in seconds to update
'''
import time
import sched
import logging
import datetime
from re import match
import requests
from markupsafe import Markup

api_key = '' # not a constant. changes based on config
config_covid_terms = "" # not a constant. changes based on config

news = []
formatted_news = []
removed_articles = []

scheduler = sched.scheduler(time.time, time.sleep)

scheduled_updates = {}

def news_API_request(covid_terms:str = "Covid COVID-19 coronavirus") -> dict:
    '''
    Makes a request to the newsapi and returns that data.

        Parameters:
            covid_terms (str): The terms that should be requested from the newsapi

        Returns:
            response (dict): The data from the newsapi
    '''
    if config_covid_terms:
        covid_terms = config_covid_terms
    logging.info("Beginning News API request")
    covid_terms_list = covid_terms.split(" ")
    url = f'''https://newsapi.org/v2/everything?q=+{"+".join(covid_terms_list)}&apikey={api_key}'''
    try:
        response = requests.get(url)
        logging.info("API request successful")
        return response.json()
    # The following are possible responses if internet is unstable or down
    # If API request fails, schedule a new attempt in 30 seconds and inform user.
    except requests.exceptions.ConnectionError as error:
        logging.warning("Connection Error: %s", error)
        print("Connection error: News API call failed. Check internet connection.")
        print("Retrying in 30 seconds...")
        schedule_news_updates(30, "API Retry")
    except requests.exceptions.Timeout as error:
        logging.warning("Connection Timed Out: %s", error)
        print("Connection timed out: News API call failed. Check internet connection.")
        print("Retrying in 30 seconds...")
        schedule_news_updates(30, "API Retry")

def update_news(terms = "Covid COVID-19 coronavirus") -> None:
    '''
    Calls the news_API_request then updates the news list. This is clear the list the be re-filled
    with news articles except those that have been removed by the user.
    '''
    logging.info("Updating Covid News")
    api_response = news_API_request(terms)
    news.clear()
    if api_response:
        if not api_response["status"] == "error":
            for article in api_response["articles"]:
                if article["title"] not in removed_articles:
                    news.append(article)
            news_formatter()

def news_formatter() -> None:
    '''
    This will take the news list and generate a list of dictionaries that contains the title
    and the article contents. Will format the contents to 100 characters long and put within
    a HTML <a> tag to hyperlink content to article link.
    '''
    logging.info("Formatting news for dashboard.")
    formatted_news.clear()
    if len(news) >= 5:
        temp_news_list = news[:5]
    else:
        temp_news_list = news[:]
    for article in temp_news_list:
        temp_formatted = {}
        url = article['url']
        temp_formatted["title"] = article['title']
        content = Markup(f"""<a href = '{url}'
                         style = 'color:black'>{article['content'][0:100]}...</a>""")
        temp_formatted["content"] = content
        formatted_news.append(temp_formatted)

def add_removed_article(article_title:str) -> None:
    '''
    Called when the user removes an article. This will add the removed article to a list and call
    the news_formatted function. The user will never see the same article again and will be removed
    from the dashboard.
    '''
    removed_articles.append(article_title)
    article_titles = [article_title_news['title'] for article_title_news in news]
    if article_title in article_titles:
        article_index = article_titles.index(article_title)
        del news[article_index]
        logging.info("%s has been removed. Will not be shown again", article_title)
    else:
        logging.warning("User has attempted to remove an article that doesn't exist.")
        logging.debug("%s was to be removed", article_title)
        logging.debug("%s are the articles that are in the list", str(article_titles))
    news_formatter()

def sch_update_news(update_time: datetime.datetime, update_name: str, repeat: bool) -> None:
    '''
    This procedure is called by the scheduler to run an update and determine whether to schedule
    a new update depending on whether this was a repeating update

        Parameters:
            update_interval (int|datetime.datetime): the datetime object of the update time
            update_name (str): the name of the scheduled update
            repeat (bool): whether the update is repeating
    '''
    logging.info("Running scheduled news update %s", update_name)
    del scheduled_updates[update_name] # scheduled update called, delete from dict
    update_news()
    if repeat: # this is for if the user requested a repeating update
        update_time = update_time + datetime.timedelta(days=1)
        logging.info("News update (%s) to be repeated. Scheduling next update", update_name)
        schedule_news_updates(update_time, update_name, repeat)

def cancel_scheduled_update(update_name:str) -> None:
    '''
    This procedure simply cancels a scheduled update and remoevd it from the scheduled update dict

        Parameters:
            update_name(str): The key of the scheduled update in dict
    '''
    logging.info("Cancelling scheduled news update %s", update_name)
    if update_name in scheduled_updates:
        # if the update exists, then find the event and remove it from the scheduler and
        # list of scheduled updates
        event = scheduled_updates[update_name]["event"]
        scheduler.cancel(event)
        del scheduled_updates[update_name]
        logging.info("%s successfully removed from scheduled news updates", update_name)
        logging.debug("news scheduled_updates = %s", scheduled_updates)
        logging.debug("news Scheduler queue = %s", scheduler.queue)
    else:
        logging.warning("""A request has been sent to cancel
        a scheduled news update that does not exist""")

def schedule_news_updates(update_interval: int|str|datetime.datetime,
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
    logging.info("Scheduling news update: %s", update_name)
    if isinstance(update_interval, str):
        logging.info("Recieved string. Attempting to parse...")
        # if it's a string, test if its coming from the dashboard and therefore HH:MM format
        if match("[0-9]{2}:[0-9]{}2", update_interval):
            time_to_update, update_time = time_to_update_interval(update_interval)
            logging.debug("time_to_update = %s", str(time_to_update))
            logging.debug("update_time = %s", str(update_time))
        elif match("[0-9]+", update_interval):
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
            time_to_update,1,sch_update_news,(update_time, update_name, repeat, )
            )
        scheduled_updates[update_name] = {
            "event": event,
            "update_time":update_time,
            "repeat":repeat
            }
        logging.info("Scheduled news update: %s", update_name)
        logging.debug("Scheduler Queue (news): %s", str(scheduler.queue))
    else:
        # should modify HTML to tell user that the app cannot schedule update as the
        # update name is already in use but outside bounds of CA
        logging.warning("Tried to schedule update with same name as existing update")
        logging.debug("Update Name: %s", update_name)
        logging.debug("Scheduler Queue (news): %s", str(scheduler.queue))

def time_to_update_interval(update_interval:str) -> tuple[int,int]:
    '''
    Function to convert the data taken from the website form into a datetime object and
    a integer variable with the amount of time from now to the update time recieved.

        Parameters:
            update_interval (str): The time in "HH:MM" format.

        Returns:
            time_to_update (int): The amount of seconds from now to the update time
            update_time (datetime.datetime): datetime object that corresponds to the update time
    '''
    # this function is called when recieving time from dashboard (HH:MM format)
    logging.info("Converting string to datetime object and seconds to update")
    logging.debug("update_interval = %s", str(update_interval))
    hrs, mins = map(int, update_interval.split(":"))
    # calculate datetime object of update
    update_time = datetime.datetime.now().replace(hour=hrs, minute=mins, second=0, microsecond=0)
    if update_time < datetime.datetime.now():
        update_time = update_time + datetime.timedelta(days=1)
    time_to_update = (update_time - datetime.datetime.now()).total_seconds()
    return time_to_update, update_time
