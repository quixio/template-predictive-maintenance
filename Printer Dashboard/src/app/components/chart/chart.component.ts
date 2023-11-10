import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { Chart, PointElement, ChartConfiguration, ChartDataset, ChartOptions, Legend, LineController, LineElement, LinearScale } from 'chart.js';
import ChartStreaming, { RealTimeScale } from 'chartjs-plugin-streaming';
import 'chartjs-adapter-luxon';

@Component({
  selector: 'app-chart',
  templateUrl: './chart.component.html',
  styleUrls: ['./chart.component.scss']
})
export class ChartComponent implements OnInit {
  @ViewChild('canvas', { static: true }) canvas: ElementRef<HTMLCanvasElement>;

  chart: Chart;
  datasets: ChartDataset[] = [];
  currentDelay: number;
  options: ChartOptions = {
    interaction: {
      mode: 'index',
      intersect: false
    },
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        type: 'realtime',
        realtime: {
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
          filter: (item) => item.text !== 'crash',
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
        backgroundColor: '#fff',
        bodyColor: '#646471',
        titleColor: '#000',
        borderColor: Chart.defaults.borderColor.toString(),
        borderWidth: 1,
        filter: (item) => item.dataset.label !== 'crash',
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

  chartParameters = ['gForceX', 'gForceY', 'gForceZ', 'crash'];
  chartColors = ['#008eff', '#ca5fff', '#fe9353', '#ff4040'];

  constructor() {
    Chart.register(
      LinearScale,
      LineController,
      PointElement,
      LineElement,
      RealTimeScale,
      Legend,
      ChartStreaming
    );
  }

  ngOnInit(): void {
    const ctx = this.canvas.nativeElement.getContext('2d');
    this.chart = new Chart(ctx!, this.configuration);
  }
}
