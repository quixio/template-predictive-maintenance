import { Component, OnDestroy, OnInit } from '@angular/core';
import { MediaObserver } from '@angular/flex-layout';
import { FormArray, FormControl, FormGroup } from '@angular/forms';
import { Observable, Subscription, map, of } from 'rxjs';
import { PRODUCTS } from 'src/app/constants/products';
import { Categories } from 'src/app/models/categories';
import { Product } from 'src/app/models/product';
import { DataService } from 'src/app/services/data.service';

@Component({
  templateUrl: './product-list.component.html',
  styleUrls: ['./product-list.component.scss']
})
export class ProductListComponent implements OnInit, OnDestroy {
  products: Product[] = PRODUCTS;
  categories: string[] = Object.values(Categories).sort();
  formArray = new FormArray<FormControl>([]);
  form = new FormGroup({ categories: this.formArray });
  subscription: Subscription;
  isMainSidenavOpen$: Observable<boolean>;

  constructor(public media: MediaObserver, private dataService: DataService) { }

  ngOnInit(): void {
    this.categories.forEach((category: string) => {
      const value = this.dataService.categorySelection?.includes(category)
      this.formArray.push(new FormControl(value));
    });

    this.subscription = this.formArray.valueChanges.subscribe((values: boolean[]) => {
      this.dataService.categorySelection = this.categories.filter((_, i) => values[i]);
      if (!this.dataService.categorySelection?.length) this.products = PRODUCTS
      else this.products = PRODUCTS.filter((f) => this.dataService.categorySelection.includes(f.category))
    });

    // Dispatch valueChanges to set the initial selection
    this.formArray.updateValueAndValidity();

    this.isMainSidenavOpen$ = this.dataService.isSidenavOpen$.asObservable()
  }

  clearSelection(): void {
    this.formArray.reset();
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}
