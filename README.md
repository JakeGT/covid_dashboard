# Introduction
This is the COVID Dashboard created by Jake Talling for his Uni Coursework

The app will display information about the latest covid statistics and covid news and allow you to specify specific times to update the data on the app. All of which is done through the web interface.

# Prerequesits
Python 3.10
uk_covid19
Flask
#### For unit testing
pytest

# Installation
uk_covid19: pip install uk_covid19
Flask: pip install flask
pytest: pip install pytest

# How to use

First, open the config.json in your preferred text editor.
1. Add your API key for newsapi.org
(Optional from here)
2. Add/modify the terms to search for in your news feed (covid_terms)
3. Modify the area_name to your location. If you wish to change the scope of your local area, you can change the area_type to the following:
overview: Data for all of the UK
nation: Either England, NI, Scotland or Wales
region: Regional
nhsRegion: NHS regional
utla: Upper-tier local authority
ltla: Lower-tier local authority

Next, you can run the application by opening covid_dashboard.py
To access the dashboard, open the following link in your browser: 127.0.0.1:5000

On the left, you can see scheduled updates. This should be empty as you have not scheduled any updates. This will update accordingly as you add updates to the app.

On the right, you can see your news feed. This will have the latest news searched with the terms you entered earlier in the config file. If you wish to remove a news article, click the X. It will not appear again.

If you wish to scheduled an update, you can use the data entry fields in the middle of the page. Enter a name and time, select what you would like to update (covid data and/or news) and whether you would like the update to repeat once a day at the same time. Once filled in, hit the submit button.
You cannot schedule an update with the same title and time as another update. You will not be informed if your update has been rejected.
If you would like to cancel an update, you can click the x in the scheduled updates on the left side of the screen of the update you would like to cancel.

# Testing
If you would like to ensure all of the code functions properly in your environment, run the pytest module as such: open terminal and CD into the directory containing the covid_dashboard.py file. Run the following:
pytest tests/

# Author
Jake George Talling
github.com/JakeGT

# Project Link:
https://github.com/JakeGT/covid_dashboard
