import { Component, ElementRef, ViewChild } from '@angular/core';
import { Data } from 'src/app/models/data';

@Component({
  selector: 'app-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent {
  @ViewChild('tableCell', { static: true }) tableCell: ElementRef<HTMLDivElement>;
  dataSource: Data[] = [];
  scroll: { height: number, top: number };



  updateScroll(): void {
    if (this.tableCell.nativeElement.scrollTop > 0) {
      const height = this.tableCell.nativeElement.scrollHeight - this.scroll.height;
      this.tableCell.nativeElement.scrollTop += height;
    }

    this.scroll = {
      height: this.tableCell.nativeElement.scrollHeight,
      top: this.tableCell.nativeElement.scrollTop
    }
  }
}
