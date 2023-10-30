import { Component, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import { USERS } from './constants/users';
import { User } from './models/user';
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
  users: User[] = USERS;
  userControl = new FormControl();
  workspaceId: string;
  deploymentId: string;
  ungatedToken: string;

  constructor(private quixService: QuixService, private dataService: DataService, public media: MediaObserver) {}

  ngOnInit(): void {
    this.workspaceId = this.quixService.workspaceId;
    this.ungatedToken = this.quixService.ungatedToken;
    this.deploymentId = environment.DEPLOYMENT_ID || '';

    this.quixService.eventDataReceived.subscribe((event: EventData) => {
      this.dataService.openDialog(event)
    });

    this.quixService.readerConnStatusChanged$.subscribe((status) => {
      if (status !== ConnectionStatus.Connected) return;
      this.userControl.setValue(this.dataService.user || USERS[0])
    });

    this.userControl.valueChanges.subscribe((user: User) => {
      const topicId = this.quixService.workspaceId + '-' + this.quixService.offersTopic;
      if (this.dataService.user) this.quixService.unsubscribeFromEvent(topicId, this.dataService.user.userId, "offer");
      this.quixService.subscribeToEvent(topicId, user.userId, "offer");
      this.dataService.user = user;
    });
  }

  toggleSidenav(isOpen: boolean): void {
    this.dataService.isSidenavOpen$.next(isOpen);
  }
}
