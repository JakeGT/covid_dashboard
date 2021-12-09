import json
import datetime
import covid_news_handling as cnh

with open("config.json", encoding="ascii") as config_file:
    config = json.load(config_file)
    cnh.api_key = config["news"]["api_key"]

def test_news_API_request():
    assert cnh.news_API_request()
    assert cnh.news_API_request('Covid COVID-19 coronavirus') == cnh.news_API_request()

def test_update_news():
    cnh.update_news('test')

def test_news_formatter():
    cnh.news_formatter()

def test_add_removed_article():
    # test intended functionality
    temp_news = cnh.news[:]
    article = cnh.news[0]["title"]
    cnh.add_removed_article(article)
    assert cnh.news == temp_news[1:]
    
    # test bad article name
    cnh.add_removed_article("fake_article")
    # test bad type
    cnh.add_removed_article(123)
    
def test_schedule_news_updates():
    # test intended functionality
    cnh.schedule_news_updates(update_interval=10, update_name='update test')
    assert len(cnh.scheduler.queue) == 1

    # test if it can handle datetime objects from the past
    time = datetime.datetime(year=1971, month=1, day=1, hour=1, minute=1, second=1, microsecond=1)
    cnh.schedule_news_updates(update_interval=time, update_name='past_datetime')
    assert len(cnh.scheduler.queue) == 2
    
    # test if it can handle negative integers
    cnh.schedule_news_updates(update_interval=-19, update_name="negative_int")
    assert len(cnh.scheduler.queue) == 3
    
    # test if it can handle integers in a string
    cnh.schedule_news_updates(update_interval='10', update_name='int_as_str')
    assert len(cnh.scheduler.queue) == 4

    # test if it can handle bad string
    cnh.schedule_news_updates(update_interval="bad", update_name="bad_string")
    assert len(cnh.scheduler.queue) == 4 # should exit out of function
    
    # test for HH:MM format
    cnh.schedule_news_updates(update_interval="12:34", update_name="HH:MM")
    assert len(cnh.scheduler.queue) == 5
    
    # test for bad HH:MM format
    cnh.schedule_news_updates(update_interval="54:43", update_name="bad_HH:MM")
    assert len(cnh.scheduler.queue) == 5 # should exit out of function
    
def test_cancel_scheduled_update():
    # test intended functionality
    len_of_queue = len(cnh.scheduler.queue)
    cnh.schedule_news_updates(update_interval = 60, update_name='test')
    assert len(cnh.scheduler.queue) == len_of_queue+1
    cnh.cancel_scheduled_update('test')
    assert len(cnh.scheduler.queue) == len_of_queue
    
    # test bad update_name
    cnh.cancel_scheduled_update("this_doesn't_exist")