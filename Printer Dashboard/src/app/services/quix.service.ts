import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { HubConnection, HubConnectionBuilder, IHttpConnectionOptions } from '@microsoft/signalr';
import { BehaviorSubject, Observable, Subject, combineLatest } from 'rxjs';
import { environment } from 'src/environments/environment';
import { EventData } from '../models/eventData';
import { ParameterData } from '../models/parameterData';
import { Data } from '../models/data';
import { ActiveStream } from '../models/activeStream';
import { ActiveStreamAction } from '../models/activeStreamAction';
import { ActiveStreamSubscription } from '../models/activeStreamSubscription';


export enum ConnectionStatus {
  Connected = 'Connected',
  Reconnecting = 'Reconnecting',
  Offline = 'Offline'
}

@Injectable({
  providedIn: 'root'
})
export class QuixService {
  // this is the token that will authenticate the user into the ungated product experience.
  // ungated means no password or login is needed.
  // the token is locked down to the max and everything is read only.
  public ungatedToken: string = 'pat-b88b3caf912641a1b0fa8b47b262868b';

  /*~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-*/
  /*WORKING LOCALLY? UPDATE THESE!*/
  // private workingLocally = false; // set to true if working locally
  // private token: string = ''; // Create a token in the Tokens menu and paste it here
  // public workspaceId: string = ''; // Look in the URL for the Quix Portal your workspace ID is after 'workspace='
  // public printerDataTopic: string = ''; // get topic name from the Topics page in the Quix portal
  // public forecastTopic: string = ''; // get topic name from the Topics page in the Quix portal
  // public forecastAlertsTopic: string = ''; // get topic name from the Topics page in the Quix portal

  private workingLocally = true; // set to true if working locally
  private token: string = 'pat-715aa7855be34da9a916e53d3825c5bd'
  public workspaceId: string = 'demo-predictivemaintenance-dev'; // Look in the URL for the Quix Portal your workspace ID is after 'workspace='
  public printerDataTopic: string = '3d-printer-data'; // get topic name from the Topics page in the Quix portal
  public forecastTopic: string = 'forecast'; // get topic name from the Topics page in the Quix portal
  public forecastAlertsTopic: string = 'alerts'; // get topic name from the Topics page in the Quix portal
  /* optional */
  /*~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-*/

  private subdomain = 'platform'; // leave as 'platform'
  readonly server = ''; // leave blank

  private readerReconnectAttempts: number = 0;
  private writerReconnectAttempts: number = 0;
  private reconnectInterval: number = 5000;
  private hasReaderHubListeners: boolean = false;

  private readerHubConnection: HubConnection;
  private writerHubConnection: HubConnection;
  public readerConnStatusChanged$ = new BehaviorSubject<ConnectionStatus>(ConnectionStatus.Offline);
  public writerConnStatusChanged$ = new BehaviorSubject<ConnectionStatus>(ConnectionStatus.Offline);

  public paramDataReceived$ = new Subject<ParameterData>();
  public eventDataReceived$ = new Subject<EventData>();
  public activeStreamsChanged$ = new Subject<ActiveStreamSubscription>();

  private domainRegex = new RegExp("^https:\\/\\/portal-api\\.([a-zA-Z]+)\\.quix\\.io");

  constructor(private httpClient: HttpClient) {

    if (this.workingLocally || location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      this.setUpHubConnections(this.workspaceId);
    }
    else {
      const headers = new HttpHeaders().set('Content-Type', 'text/plain; charset=utf-8');
      let bearerToken$ = this.httpClient.get(this.server + 'bearer_token', { headers, responseType: 'text' });
      let workspaceId$ = this.httpClient.get(this.server + 'workspace_id', { headers, responseType: 'text' });
      let portalApi$ = this.httpClient.get(this.server + 'portal_api', { headers, responseType: 'text' })
      let printerData$ = this.httpClient.get(this.server + 'printer_data_topic', { headers, responseType: 'text' });
      let forecast$ = this.httpClient.get(this.server + 'forecast_topic', { headers, responseType: 'text' });
      let forecastAlerts$ = this.httpClient.get(this.server + 'alerts_topic', { headers, responseType: 'text' });

      combineLatest([
        bearerToken$,
        workspaceId$,
        portalApi$,
        printerData$,
        forecast$,
        forecastAlerts$
      ]).subscribe(([bearerToken, workspaceId, portalApi, printerData, forecast, forecastAlerts]) => {
        this.token = bearerToken.replace('\n', '');
        this.workspaceId = workspaceId.replace('\n', '');
        this.printerDataTopic = printerData.replace('\n', '');
        this.forecastTopic = forecast.replace('\n', '');
        this.forecastAlertsTopic = forecastAlerts.replace('\n', '');

        console.log(this.token);
        console.log(this.workspaceId);
        console.log(this.printerDataTopic);
        console.log(this.forecastTopic);
        console.log(this.forecastAlertsTopic);

        // work out what domain the portal api is on:
        portalApi = portalApi.replace("\n", "");
        let matches = portalApi.match(this.domainRegex);
        if (matches) this.subdomain = matches[1];
        else this.subdomain = "platform"; // default to prod

        this.setUpHubConnections(this.workspaceId);
      });
    }
  }

