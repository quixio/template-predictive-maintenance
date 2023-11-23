import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { Alert, EventData } from 'src/app/models';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent implements OnInit {
  dataSource: Alert[] = [];
  @Input() reset$: Observable<any>;
  @Input() eventIds: string[];
  @Input() disableEventId: string;
  @Input() disableParameterId: string;
  @Input() set data(data: EventData) {
    if (!data) return;
    const value: Alert = JSON.parse(data.value);
    if (!this.eventIds.includes(value.status!)) return;
    if (value.status === this.disableEventId || value.parameter_name === this.disableParameterId) {
      this.dataSource.forEach((alert) => {
        if (value.parameter_name === alert.parameter_name) alert.disabled = true
      });
    }
    this.dataSource = [value, ...this.dataSource].slice(0, 19);
  }

  ngOnInit(): void {
    this.reset$.subscribe(() => this.dataSource = []);
  }
}
