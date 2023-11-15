import { Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import { Chart, PointElement, ChartConfiguration, ChartDataset, ChartOptions, Legend, LineController, LineElement, LinearScale, Tooltip, ScaleChartOptions, ScaleOptionsByType } from 'chart.js';
import ChartStreaming, { RealTimeScale } from 'chartjs-plugin-streaming';
import 'chartjs-adapter-luxon';
import { Data } from 'src/app/models/data';
import { Observable } from 'rxjs';
import annotationPlugin from 'chartjs-plugin-annotation';
import { ParameterData } from 'src/app/models/parameterData';

@Component({
  selector: 'app-chart',
  templateUrl: './chart.component.html',
  styleUrls: ['./chart.component.scss']
})
export class ChartComponent implements OnInit {
  @ViewChild('canvas', { static: true }) canvas: ElementRef<HTMLCanvasElement>;
  chart: Chart;
  datasets: ChartDataset[] = [];
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
      }
    },
    plugins: {
      legend: {
        position: 'top',
        align: 'start',
        labels: {
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
  configuration: ChartConfiguration = {
    type: 'line',
    data: { datasets: this.datasets },
    options: this.options
  }
  private _lastTimestamp: number;
  private _currentDelay: number;

  @Input() key: string;
  @Input() forecastKey: string;
  @Input() range: { min: number, max: number };
  @Input() reset$: Observable<void>;
  // @Input() set range (range: { min: number, max: number }){
  //   (this.options!.scales!['y'] as any).min = range.min - 10;
  //   (this.options!.scales!['y'] as any).max = range.max + 10;
  // }
  @Input() set duration(duration: number) {
    (this.options!.scales!['x'] as any).realtime['duration'] = duration;
  }
  @Input() set delay(delay: number) {
    (this.options!.scales!['x'] as any).realtime['delay'] = delay;
  }
  @Input() set data(data: ParameterData) {
    this.onSetData(data);
  }

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

  onSetData(data: ParameterData) {
    const values = data?.numericValues![this.key];
    if (values) {
      data.timestamps?.forEach((timestamp, i) => {
        this.updateChart(this.key, { x: timestamp / 1000000, y: values[i] }, '#008eff')
        this._lastTimestamp = timestamp;
      });

      if (this.forecastKey) {
        (this.options.plugins!.annotation!.annotations as any)['forecast'] = {
          type: 'line',
          xMin: this._lastTimestamp / 1000000,
          xMax: this._lastTimestamp / 1000000,
          borderColor: 'rgb(255, 99, 132)',
          borderWidth: 2,
        }

        // Remove initial values of forecast
        const dataset = this.datasets.find((f) => f.label === this.forecastKey);
        if (dataset) dataset.data = dataset.data.filter((f: any) => f.x > this._lastTimestamp / 1000000);
      }
    }

    const forecastValues = data?.numericValues![this.forecastKey];
    if (forecastValues) {
      // remove previous forecast
      const dataset = this.datasets.find((f) => f.label === this.forecastKey);
      if (dataset) dataset.data = []

      data.timestamps?.forEach((timestamp, i) => {
        if (timestamp < this._lastTimestamp) return;
        this.updateChart(this.forecastKey, { x: timestamp / 1000000, y: forecastValues[i] }, '#ca5fff', false)
      });
    }


    if (this.range) {
      (this.options.plugins!.annotation!.annotations as any)['range'] = {
        type: 'box',
        yMin: this.range.min,
        yMax: this.range.max,
        backgroundColor: 'rgba(255, 99, 132, 0.25)'
      }
    }

    this.chart?.update();
  }

  updateChart(key: string, point: { x: number, y: number }, color?: string, hideAxis?: boolean): void {
    const delay = Date.now() - point.x;
    const offset = 1000;
    if (!this._currentDelay || this._currentDelay - delay > offset || this._currentDelay - delay < -offset) {
      (this.options!.scales!['x'] as any).realtime.delay = delay + offset;
      this._currentDelay = delay;
    }

    let dataset = this.datasets.find((f) => f.label === key);
    if (dataset) {
      dataset.data.push(point);
    } else {
      let options: any = {
        type: 'linear',
        axis: 'y',
        display: !hideAxis,
        min: this.range.min - 10,
        max: this.range.max + 10
      };
      let dataset: ChartDataset<'line'> = {
        data: [point],
        label: key,
        yAxisID: key,
        borderColor: color,
        pointBackgroundColor: color,
        pointHoverBorderWidth: 0,
        pointRadius: 0
      };
      this.options.scales![key] = options;
      this.datasets.push(dataset);
    }
  }

  reset() {
    this.chart.data.datasets.forEach((dataset) => {
      dataset.data = [];
    });
  }
}
