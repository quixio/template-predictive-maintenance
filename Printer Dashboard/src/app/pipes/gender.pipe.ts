import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'gender'
})
export class GenderPipe implements PipeTransform {
  transform(value?: string): string {
    switch (value) {
      case 'M':
        return 'Male';
      case 'F':
        return 'Female';
      case 'U':
        return 'Unknown';
      default:
        return 'Not Specified';
    }
  }
}