  private setUpHubConnections(workspaceId: string): void {
    const options: IHttpConnectionOptions = {
      accessTokenFactory: () => this.token,
    };

    this.readerHubConnection = this.createHubConnection(`https://reader-${workspaceId}.${this.subdomain}.quix.io/hub`, options, true);
    this.startConnection(true, this.readerReconnectAttempts);

    this.writerHubConnection = this.createHubConnection(`https://writer-${workspaceId}.${this.subdomain}.quix.io/hub`, options, false);
    this.startConnection(false, this.writerReconnectAttempts);
  }

  /**
   * Creates a new hub connection.
   *
   * @param url The url of the SignalR connection.
   * @param options The options for the hub.
   * @param isReader Whether it's the ReaderHub or WriterHub.
   *
   * @returns The newly created hub connection.
   */
  private createHubConnection(url: string, options: IHttpConnectionOptions, isReader: boolean): HubConnection {
    const hubConnection = new HubConnectionBuilder()
      .withUrl(url, options)
      .build();

    const hubName = isReader ? 'Reader' : 'Writer';
    hubConnection.onclose((error) => {
      console.log(`Quix Service - ${hubName} | Connection closed. Reconnecting... `, error);
      this.tryReconnect(isReader, isReader ? this.readerReconnectAttempts : this.writerReconnectAttempts);
    })
    return hubConnection;
  }

  /**
   * Handles the initial logic of starting the hub connection. If it falls
   * over in this process then it will attempt to reconnect.
   *
   * @param isReader Whether it's the ReaderHub or WriterHub.
   * @param reconnectAttempts The number of attempts to reconnect.
   */
  private startConnection(isReader: boolean, reconnectAttempts: number): void {
    const hubConnection = isReader ? this.readerHubConnection : this.writerHubConnection;
    const subject = isReader ? this.readerConnStatusChanged$ : this.writerConnStatusChanged$;
    const hubName = isReader ? 'Reader' : 'Writer';

    if (!hubConnection || hubConnection.state === 'Disconnected') {

      hubConnection.start()
        .then(() => {
          console.log(`QuixService - ${hubName} | Connection established!`);
          reconnectAttempts = 0; // Reset reconnect attempts on successful connection
          subject.next(ConnectionStatus.Connected);

          // If it's reader hub connection then we create listeners for data
          if (isReader && !this.hasReaderHubListeners) {
            this.setupReaderHubListeners(hubConnection);
            this.hasReaderHubListeners = true;
          }
        })
        .catch(err => {
          console.error(`QuixService - ${hubName} | Error while starting connection!`, err);
          subject.next(ConnectionStatus.Reconnecting)
          this.tryReconnect(isReader, reconnectAttempts);
        });
    }
  }

  /**
   * Creates listeners on the ReaderHub connection for both parameters
   * and events so that we can detect when something changes. This can then
   * be emitted to any components listening.
   *
   * @param readerHubConnection The readerHubConnection we are listening to.
   */
  private setupReaderHubListeners(readerHubConnection: HubConnection): void {
    // Listen for active streams and emit
    readerHubConnection.on('ActiveStreamsChanged', (stream: ActiveStream, action?: ActiveStreamAction) => {
      this.activeStreamsChanged$.next({ streams: [stream], action });
    });

    // Listen for parameter data and emit
    readerHubConnection.on("ParameterDataReceived", (payload: ParameterData) => {
      this.paramDataReceived$.next(payload);
    });

    // Listen for event data and emit
    readerHubConnection.on("EventDataReceived", (payload: EventData) => {
      this.eventDataReceived$.next(payload);
    });
  }

