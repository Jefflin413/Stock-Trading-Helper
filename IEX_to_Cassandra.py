# Author: Ping-Feng Lin

# This code aims to push stock data from IEX Cloud into Cassandra database according to every set interval at the scheduled time
# The interval for intraday data has 3 levels: second, minute and hour
# Scheduled time is the trading hour on business days; 9:30 to 16:00, Monday to Friday excluding holidays
# Intraday minute-level information will be corrected before the beginning of trading hour next day
# Daily data will be push to the database after the end of the trading hour

import os
import time
import schedule
from threading import Timer
from datetime import date, datetime
import holidays

from iexfinance.stocks import Stock
from cassandra.cluster import Cluster

from Stock_source_utils import StockDataQueue, RepeatedTimer

def Retrieve_Process(interval_type, iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr):
    now = datetime.now()
    timestamp = int(datetime.timestamp(now))
    if interval_type == 'sec':
        print("Retrieve_Process_sec is working... " + now.strftime("%m/%d/%Y - %H:%M:%S"))
        StockDataQueue_sec.push(iexstocks.get_ohlc(), timestamp)
    elif interval_type == 'min':
        print("Retrieve_Process_min is working... " + now.strftime("%m/%d/%Y - %H:%M:%S"))
        StockDataQueue_min.push(StockDataQueue_sec.extract(), timestamp)
    elif interval_type == 'hr':
        print("Retrieve_Process_hr is working... " + now.strftime("%m/%d/%Y - %H:%M:%S"))
        StockDataQueue_hr.push(StockDataQueue_min.extract(), timestamp)


def StartReceivingThread(iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr):
    # if it is a business day, then start receiving data
    if date.today() not in us_holidays:
        # use two threads to retrieve second-level data because it happens a lot that the API takes longer than 1 sec to respond, thus cause missing value
        # two threads iteratively get and push data into database can make the process more robost
        # to make the iterative operation work, we set the beginning time of the day at 09:29:59, the first execution for thread1 will be at 09:30:01, and then 09:30:03, 09:30:05, ...
        # as comparison, the first execution for thread2 is at 09:30:02,  and then 09:30:04, 09:30:06, ...
        # RepeatedTimer(interval, stop_after, function, *args, **kwargs)
        thread1 = Timer(0, RepeatedTimer, args=(2, 23400, Retrieve_Process, 'sec', iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr))
        thread2 = Timer(1, RepeatedTimer, args=(2, 23400, Retrieve_Process, 'sec', iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr))
        # Because we start at 09:29:59, so every tasks has to wait 1 sec to start
        thread3 = Timer(1, RepeatedTimer, args=(60, 23400, Retrieve_Process, 'min', iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr))
        thread4 = Timer(1, RepeatedTimer, args=(3600, 23400, Retrieve_Process, 'hr', iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr))
        
        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()


# Setting the the server version that the API connects to
# In Jupyter notebook: %env IEX_API_VERSION=iexcloud-sandbox
# None of the belowing works,only set the environmental variable outside works
# export IEX_API_VERSION=iexcloud-sandbox

#os.environ['IEX_API_VERSION'] = 'iexcloud-sandbox'
#os.putenv('IEX_API_VERSION', 'iexcloud-sandbox')
#os.system("echo $IEX_API_VERSION")

# Connect to Cassandra
c_cluster = Cluster(['10.142.0.12'])
c_session = c_cluster.connect('stock')

# Making sure that retrieving and pushing data won't be activated on holidays
us_holidays = holidays.US()

# Reading API access key
token = os.environ['IEX_TOKEN']

# Currently only support the below 10 companies' stock data
# BA: BOEING CO, CRM: SALESFORCE.COM INC, CVS: CVS HEALTH CORPORATION, DIS: WALT DISNEY COMPANY (THE), MS: MORGAN STANLEY
# JPM: JPMORGAN CHASE & CO., WMT: WALMART INC, V: VISA INC, VMW: VMWARE INC, VZ: VERIZON COMMUNICATIONS
stock_symbol = ["BA", "CRM", "CVS", "DIS", "MS", "JPM", "WMT", "V", "VMW", "VZ"]
iexstocks = Stock(stock_symbol, token=token)

# StockDataQueue is used for connecting with Cassandra and managing of retrieved data
# For second-level data, the user can only access to data in the latest 6.5 hours, but we keep twice the amount for buffer (2 * 6.5 * 60 * 60 = 46800).
# Minute-level data is accessible for the latest 60 trading days, and we also keeps twice the amount in the database (2 * 60 * 6.5 * 60 = 46800).
# Hourly-level data holds for the lastest 1 year (~=1694). The same, nearly twice the data are hold (3400).

StockDataQueue_sec = StockDataQueue(stock_symbol, 'sec', 46800, c_session)
StockDataQueue_min = StockDataQueue(stock_symbol, 'min', 46800, c_session)
StockDataQueue_hr = StockDataQueue(stock_symbol, 'hr', 3400, c_session)

# Because the schedule doesn't account for the time consumption of the task, which means that the task execution time will delay the starting time on the next round
# To solve this, we have to let the task only be responsible for setting and starting the threads, so that it can finish and report to the scheduler immediately and make no delay for the next scheduled task
schedule.every().monday.at("09:29:59").do(StartReceivingThread, iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr)
schedule.every().tuesday.at("09:29:59").do(StartReceivingThread, iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr)
schedule.every().wednesday.at("09:29:59").do(StartReceivingThread, iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr)
schedule.every().thursday.at("09:29:59").do(StartReceivingThread, iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr)
schedule.every().friday.at("09:29:59").do(StartReceivingThread, iexstocks, StockDataQueue_sec, StockDataQueue_min, StockDataQueue_hr)

print(schedule.jobs)
while True:
    schedule.run_pending()
    time.sleep(0.5)




