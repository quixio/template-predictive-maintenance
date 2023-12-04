#!/bin/sh
echo "${bearer_token}" > /usr/share/nginx/html/bearer_token
echo "${Quix__Workspace__Id}" > /usr/share/nginx/html/workspace_id
echo "${Quix__Portal__Api}" > /usr/share/nginx/html/portal_api
echo "${printer_data_topic}" > /usr/share/nginx/html/printer_data_topic
echo "${forecast_topic}" > /usr/share/nginx/html/forecast_topic
echo "${alerts_topic}" > /usr/share/nginx/html/alerts_topic
nginx -g "daemon off;"
