import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { ActiveStream } from '../models/activeStream';

@Injectable({
  providedIn: 'root'
})
export class DataService {
  isSidenavOpen$ = new Subject<boolean>();
  stream: ActiveStream;

  constructor() {
  }
}
