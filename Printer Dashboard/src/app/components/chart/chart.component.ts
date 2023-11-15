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
        ticks: {}
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
  dataset: ChartDataset<'line'> = {
    data: [],
    yAxisID: 'y',
    pointHoverBorderWidth: 0,
    pointRadius: 0,
    borderColor: '#0088ff',
    pointBackgroundColor: '#0088ff',
  }
  configuration: ChartConfiguration = {
    type: 'line',
    data: { datasets: [this.dataset] },
    options: this.options
  }
  private _currentDelay: number;
  private _key: string;
  @Input() reset$: Observable<void>;
  @Input() set key(key: string) {
    this.dataset.label = key;
    this._key = key;
  }
  @Input() set color(color: string) {
    this.dataset.borderColor = color;
    this.dataset.pointBackgroundColor = color;
  }
  @Input() set label(label: string) {
    this.dataset.label = label;
  }
  @Input() set range(range: { min: number, max: number }) {
    (this.options as any).plugins.annotation.annotations['range'] = {
      type: 'box',
      yMin: range.min,
      yMax: range.max,
      backgroundColor: '#00FF000f',
      borderWidth: 0
    };
    (this.options as any).scales['y'].min = range.min - 5;
    (this.options as any).scales['y'].max = range.max + 5;
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
  @Input() set data(data: ParameterData) {
    const values = data?.numericValues![this._key];
    if (values) {
      data.timestamps?.forEach((timestamp, i) => {
        this.dataset.data.push({ x: timestamp / 1000000, y: values[i] });
      });
      const lastTimestamp: number = data.timestamps[data.timestamps.length - 1];
      this.updateDelay(lastTimestamp);
    }
    this.chart?.update();
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

  updateDelay(timestamp: number): void {
    const delay = Date.now() - timestamp / 1000000;
    const offset = 1000;
    if (!this._currentDelay || this._currentDelay - delay > offset || this._currentDelay - delay < -offset) {
      (this.options!.scales!['x'] as any).realtime.delay = delay + offset;
      this._currentDelay = delay;
    }
  }

  reset() {
    this.chart.data.datasets.forEach((dataset) => {
      dataset.data = [];
    });
  }
}
