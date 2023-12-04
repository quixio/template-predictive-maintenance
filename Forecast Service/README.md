# Forecast Service

[This project](https://github.com/quixio/template-predictive-maintenance/tree/develop/Forecast%20Service) generates
a forecast for the temperature data received from the input topic.

To make it simple but still interesting, the forecast is generated using a quadratic function.

## How to run

Create a [Quix](https://portal.platform.quix.ai/self-sign-up?xlink=github) account or log-in and clone this template.

## Environment variables

The application uses the following environment variables:

- **input**: This is the input topic to read data from
- **output**: This is the output topic to write data to
- **parameter_name**: The name of the parameter to forecast
- **debug**: If set to true, some debug information will be printed to the console
- **window_value**: The size of the window to use for the forecast. The application uses this value to calculate the
  number of observations or the time period to use for the forecast (ie, if the window type is 2, the 
  window_value is 10 and the forecast_unit is 'min', the application will use the last 10 minutes to generate the forecast)
- **window_type**: The unit of the window to use for the forecast. 1 for "Number of Observations", 2 for "Time Period"
- **forecast_length**: The length of the forecast
- **forecast_unit**: The unit of the forecast length ('S' for seconds, 'min' for minutes). [More info](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases)

## Contribute

Submit forked projects to the [Quix GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept
will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available
in [our GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.


