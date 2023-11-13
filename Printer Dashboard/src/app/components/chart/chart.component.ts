import { Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import { Chart, PointElement, ChartConfiguration, ChartDataset, ChartOptions, Legend, LineController, LineElement, LinearScale, Tooltip } from 'chart.js';
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
  currentDelay: number = 0;
  options: ChartOptions = {
    interaction: {
      mode: 'index',
      intersect: false
    },
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        type: 'realtime',
        realtime: {
          delay: this.currentDelay,
          duration: 300000,
          refresh: 500,
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
    data: {
      datasets: this.datasets
    },
    options: this.options
  }

  @Input() key: string;
  @Input() set data(data: ParameterData) {
    if (!data?.numericValues![this.key] && !data?.numericValues![this.key + '-forecast']) return;
    data.timestamps?.forEach((timestamp, i) => {
      this.updateChart(this.key, { x: timestamp / 1000000, y: data.numericValues![this.key][i] })
    });
    const lastTimestamp = data.timestamps![data.timestamps!.length - 1] / 1000000;
    this.options.plugins!.annotation!.annotations = {
      range: {
        type: 'box',
        yMin: 50,
        yMax: 70,
        backgroundColor: 'rgba(255, 99, 132, 0.25)'
      },
      line1: {
        type: 'line',
        xMin: lastTimestamp,
        xMax: lastTimestamp,
        borderColor: 'rgb(255, 99, 132)',
        borderWidth: 2,
      }
    }
    this.chart?.update();
  }
  @Input() reset$: Observable<void>;

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

  updateChart(key: string, point: { x: number, y: number }, isEvent: boolean = false): void {
    const delay = Date.now() - point.x;
    const offset = 1000;
    if (!this.currentDelay || this.currentDelay - delay > offset || this.currentDelay - delay < -offset) {
      (this.options!.scales!['x'] as any).realtime.delay = delay + offset;
      this.currentDelay = delay;
    }

    let dataset = this.datasets.find((f) => f.label === key);
    if (dataset) {
      dataset.data.push(point);
    } else {
      const color = key.includes('forecast') ? '#ca5fff' : '#008eff';
      let options: any = { type: 'linear', axis: 'y' };
      let dataset: ChartDataset<'line'> = {
        data: [point],
        label: key,
        yAxisID: key,
        borderColor: color,
        pointBackgroundColor: color,
        pointHoverBorderWidth: 0,
        pointRadius: 0
      };

      if (isEvent) {
        const image = new Image();
        image.src = 'assets/alert.png'
        dataset = { ...dataset, pointStyle: image, pointRadius: 10, showLine: false, order: -1 };
        options = { ...options, min: 0.9, max: 2 }
      }

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
