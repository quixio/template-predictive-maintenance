import { Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { Chart, PointElement, ChartConfiguration, ChartDataset, ChartOptions, Legend, LineController, LineElement, LinearScale, Tooltip, ScaleChartOptions, ScaleOptionsByType, Point } from 'chart.js';
import ChartStreaming, { RealTimeScale } from 'chartjs-plugin-streaming';
import 'chartjs-adapter-luxon';
import { DateTime } from 'luxon';
import { Observable } from 'rxjs';
import annotationPlugin from 'chartjs-plugin-annotation';
import { Alert, EventData, ParameterData } from 'src/app/models';
import { TooltipItem } from 'chart.js';

@Component({
  selector: 'app-chart',
  templateUrl: './chart.component.html',
  styleUrls: ['./chart.component.scss']
})
export class ChartComponent implements OnInit {
  @ViewChild('canvas', { static: true }) canvas: ElementRef<HTMLCanvasElement>;
  alertImage = new Image(16, 16);
  noAlertImage = new Image(18, 18);
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
        },
        time: {
          displayFormats: {
            hour: 'H:mm',
          }
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
          filter: (item) => item.text !== 'Event',
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
      tooltip: {
        usePointStyle: true,
        callbacks: {
          title: (context) => {
            const d = new Date((context[0].raw as Point).x);
            const luxonDate = DateTime.fromJSDate(d);
            return luxonDate.toFormat('H:mm:ss');
          },
          label: (context) => {
            const tooltipItems: TooltipItem<any>[] = context.chart.tooltip?.dataPoints || [];
            if (tooltipItems.length > 1 && context.dataset.label !== 'Event')  return '';
            if (tooltipItems.length > 1 && context.dataIndex % 2 === 0) return '';
            return `${context.formattedValue} ºC`
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
    order: -1,
    showLine: false,
    pointHoverBorderWidth: 0,
    pointRadius: 5,
    pointBackgroundColor: '#0088ff',
  }
  alertEventDataset: ChartDataset<'line'> = {
    data: [],
    label: 'Event',
    order: -1,
    showLine: false,
    pointRadius: 10,
    pointHoverRadius: 10,
    pointBackgroundColor: 'black',
    pointStyle: ['circle', this.alertImage]
  }
  noAlertEventDataset: ChartDataset<'line'> = {
    data: [],
    label: 'Event',
    order: -1,
    showLine: false,
    pointRadius: 10,
    pointHoverRadius: 10,
    pointBackgroundColor: 'white',
    pointStyle: ['circle', this.noAlertImage]
  }
  configuration: ChartConfiguration = {
    type: 'line',
    data: { datasets: [this.parameterDataset, this.noAlertEventDataset, this.alertEventDataset] },
    options: this.options
  }
  private _currentDelay: number;
  private _parameterId: string;
  private _offset: number = 5;
  private _min: number = Infinity;
  private _max: number = -Infinity;
  private _limit: { min: number, max: number }
  @Input() reset$: Observable<any>;
  @Input() set parameterId(parameterId: string) {
    this._parameterId = parameterId;
    if (!this.parameterDataset.label) this.parameterDataset.label = parameterId;
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

     // Update delay
    const lastTimestamp: number = data.timestamps[data.timestamps.length - 1];
    this.updateDelay(lastTimestamp);

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

    this.chart?.update();
  }
  @Input() set eventData(data: EventData) {
    if (!data) return;

    // Add points to the chart
    const value: Alert = JSON.parse(data.value);
    if (value.parameter_name === this._parameterId) {
      const point: Point = { x: value.alert_timestamp! / 1000000, y: value.alert_temperature! };
      if (value.status === 'no-alert') this.noAlertEventDataset.data.push(point, point);
      else this.alertEventDataset.data.push(point, point);
      this.chart?.update();
    }
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
    this.reset$?.subscribe(() => {
      this.parameterDataset.data = [];
      this.noAlertEventDataset.data = [];
      this.alertEventDataset.data = [];
    });
    this.alertImage.src = 'assets/alert.svg';
    this.noAlertImage.src = 'assets/no-alert.svg'
  }

  updateDelay(timestamp: number): void {
    const delay = Date.now() - timestamp / 1000000;
    const offset = 1000;
    if (!this._currentDelay || this._currentDelay - delay > offset || this._currentDelay - delay < -offset) {
      (this.options!.scales!['x'] as any).realtime.delay = delay + offset;
      this._currentDelay = delay;
    }
  }
}
