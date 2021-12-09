import covid_data_handler as cdh
import datetime

def test_parse_csv_data():
    data = cdh.parse_csv_data('nation_2021-10-28.csv')
    assert len(data) == 638 # THIS HAS BEEN CHANGED:
    # this has been changed as I have used a different data structure than intended.
    assert data[366]["hospital_cases"] == '8595'
    assert data[270]["date"] == '2021-01-31'
    
    # test if can handle no csv file
    cdh.parse_csv_data('fake_file.csv')
    
    # handle bad csv file
    cdh.parse_csv_data('bad_file.csv')
    
    # bad parameter
    cdh.parse_csv_data(12434)

def test_process_covid_csv_data():
    last7days_cases , current_hospital_cases , total_deaths = \
        cdh.process_covid_csv_data ( cdh.parse_csv_data (
            'nation_2021-10-28.csv' ) )
    assert last7days_cases == 240_299
    assert current_hospital_cases == 7_019
    assert total_deaths == 141_544
    
    # test function to see if it can handle no hospital cases or cumulative deaths
    # make API call to location type without the above: Exeter
    
    last7days_cases , current_hospital_cases , total_deaths = \
        cdh.process_covid_csv_data ( cdh.covid_API_request(
            location="Exeter", location_type="ltla"
            )['data'] )
    assert current_hospital_cases == "N/A"
    assert total_deaths == "N/A"

def test_covid_API_request():
    # test intended functionality
    data = cdh.covid_API_request()
    assert isinstance(data, dict)

def test_schedule_covid_updates():
    # test intended functionality
    cdh.schedule_covid_updates(update_interval=10, update_name='update test')
    assert len(cdh.scheduler.queue) == 1

    # test if it can handle datetime objects from the past
    time = datetime.datetime(year=1971, month=1, day=1, hour=1, minute=1, second=1, microsecond=1)
    cdh.schedule_covid_updates(update_interval=time, update_name='past_datetime')
    assert len(cdh.scheduler.queue) == 2
    
    # test if it can handle negative integers
    cdh.schedule_covid_updates(update_interval=-19, update_name="negative_int")
    assert len(cdh.scheduler.queue) == 3
    
    # test if it can handle integers in a string
    cdh.schedule_covid_updates(update_interval='10', update_name='int_as_str')
    assert len(cdh.scheduler.queue) == 4

    # test if it can handle bad string
    cdh.schedule_covid_updates(update_interval="bad", update_name="bad_string")
    assert len(cdh.scheduler.queue) == 4 # should exit out of function
    
    
def test_cancel_scheduled_update():
    # test intended functionality
    len_of_queue = len(cdh.scheduler.queue)
    cdh.schedule_covid_updates(update_interval = 60, update_name='test')
    assert len(cdh.scheduler.queue) == len_of_queue+1
    cdh.cancel_scheduled_update('test')
    assert len(cdh.scheduler.queue) == len_of_queue
    
    # test bad update_name
    cdh.cancel_scheduled_update("this_doesn't_exist")
