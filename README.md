# Predictive maintenance template

A Quix template providing examples of how to build a predictive maintenance system

- [See the deployed project](https://portal.platform.quix.io/pipeline?workspace=demo-predictivemaintenance-dev&token=pat-1bb3d78414e049a09ab6a9a6a9f9f7eb)
- [See the project running in Quix](https://dash-demo-predictivemaintenance-dev.deployments.quix.io/)

## Technologies used

Some of the technologies used by this template project are listed here.

**Infrastructure:**

- [Quix](https://quix.io/)
- [Docker](https://www.docker.com/)
- [Kubernetes](https://kubernetes.io/)
- [InfluxDB](https://www.influxdata.com/products/influxdb/)

**Backend:**

- [Aiven for Apache Kafka](https://aiven.io/kafka)
- [Quix Streams](https://github.com/quixio/quix-streams)
- [Flask](https://flask.palletsprojects.com/en/2.3.x/#)
- [pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)

**Frontend:**

- [Angular](https://angular.io/)
- [Typescript](https://www.typescriptlang.org/)
- [Microsoft SignalR](https://learn.microsoft.com/en-us/aspnet/signalr/)

## The project pipeline

The main services in the pipeline are:

1. _Data Generator_: Generates temperature data simulating one or more 3D printer.
2. _3D Printer Down Sampling_: Down samples the data to 1 minute intervals.
3. _Forecast Service_: Creates a forecast for the next 8 hours for each printer.
4. _Alert Service_: Detects when temperature is outside of normal parameters and sends alerts to the frontend.
5. _Printers Dashboard_: Displays the data and alerts for each printer.
6. _InfluxDB 3.0 Alerts_: Stores the alerts in InfluxDB 3.0.
7. _InfluxDB 3.0 Raw Data_: Stores the data in InfluxDB 3.0.

## Prerequisites

To get started make sure you have a [free Quix account](https://portal.platform.quix.io/self-sign-up).

If you are new to Quix it is worth reviewing the [recent changes page](https://quix.io/docs/platform/changes.html),
as that contains very useful information about the significant recent changes, and also has a number of useful videos you can watch to gain familiarity with Quix.

### Git provider

You also need to have a Git account. This could be GitHub, Bitbucket, GitLab, or any other Git provider you are familar with, and that supports SSH keys. The simplest option is to create a free [GitHub account](https://github.com).

While this project uses an external Git account, Quix can also provide a Quix-hosted Git solution using Gitea for your own projects. You can watch a video on [how to create a project using Quix-hosted Git](https://www.loom.com/share/b4488be244834333aec56e1a35faf4db?sid=a9aa124a-a2b0-45f1-a756-11b4395d0efc).

## Tutorial

Check out our [tutorials](https://quix.io/docs/platform/tutorials/).
A specific tutorial for this template is coming soon.

## Getting help

If you need any assistance while following the tutorial, we're here to help in the [Quix forum](https://forum.quix.io/).
