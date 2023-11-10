import { Component, OnInit } from '@angular/core';
import { DataService } from './services/data.service';
import { ConnectionStatus, QuixService } from './services/quix.service';
import { MediaObserver } from '@angular/flex-layout';
import { FormControl } from '@angular/forms';
import { EventData } from './models/eventData';
import { ActiveStream } from './models/activeStream';
import { ActiveStreamAction } from './models/activeStreamAction';
import { ActiveStreamSubscription } from './models/activeStreamSubscription';
import { ParameterData } from './models/parameterData';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  streamsControl = new FormControl();
  printers: any[] = [];
  workspaceId: string;
  deploymentId: string;
  ungatedToken: string;
  activeStreams: ActiveStream[] = [];

  constructor(private quixService: QuixService, private dataService: DataService, public media: MediaObserver) { }

  ngOnInit(): void {
    this.workspaceId = this.quixService.workspaceId;
    this.ungatedToken = this.quixService.ungatedToken;
    this.deploymentId = '';

    this.quixService.activeStreamsChanged$.subscribe((streamSubscription: ActiveStreamSubscription) => {
      const { streams, action } = streamSubscription;
      this.setActiveSteams(streamSubscription)
      if (!this.streamsControl.value) this.streamsControl.setValue(streams?.at(0))
    });

    this.quixService.paramDataReceived$.subscribe((parameter: ParameterData) => {
      // TODO: Parameter received
    });

    this.quixService.eventDataReceived$.subscribe((event: EventData) => {
      // TODO: Event received
    });

    this.quixService.readerConnStatusChanged$.subscribe((status) => {
      if (status !== ConnectionStatus.Connected) return;
      this.quixService.subscribeToActiveStreams(this.quixService.printerDataTopic);
    });


    this.streamsControl.valueChanges.subscribe((stream: ActiveStream) => {
      const forecastTopicId = this.quixService.workspaceId + '-' + this.quixService.forecastTopic;
      const forecastAlertsTopicId = this.quixService.workspaceId + '-' + this.quixService.forecastAlertsTopic;
      if (this.streamsControl.value) this.quixService.unsubscribeFromEvent(forecastTopicId, this.dataService.printer.printerId, "offer");
      this.quixService.subscribeToParameter(forecastTopicId, stream.streamId, "*");
      this.quixService.subscribeToEvent(forecastAlertsTopicId, stream.streamId, "*");
    });
  }

  toggleSidenav(isOpen: boolean): void {
    this.dataService.isSidenavOpen$.next(isOpen);
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
