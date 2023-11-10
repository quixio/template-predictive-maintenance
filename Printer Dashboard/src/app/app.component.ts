import { Component, OnInit } from '@angular/core';
import { DataService } from './services/data.service';
import { ConnectionStatus, QuixService } from './services/quix.service';
import { MediaObserver } from '@angular/flex-layout';
import { FormControl } from '@angular/forms';
import { EventData } from './models/eventData';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  printerControl = new FormControl();
  printers: any[] = [];
  workspaceId: string;
  deploymentId: string;
  ungatedToken: string;

  constructor(private quixService: QuixService, private dataService: DataService, public media: MediaObserver) {}

  ngOnInit(): void {
    this.workspaceId = this.quixService.workspaceId;
    this.ungatedToken = this.quixService.ungatedToken;
    this.deploymentId = '';

    this.quixService.eventDataReceived.subscribe((event: EventData) => {
      // TODO: Event received
    });

    this.quixService.readerConnStatusChanged$.subscribe((status) => {
      if (status !== ConnectionStatus.Connected) return;
      // TODO: Reader connection changes
    });

    this.printerControl.valueChanges.subscribe((printer: any) => {
      const topicId = this.quixService.workspaceId + '-' + this.quixService.offersTopic;
      if (this.dataService.printer) this.quixService.unsubscribeFromEvent(topicId, this.dataService.printer.printerId, "offer");
      this.quixService.subscribeToEvent(topicId, printer.printerId, "offer");
      this.dataService.printer = printer;
    });
  }

  toggleSidenav(isOpen: boolean): void {
    this.dataService.isSidenavOpen$.next(isOpen);
  }
}
