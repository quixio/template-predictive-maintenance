import { Component, OnInit, ViewChild } from '@angular/core';
import { ConnectionStatus, QuixService } from './services/quix.service';
import { MediaObserver } from '@angular/flex-layout';
import { FormControl } from '@angular/forms';
import { EventData } from './models/eventData';
import { ActiveStream } from './models/activeStream';
import { ActiveStreamAction } from './models/activeStreamAction';
import { ActiveStreamSubscription } from './models/activeStreamSubscription';
import { ParameterData } from './models/parameterData';
import { Observable, filter, interval, map, merge, tap, timer, withLatestFrom } from 'rxjs';
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
  activeStreamsStartTime: number[] = [];
  activeStreams$: Observable<ActiveStream[]>;
  printerData$: Observable<ParameterData>;
  forecastData$: Observable<ParameterData>;
  eventData$: Observable<EventData>;
  streamsMap = new Map<string, string>();
  forecastLimit: { min: number, max: number } = { min: 40, max: 60 }
  parameterIds: string[] = ['ambient_temperature', 'bed_temperature', 'hotend_temperature'];
  eventsIds: string[] = ['under-forecast', 'under-now', 'no-alert'];
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

    this.activeStreams$ = this.quixService.activeStreamsChanged$.pipe(
      map((streamSubscription: ActiveStreamSubscription) => {
        const { streams } = streamSubscription;
        if (!streams?.length) return [];
        return this.updateActiveSteams(streamSubscription).sort((a, b) => {
          return +a.metadata['start_time'] > +b.metadata['start_time'] ? -1 : 1
        })
      })
    );

    this.activeStreams$.subscribe((activeStreams) => {
      if (!this.streamsControl.value) this.streamsControl.setValue(activeStreams.at(0))
      this.activeStreams = activeStreams;
    });

    interval(1000).pipe(withLatestFrom(this.activeStreams$)).subscribe(([_, activeStreams]) => {
      this.activeStreamsStartTime = activeStreams.map((m) => {
        const timeToFailure: number = (4 * 60 + 35) * 60 * 1000;
        return (timeToFailure + +m.metadata['start_time'] / 1000000) - new Date().getTime()
      });
    });

    this.printerData$ = this.quixService.paramDataReceived$
      .pipe(filter((f) => f.topicName === this.quixService.printerDataTopic))
    this.forecastData$ = this.quixService.paramDataReceived$
      .pipe(filter((f) => f.topicName === this.quixService.forecastTopic));
    this.eventData$ = this.quixService.eventDataReceived$;

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
      this.subscribeToEvent(forecastAlertsTopicId, stream.streamId + '-alerts', this.eventsIds);
      this.forecastLimit = { min: 40, max: 60 };
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
  updateActiveSteams(streamSubscription: ActiveStreamSubscription): ActiveStream[] {
    const { streams, action } = streamSubscription;
    const currentStreams = this.activeStreams.filter((stream) => !streams?.some((s) => s.streamId === stream.streamId));
    switch (action) {
      case ActiveStreamAction.AddUpdate:
        return [...currentStreams, ...(streams || [])];
      case ActiveStreamAction.Remove:
        return currentStreams;
      default:
        return this.activeStreams;
    }
  }

  /**
   * Converts the seconds into a readable format
   * @param timestamp noOfMilliseconds
   * @returns the time in a human readable string
   */
  forHumans(timestamp: number, levelsCount?: number) {
    timestamp = Math.abs(timestamp);

    const levels: any = [
      [Math.floor(timestamp / 31536000000), 'years'],
      [Math.floor((timestamp % 31536000000) / 86400000), 'days'],
      [Math.floor(((timestamp % 31536000000) % 86400000) / 3600000), 'hours'],
      [Math.floor((((timestamp % 31536000000) % 86400000) % 3600000) / 60000), 'min'],
      [Math.floor(((((timestamp % 31536000000) % 86400000) % 3600000) % 60000) / 1000), 'sec'],
      [Math.floor((((((timestamp % 31536000000) % 86400000) % 3600000) % 60000) % 1000) * 100) / 100, 'ms']
    ];
    let returnText = '';

    for (let i = 0, max = levels.length; i < max; i += 1) {
      if (levels[i][0] > 0) {
        returnText += ` ${levels[i][0]} ${levels[i][1]}`;
        if (levelsCount && i > levelsCount) break;
      }
    }
    return returnText.trim();
  }
}