  /**
   * Handles the reconnection for a hub connection. Will continiously
   * attempt to reconnect to the hub when the connection drops out. It does
   * so with a timer of 5 seconds to prevent a spam of requests and gives it a
   * chance to reconnect.
   *
   * @param isReader Whether it's the ReaderHub or WriterHub.
   * @param reconnectAttempts The number of attempts to reconnect.
   */
  private tryReconnect(isReader: boolean, reconnectAttempts: number) {
    const hubName = isReader ? 'Reader' : 'Writer';
    reconnectAttempts++;
    setTimeout(() => {
      console.log(`QuixService - ${hubName} | Attempting reconnection... (${reconnectAttempts})`);
      this.startConnection(isReader, reconnectAttempts)
    }, this.reconnectInterval);

  }

   /**
   * Subscribes to all the active streams on the message topic so
   * we can listen to changes.
   *
   * @param topic The topic being wrote to.
   */
   public subscribeToActiveStreams(topic: string): void {
    // console.log("QuixService subscribing to retrieve streams");
    this.readerHubConnection
      .invoke('SubscribeToActiveStreams', topic)
      .then((stream: ActiveStream, action?: ActiveStreamAction) => {
        if (!stream) return;
        if (!action) action = ActiveStreamAction.AddUpdate;
        const streamsArray = Array.isArray(stream) ? stream : [stream];
        this.activeStreamsChanged$.next({ streams: streamsArray, action });
      });
  }

  /**
   * Subscribes to a parameter on the ReaderHub connection so
   * we can listen to changes.
   *
   * @param topic The topic being wrote to.
   * @param streamId The id of the stream.
   * @param parameterId The parameter want to listen for changes.
   */
  public subscribeToParameter(topic: string, streamId: string, parameterId: string) {
    // console.log(`QuixService Reader | Subscribing to parameter - ${topic}, ${streamId}, ${parameterId}`);
    this.readerHubConnection.invoke("SubscribeToParameter", topic, streamId, parameterId);
  }

  /**
   * Subscribes to a event on the ReaderHub connection so
   * we can listen to changes.
   *
   * @param topic The topic being wrote to.
   * @param streamId The id of the stream.
   * @param eventId The event want to listen for changes.
   */
  public subscribeToEvent(topic: string, streamId: string, eventId: string) {
    // console.log(`QuixService Reader | Subscribing to event - ${topic}, ${streamId}, ${eventId}`);
    this.readerHubConnection.invoke("SubscribeToEvent", topic, streamId, eventId);
  }

  /**
   * Sends parameter data to Quix using the WriterHub connection.
   *
   * @param topic The name of the topic we are writing to.
   * @param streamId The id of the stream.
   * @param payload The payload of data we are sending.
   */
    public sendParameterData(topic: string, streamId: string, payload: Data): void {
      // console.log("QuixService Sending parameter data!", topic, streamId, payload);
      this.writerHubConnection.invoke("SendParameterData", topic, streamId, payload);
    }


  /**
   * Unsubscribe from all the active streams on the message topic.
   * so we no longer recieve changes.
   *
   * @param topic
   */
	public unsubscribeFromActiveStreams(topic: string): void {
		// console.log(`QuixService unsubscribing from retrieve channels`);
		this.readerHubConnection.invoke('UnsubscribeFromActiveStreams', topic);
	}

  /**
   * Unsubscribe from a parameter on the ReaderHub connection
   * so we no longer recieve changes.
   *
   * @param topic
   * @param streamId
   * @param parameterId
   */
  public unsubscribeFromParameter(topic: string, streamId: string, parameterId: string) {
    // console.log(`QuixService Reader | Unsubscribing from parameter - ${topic}, ${streamId}, ${parameterId}`);
    this.readerHubConnection.invoke("UnsubscribeFromParameter", topic, streamId, parameterId);
  }

  /**
   * Unsubscribe from a event on the ReaderHub connection
   * so we no longer recieve changes.
   *
   * @param topic
   * @param streamId
   * @param eventId
   */
  public unsubscribeFromEvent(topic: string, streamId: string, eventId: string) {
    // console.log(`QuixService Reader | Unsubscribing from event - ${topic}, ${streamId}, ${eventId}`);
    this.readerHubConnection.invoke("UnsubscribeFromEvent", topic, streamId, eventId);
  }

  /**
   * Uses the telemetry data api to retrieve persisted parameter
   * data for a specific criteria.
   *
   * @param payload The payload that we are querying with.
   * @returns The persisted parameter data.
   */
  public retrievePersistedParameterData(payload: any): Observable<ParameterData> {
    return this.httpClient.post<ParameterData>(
      `https://telemetry-query-${this.workspaceId}.${this.subdomain}.quix.io/parameters/data`,
      payload,
      {
        headers: { 'Authorization': 'bearer ' + this.token }
      }
    );
  }
}

