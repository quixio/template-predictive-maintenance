import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class DataService {
  isSidenavOpen$ = new Subject<boolean>();
  printer: any;

  constructor() {
  }
}
