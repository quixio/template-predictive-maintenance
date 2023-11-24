# Alert Service

[This service](https://github.com/quixio/template-predictive-maintenance/tree/develop/Alert%20Service) sends
alerts to an output topic when the temperature is under or over the threshold.

It receives data from 2 topics (3d printer data and forecast) and triggers an alert (to output topic alerts)
if the temperature is under or over the threshold.

## How to run

Create a [Quix](https://portal.platform.quix.ai/self-sign-up?xlink=github) account or log-in and clone this template.

## Environment variables

The following environment variables are required to run the service:

- **alerts**: The topic where the alerts will be sent to.
- **printer_data**: The topic where the printer data will be received from.
- **forecast_data**: The topic where the forecast data will be received from.

## Contribute

Submit forked projects to the [Quix GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept
will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available
in [our GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
