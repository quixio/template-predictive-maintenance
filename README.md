# template-predictive-maintenance

A Quix template providing examples of how to build a predictive maintenance system

* [See the deployed project](https://portal.platform.quix.io/pipeline?workspace=demo-predictivemaintenance-dev)
* [See the project running in Quix](https://dash-demo-predictivemaintenance-dev.deployments.quix.io/)

## Technologies used

Some of the technologies used by this template project are listed here.

**Infrastructure:** 

* [Quix](https://quix.io/)
* [Docker](https://www.docker.com/)
* [Kubernetes](https://kubernetes.io/)

**Backend:** 

* [Redpanda Cloud](https://redpanda.com/redpanda-cloud)
* [Quix Streams](https://github.com/quixio/quix-streams)
* [Flask](https://flask.palletsprojects.com/en/2.3.x/#)
* [pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)

**Frontend:**

* [Angular](https://angular.io/)
* [Typescript](https://www.typescriptlang.org/)
* [Microsoft SignalR](https://learn.microsoft.com/en-us/aspnet/signalr/)

## The project pipeline

The main services in the pipeline are:

1. *Data Generator*: Generates temperature data simulating one or more 3D printer.
2. *3D Printer Down Sampling*: Down samples the data to 1 minute intervals.
3. *Forecast Service*: Creates a forecast for the next 8 hours for each printer.
4. *Alert Service*: Detects when temperature is not under normal parameters and sends alerts to the frontend.
5. *Printers Dashboard*: Displays the data and alerts for each printer.
6. *InfluxDB 3.0 Alerts*: Stores the alerts in InfluxDB 3.0.
7. *InfluxDB 3.0 Raw Data*: Stores the data in InfluxDB 3.0.

## Prerequisites

To get started make sure you have a [free Quix account](https://portal.platform.quix.io/self-sign-up).

If you are new to Quix it is worth reviewing the [recent changes page](https://quix.io/docs/platform/changes.html), 
as that contains very useful information about the significant recent changes, and also has a number of useful videos you can watch to gain familiarity with Quix.

### Git provider

You also need to have a Git account. This could be GitHub, Bitbucket, GitLab, or any other Git provider you are familar with, and that supports SSH keys. The simplest option is to create a free [GitHub account](https://github.com).

While this project uses an external Git account, Quix can also provide a Quix-hosted Git solution using Gitea for your own projects. You can watch a video on [how to create a project using Quix-hosted Git](https://www.loom.com/share/b4488be244834333aec56e1a35faf4db?sid=a9aa124a-a2b0-45f1-a756-11b4395d0efc).

## Tutorial

Work through the [tutorial](https://quix.io/docs/platform/tutorials/).

## Getting help

If you need any assistance while following the tutorial, we're here to help in the [Quix forum](https://forum.quix.io/).
