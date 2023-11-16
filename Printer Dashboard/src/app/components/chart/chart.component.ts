import { Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { Chart, PointElement, ChartConfiguration, ChartDataset, ChartOptions, Legend, LineController, LineElement, LinearScale, Tooltip, ScaleChartOptions, ScaleOptionsByType } from 'chart.js';
import ChartStreaming, { RealTimeScale } from 'chartjs-plugin-streaming';
import 'chartjs-adapter-luxon';
import { Observable } from 'rxjs';
import annotationPlugin from 'chartjs-plugin-annotation';
import { ParameterData } from 'src/app/models/parameterData';
import { EventData } from 'src/app/models/eventData';
import { Alert } from 'src/app/models/alert';

@Component({
  selector: 'app-chart',
  templateUrl: './chart.component.html',
  styleUrls: ['./chart.component.scss']
})
export class ChartComponent implements OnInit {
  @ViewChild('canvas', { static: true }) canvas: ElementRef<HTMLCanvasElement>;
  chart: Chart;
  options: ChartOptions = {
    interaction: {
      mode: 'nearest',
      intersect: false
    },
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        type: 'realtime',
        realtime: {
          refresh: 500
        }
      },
      y: {
        type: 'linear',
        ticks: {
          stepSize: 5
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
        align: 'start',
        labels: {
          filter: (item) => item.text !== 'Alert',
          usePointStyle: true,
          boxHeight: 7,
          padding: 15,
          color: '#000',
          font: {
            weight: 'bold',
            size: 12
          }
        }
      },
      annotation: {
        annotations: {}
      }
    }
  };
  parameterDataset: ChartDataset<'line'> = {
    data: [],
    pointHoverBorderWidth: 0,
    pointRadius: 0,
    backgroundColor: '#00ff00',
    borderColor: '#0088ff',
    pointBackgroundColor: '#0088ff',
  }
  eventDataset: ChartDataset<'line'> = {
    data: [],
    label: 'Alert',
    order: 1,
    showLine: false,
    pointHoverBorderWidth: 0,
    pointRadius: 5,
    pointBackgroundColor: '#0088ff',
  }
  configuration: ChartConfiguration = {
    type: 'line',
    data: { datasets: [this.parameterDataset, this.eventDataset] },
    options: this.options
  }
  private _currentDelay: number;
  private _parameterId: string;
  private _eventId: string;
  private _offset: number = 5;
  private _min: number = Infinity;
  private _max: number = -Infinity;
  private _limit: { min: number, max: number }
  @Input() reset$: Observable<void>;
  @Input() set parameterId(parameterId: string) {
    this.parameterDataset.label = parameterId;
    this._parameterId = parameterId;
  }
  @Input() set eventId(eventId: string) {
    this._eventId = eventId;
  }
  @Input() set color(color: string) {
    this.parameterDataset.borderColor = color;
    this.parameterDataset.pointBackgroundColor = color;
    this.eventDataset.pointBackgroundColor = color;
  }
  @Input() set label(label: string) {
    this.parameterDataset.label = label;
  }
  @Input() set range(range: { min: number, max: number }) {
    (this.options as any).plugins.annotation.annotations['range'] = {
      type: 'box',
      yMin: range.min,
      yMax: range.max,
      backgroundColor: '#FFFF000f',
      borderWidth: 0
    };
    (this.options as any).scales['y'].min = range.min - this._offset;
    (this.options as any).scales['y'].max = range.max + this._offset;
  }
  @Input() set limit(limit: { min: number, max: number }) {
    if (!limit) return;
    (this.options as any).scales['y'].min = limit.min;
    (this.options as any).scales['y'].max = limit.max;
    this._limit = limit;
  }
  @Input() set duration(duration: number) {
    (this.options as any).scales['x'].realtime['duration'] = duration;
  }
  @Input() set delay(delay: number) {
    (this.options as any).scales['x'].realtime['delay'] = delay;
  }
  @Input() set hiddenAxe(key: 'x' | 'y') {
    (this.options as any).scales[key].ticks.display = false;
  }
  @Input() set parameterData(data: ParameterData) {
    if (!data) return;

    // Add points to the chart
    const values = data.numericValues![this._parameterId];
    data.timestamps?.forEach((timestamp, i) => {
      if (values[i] < this._min) this._min = values[i];
      if (values[i] > this._max) this._max = values[i];
      this.parameterDataset.data.push({ x: timestamp / 1000000, y: values[i] });
    });

    // Emit limit if exceed ranges
    const scale = (this.options as any).scales['y'];
    if (!this._limit && (this._min < scale.min || this._max > scale.max)) {
      if (this._min < scale.min) scale.min = Math.floor(this._min - this._offset);
      if (this._max > scale.max) scale.max = Math.floor(this._max + this._offset);
      this.limitChange.emit({ min: scale.min, max: scale.max });
    }

    // Update delay
    const lastTimestamp: number = data.timestamps[data.timestamps.length - 1];
    this.updateDelay(lastTimestamp);

    this.chart?.update();
  }
  @Input() set eventData(data: EventData) {
    if (!data) return;

    // Add points to the chart
    const value: Alert = JSON.parse(data.value);
    if (value.status === this._eventId) {
      this.eventDataset.data.push({ x: value.alert_timestamp! / 1000000, y: value.alert_temperature! });
      this.chart?.update();
    }
    if (value.status === "no-alert") this.eventDataset.data = [];
  }
  @Output() limitChange = new EventEmitter<{ min: number, max: number }>();

  constructor() {
    Chart.register(
      LinearScale,
      LineController,
      PointElement,
      LineElement,
      RealTimeScale,
      Legend,
      Tooltip,
      ChartStreaming,
      annotationPlugin,
    );
  }

  ngOnInit(): void {
    const ctx = this.canvas.nativeElement.getContext('2d');
    this.chart = new Chart(ctx!, this.configuration);
    this.reset$.subscribe(() => this.reset());
  }

  updateDelay(timestamp: number): void {
    const delay = Date.now() - timestamp / 1000000;
    const offset = 1000;
    if (!this._currentDelay || this._currentDelay - delay > offset || this._currentDelay - delay < -offset) {
      (this.options!.scales!['x'] as any).realtime.delay = delay + offset;
      this._currentDelay = delay;
    }
  }

  reset() {
    this.parameterDataset.data = [];
  }
}
