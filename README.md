# Stock-Trading-Helper
This project aims to develop a web application that is useful and convenient for people who want to do algorithmic trading. The features include a real-time stock chart with multiple adjustable options; a trading strategy setting function which allows user to arbitrarily compose several conditions to set multiple automated trading programs; a backtesting function that is used to examine the effectiveness of a strategy.

The conceptual figure of the design is shown below
![website appearance](https://github.com/Jefflin413/Stock-Trading-Helper/blob/master/prototype.png)

# Features
## Real-time Stock Chart
* Print Real-time data from multiple open sources in the time series format, currently available stocks are from NASDAQ.
* Time interval (Refreshing rate) can be set to second, minute, hour or day. The time scale as the chart's x-axis will be automatically changed to the corresponding scale.
* Chart style can be OHLC or candlestick.
* Historical data are supported starting from 20xx, users can choose any specific period of time they interest after this date and use it to do backtesting of strategies.
* Five types of indicators can be plot simultaneously on the chart while these indicators are available for users to define under the given framework. Now the indicators include exponential moving averages (EMAs),  Bollinger bands, stochastic oscillator, moving average convergence divergence (MACD) and on-balance-volume (OBV). More indicator type will be added in the future update

## Indicator Editor
* The place that users can edit and create their unique indicators
* The created indicators are linked to the selected stock symbol at the time when it was saved. Once an indicator instance is created, it can be used as an object in the strategy under the same stock symbol. 
* The followings are the descriptions and parameters in each technical indicator:
  1. EMA
      * Description:
          An exponential moving average (EMA) is a type of moving average (MA) that places a greater weight and significance on the most recent data points. The exponential moving average is also referred to as the exponentially weighted moving average.
      * Parameters: 
         * Scale: second, minute, hour, day
         * Range: the considered range of EMA, number of the selected scale, a positive integer
  2. Bollinger
      * Description:
          Bollinger Bands are envelopes plotted at a standard deviation level above and below a simple moving average of the price. Because the distance of the bands is based on standard deviation, they adjust to volatility swings in the underlying price. 
      * Parameters:
         * Scale: second, minute, hour, day
         * Period: number of the selected scale in smoothing period, a positive integer
         * N_STD: number of standard deviation, a positive integer
  3. Stochastic
      * Description:
          A stochastic oscillator is a momentum indicator comparing a particular closing price of a security to a range of its prices over a certain period of time. The sensitivity of the oscillator to market movements is reducible by adjusting that time period or by taking a moving average of the result.
      * Parameters:
         * Scale: second, minute, hour, day
         * N_PTS: number of previous trading session, a positive integer
         * EMA: if True, use EMA in calculation, else use SMA, True or False
         * Range_K: the range of EMA of %K, number of the selected scale, a positive integer 
         * Range_D: the range of EMA of %D, number of the selected scale, a positive integer
  4. MACD
      * Description:
          Moving Average Convergence Divergence (MACD) is a trend-following momentum indicator that shows the relationship between two moving averages of a security's price. 
      * Parameters:
         * Scale: second, minute, hour, day
         * Range_EMA1: the smaller one in Range_EMA1 and Range_EMA2 will be fast EMA, and the other one will be slow EMA, a positive integer 
         * Range_EMA2: EMA type object, the scale attribute must be the same as EMA_slow, a positive integer
         * Range: the range of EMA of difference between fast EMA and slow EMA, a positive integer        
  5. OBV
      * Description:
          On-balance volume provides a running total of an asset's trading volume and indicates whether this volume is flowing in or out of a given security or currency pair. The OBV is a cumulative total of volume (positive and negative). 
      * Parameters:
         * Start: the starting day, a string in the format "yyyy/mm/dd"

## Strategy and Backtesting
The Strategy is an automated trading function that can help users make transactions in an accurate, quick and efficient way. Strategies are actions triggered by a combination of several conditions on technical indicators, stock market price and other criteria. It performs the pre-defined action after the given condition is satisfied. For example, we first create two indicators, EMA200 and EMA50, which indicate the EMA of the latest 200 days and 50 days respectively. Then we can make a strategy that will send a selling order to the market when EMA200 and EMA50 intersect with each other. 

A strategy is formed by actions and conditions composed of logic operations. The first step of creating a strategy is to add an action with a condition/conditions. A condition should be an equation or an inequality following the below format:
* \[Object\] \[Operation Symbol\] \[Object\] \[Optional Operation\]
* Object: can be a numerical value, the stock price, profit, loss, position, or a technical indicator that is related to the current selected stock symbol.
* Operation Symbol: +, -, *, /, >, <, =, >=, <=, !=. An Object is required after an Operation Symbol 
* Optional Operation: additional Operations follow the pattern: \[Operation Symbol\] \[Object\]

After the first condition is created, you can add new conditions and choose a relation from AND and OR to decide the logical relationship between conditions, parentheses are also available to perform a better logic. The second step is to set a trading action triggered when the conditions being satisfied, the available actions are
* BUY(Quantity) 
* SELL(Quantity) 
* FLAT

The following examples a possible strategy format: <br>
Strategy_1: { <br>
\[ACTION_1\]: \[CONDITION_1\] AND (\[CONDITION_2\] OR \[CONDITION_3\]), <br>
\[ACTION_2\]: \[CONDITION_4\]  <br>
} <br>

Backtesting function is used to examine the effectiveness of a strategy. After a strategy is generated, before it is activated on the real-time market data, user can choose a specific period of time and the strategy will be implemented on the historical data in that period to see the result (profit and loss, position and revenue). To use this function the user just need to determine the start date and the end date.

# System Architecture
The system architecture is shown below
![system architecture](https://github.com/Jefflin413/Stock-Trading-Helper/blob/master/system%20architecture.png)
