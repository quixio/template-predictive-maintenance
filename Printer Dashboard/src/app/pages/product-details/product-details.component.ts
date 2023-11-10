import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Observable, Subscription, delay } from 'rxjs';
import { PRODUCTS } from 'src/app/constants/products';
import { Product } from 'src/app/models/product';
import { ConnectionStatus, QuixService } from 'src/app/services/quix.service';
import { DataService } from './../../services/data.service';
import { ParameterData } from 'src/app/models/parameterData';
import { Data } from 'src/app/models/data';
import { USERS } from 'src/app/constants/users';
import { User } from 'src/app/models/user';


@Component({
  templateUrl: './product-details.component.html',
  styleUrls: ['./product-details.component.scss']
})
export class ProductDetailsComponent implements OnInit, OnDestroy {
  product: Product | undefined;
  isMainSidenavOpen$: Observable<boolean>;
  subscription: Subscription;

  constructor(
    private route: ActivatedRoute,
    private quixService: QuixService,
    private dataService: DataService
  ) { }

  ngOnInit(): void {
    const productId = this.route.snapshot.paramMap.get('id');
    this.product = PRODUCTS.find((f) => f.id === productId);

    this.subscription = this.quixService.writerConnStatusChanged$.subscribe((status) => {
      if (status !== ConnectionStatus.Connected) return;
      this.sendData();
    });

    this.isMainSidenavOpen$ = this.dataService.isSidenavOpen$.asObservable();
  }

  sendData(): void {
    if (!this.product) return;
    const user: User = this.dataService.user || USERS[0];
    const payload: Data = {
      timestamps: [new Date().getTime() * 1000000],
      stringValues: {
        'userId': [user.userId],
        'ip': [this.dataService.userIp],
        'userAgent': [navigator.userAgent],
        'productId': [this.product.id],
      }
    };
    const topicId = this.quixService.workspaceId + '-' + this.quixService.clickTopic;
    this.quixService.sendParameterData(topicId, user.userId, payload);
  }

  clearSelection(): void {
    this.dataService.categorySelection = [];
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}
