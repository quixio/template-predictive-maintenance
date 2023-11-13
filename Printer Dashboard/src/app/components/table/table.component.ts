import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Data } from 'src/app/models/data';
import { EventData } from 'src/app/models/eventData';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent {
  dataSource: EventData[] = [];
  @Input() set data(data: EventData){
    if (!data) return;
    this.dataSource.push(data);
  }
}
