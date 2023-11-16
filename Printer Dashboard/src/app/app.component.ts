import { Component, OnInit, ViewChild } from '@angular/core';
import { ConnectionStatus, QuixService } from './services/quix.service';
import { MediaObserver } from '@angular/flex-layout';
import { FormControl } from '@angular/forms';
import { EventData } from './models/eventData';
import { ActiveStream } from './models/activeStream';
import { ActiveStreamAction } from './models/activeStreamAction';
import { ActiveStreamSubscription } from './models/activeStreamSubscription';
import { ParameterData } from './models/parameterData';
import { Observable, filter, merge } from 'rxjs';
import { ChartComponent } from './components/chart/chart.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  @ViewChild(ChartComponent) chart: ChartComponent;
  streamsControl = new FormControl();
  printers: any[] = [];
  workspaceId: string;
  deploymentId: string;
  ungatedToken: string;
  activeStreams: ActiveStream[] = [];
  printerData$: Observable<ParameterData>;
  forecastData$: Observable<ParameterData>;
  resetForecast$: Observable<void>;
  eventData$: Observable<EventData>;
  streamsMap = new Map<string, string>();
  parameterIds: string[] = ['ambient_temperature', 'bed_temperature', 'hotend_temperature'];
  ranges: { [key: string]: { min: number, max: number } } = {
    'ambient_temperature': { min: 45, max: 55 },
    'bed_temperature': { min: 105, max: 115 },
    'hotend_temperature': { min: 245, max: 255 }
  };

  constructor(private quixService: QuixService, public media: MediaObserver) { }

  ngOnInit(): void {
    this.workspaceId = this.quixService.workspaceId;
    this.ungatedToken = this.quixService.ungatedToken;
    this.deploymentId = '';

    this.quixService.activeStreamsChanged$.subscribe((streamSubscription: ActiveStreamSubscription) => {
      const { streams } = streamSubscription;
      if (!streams?.length) return;
      this.setActiveSteams(streamSubscription)
      if (!this.streamsControl.value) this.streamsControl.setValue(streams.at(0))
    });

    this.printerData$ = this.quixService.paramDataReceived$
      .pipe(filter((f) => f.topicName === this.quixService.printerDataTopic))
    this.forecastData$ = this.quixService.paramDataReceived$
      .pipe(filter((f) => f.topicName === this.quixService.forecastTopic));
    this.eventData$ = this.quixService.eventDataReceived$;

    this.resetForecast$ = merge(this.forecastData$, this.streamsControl.valueChanges)

    this.quixService.readerConnStatusChanged$.subscribe((status) => {
      if (status !== ConnectionStatus.Connected) return;
      this.quixService.subscribeToActiveStreams(this.quixService.printerDataTopic);
    });


    this.streamsControl.valueChanges.subscribe((stream: ActiveStream) => {
      const printerDataTopicId = this.quixService.workspaceId + '-' + this.quixService.printerDataTopic;
      const forecastTopicId = this.quixService.workspaceId + '-' + this.quixService.forecastTopic;
      const forecastAlertsTopicId = this.quixService.workspaceId + '-' + this.quixService.forecastAlertsTopic;
      this.subscribeToParameter(printerDataTopicId, stream.streamId, this.parameterIds);
      this.subscribeToParameter(forecastTopicId, stream.streamId + '-forecast', ['forecast_fluctuated_ambient_temperature']);
      this.subscribeToEvent(forecastAlertsTopicId, stream.streamId + '-alerts', ['under-fcast', 'under-now', 'no-alert']);
    });
  }

  subscribeToParameter(topicId: string, streamId: string, parameterIds: string[]): void {
    const previousStream = this.streamsMap.get(topicId);
    parameterIds.forEach(id => {
      if (previousStream) this.quixService.unsubscribeFromParameter(topicId, previousStream, id);
      this.quixService.subscribeToParameter(topicId, streamId, id)
    });
    this.streamsMap.set(topicId, streamId);
  }

  subscribeToEvent(topicId: string, streamId: string, eventIds: string[]): void {
    const previousStream = this.streamsMap.get(topicId);
    eventIds.forEach(id => {
      if (previousStream) this.quixService.unsubscribeFromEvent(topicId, previousStream, id);
      this.quixService.subscribeToEvent(topicId, streamId, id)
    });
    this.streamsMap.set(topicId, streamId);
  }

  /**
   * Handles when a new stream is added or removed.
   *
   * @param action The action we are performing.
   * @param streams The data within the stream.
   */
  private setActiveSteams(streamSubscription: ActiveStreamSubscription): void {
    const { streams, action } = streamSubscription;
    switch (action) {
      case ActiveStreamAction.AddUpdate:
        const newStreams = streams?.filter((stream) => !this.activeStreams.some((s) => s.streamId === stream.streamId)) || [];
        this.activeStreams.push(...newStreams);
        break;
      case ActiveStreamAction.Remove:
        this.activeStreams = this.activeStreams.filter((stream) => streams?.some((s) => s.streamId === stream.streamId));
        break;
      default: break;
    }
  }
}
