from collections import deque
from datetime import datetime
from cassandra import ConsistencyLevel
from cassandra.query import BatchStatement
from threading import Event, Thread, Timer
import time
import json

class StockDataQueue:
    def __init__(self, stock_symbol, interval_type, length, c_session):
        self.queue = deque()
        self.length = length
        self.c_session = c_session
        self.interval_type = interval_type

        if self.interval_type == 'sec':
            self.interval = 1
        elif self.interval_type == 'min':
            self.interval = 60
        elif self.interval_type == 'hr':
            self.interval = 3600

        self.H = {}
        self.L = {}
        for symbol in stock_symbol:
            self.H[symbol] = 0
            self.L[symbol] = float('inf')
            
            
    def __InsertCassandraStock(self):
        # symbol: str -> text, OHLC: dict (json) -> text, interval_type: str -> text, ts: datetime -> timestamp
        return self.c_session.prepare(
            'INSERT INTO stocks_history (OHLC,symbol,interval_type, ts) VALUES (?, ?, ?, ?)'
            )

    def __UpdateCassandraStock(self):
        return self.c_session.prepare(
            'UPDATE stocks_history SET OHLC =? WHERE symbol=? AND interval_type=? AND ts=?'
            )
    
    # Deleting data from Cassandra table
    def __DeleteCassandraStock(self):
        return self.c_session.prepare(
            'DELETE FROM stocks_history WHERE symbol=? AND interval_type=? AND ts=?'
            )
    
    def push(self, OHLCs, timestamp):
        # Sometimes there will be missing timestamp in the queue, it is caused by overmuch time consumed when asking stock data from IEX API, so the later data retriever write data earlier than the earlier data retriever
        # So when there's a missing value, we will supplement it with the duplicate of the current value
        # Later when the program which is responsible for this timestamp starts to write data, it will update the previous supplemented value
        # In other situation if the time consumed is longer than the set interval, it will force the data retriever to skip one round of data retrieval
        # In that case the supplemented data won't be update and will be just the same as the descendent
        # There are 4 situations that could happen at the moment when the data is about to be pushed into the queue
        # 1. the latest timestamp is exactly 1 second before the current timestamp, then we can append our current data to the end of the queue
        # 2. the lastest timestamp is earlier than the current timestamp more than 1 second but not more than 10 seconds. In this case we duplicate the current data and supplement the missing value
        # 3. the latest timestamp is bigger than the current timestamp.
        #     In this case, we pop out all the data which is later than the current timestamp until we found a timestamp which is less than or equal to the current timestamp, and see now it belongs to situation 1 or situation 2
        # 4. large difference between current timestamp and the last timestamp. It indicate the current one is the beginning of a new day, so just append it to the end of the queue
        # The above analysis is only for the problem in retrieving data every second. Introducing interval into the code can generalize it for every minute data and every hour data

        # unit of timestamp is second 
        stack = []
        while self.queue and self.queue[-1]['timestamp'] > timestamp:
            stack.append(self.queue.pop())
            
        # An execution of a batch of operations is faster than multiple executions every single operations in a loop
        batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
        
        if self.queue and timestamp == self.queue[-1]['timestamp']:
            # modify content of the element in the queue
            self.queue[-1]['OHLCs'] = OHLCs

            # update data in Cassandra table "stocks_history"
            dt = datetime.fromtimestamp(timestamp)
            update = self.__UpdateCassandraStock()
            
            for symbol in OHLCs.keys():
                # Convert dict to json so that it can be insert into Cassandra table
                OHLC_json = json.dumps(OHLCs[symbol])
                batch.add(update, (OHLC_json, symbol, self.interval_type, dt))
                # Update H and L
                self.H[symbol] = max(OHLCs[symbol]['high'], self.H[symbol])
                self.L[symbol] = min(OHLCs[symbol]['low'], self.L[symbol])
                
        elif self.queue and timestamp - self.queue[-1]['timestamp'] < 10 * self.interval:
            # the timestamp that is less than or equal to the current timestamp, in a certain range
            # supplement the intermediate missing data 
            latest = self.queue[-1]['timestamp']
            insert = self.__InsertCassandraStock()
    
            for t in range((timestamp - latest)//self.interval):
                ts = latest + (t+1) * self.interval
                self.queue.append({'OHLCs':OHLCs, 'timestamp':ts})
                dt = datetime.fromtimestamp(ts)
                for symbol in OHLCs.keys():
                    OHLC_json = json.dumps(OHLCs[symbol])
                    batch.add(insert, (OHLC_json, symbol, self.interval_type, dt))
                    if t < 1:
                        # Because they are all same values, so update H and L only once
                        self.H[symbol] = max(OHLCs[symbol]['high'], self.H[symbol])
                        self.L[symbol] = min(OHLCs[symbol]['low'], self.L[symbol])
                    
        else:
            self.queue.append({'OHLCs':OHLCs, 'timestamp':timestamp})
            dt = datetime.fromtimestamp(timestamp)
            insert = self.__InsertCassandraStock()
            for symbol in OHLCs.keys():
                OHLC_json  = json.dumps(OHLCs[symbol])
                batch.add(insert, (OHLC_json, symbol, self.interval_type, dt))
                # Update H and L
                self.H[symbol] = max(OHLCs[symbol]['high'], self.H[symbol])
                self.L[symbol] = min(OHLCs[symbol]['low'], self.L[symbol])
                    

        while stack:
            self.queue.append(stack.pop())

        # Pop the exceeded data out if the queue is full
        # Delete the data being pop out from Cassandra table
        delete = self.__DeleteCassandraStock()
        while len(self.queue) > self.length:
            del_data = self.queue.popleft()
            dt = datetime.fromtimestamp(del_data['timestamp'])
            for symbol in del_data['OHLCs'].keys():
                batch.add(delete, (symbol, self.interval_type, dt))

        self.c_session.execute(batch)
        batch.clear()

    def extract(self):
        OHLCs = {}
        
        if len(self.queue) >= 60:
            O = self.queue[-60]['OHLCs']
        else:
            O = self.queue[0]['OHLCs']

        C = self.queue[-1]['OHLCs']
    
        for symbol in O.keys():
            OHLCs[symbol] = {'close':{'price':C[symbol]['close']['price'], 'time':C[symbol]['close']['time']}, 
                        'open':{'price':O[symbol]['open']['price'], 'time':O[symbol]['open']['time']}, 
                        'high':self.H[symbol], 
                        'low':self.L[symbol], 
                        'symbol':symbol, 
                        'volume':C[symbol]['volume']}
        
            self.H[symbol] = 0
            self.L[symbol] = float('inf')
        return OHLCs

### Repeated program runner with accurate execution interval
class RepeatedTimer:
    # Repeat function every interval seconds, stop after a given number of seconds
    def __init__(self, interval, stop_after, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.start = time.time()
        self.stop_at = self.start + stop_after
        self.event = Event()
        self.thread = Thread(target=self._target)
        self.thread.start()

    def _target(self):
        while not self.event.wait(self._time):
            if time.time()  > self.stop_at:
                break
            self.function(*self.args, **self.kwargs)
            

    @property
    def _time(self):
        return self.interval - ((time.time() - self.start) % self.interval)

    def stop(self):
        self.event.set()
        self.thread.join()
            
