import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Alert } from 'src/app/models/alert';
import { Data } from 'src/app/models/data';
import { EventData } from 'src/app/models/eventData';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent {
  dataSource: Alert[] = [];
  @Input() eventIds: string[];
  @Input() set data(data: EventData){
    if (!data) return;
    const value: Alert = JSON.parse(data.value);
    console.log(value)
    if (this.eventIds.includes(value.status!)) this.dataSource = [value, ...this.dataSource].slice(0, 9);
    if (value.status === "no-alert") this.dataSource.forEach((alert) => alert.disabled = true);
  }
}
