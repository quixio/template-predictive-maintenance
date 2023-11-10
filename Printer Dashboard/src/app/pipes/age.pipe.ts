import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'age'
})
export class AgePipe implements PipeTransform {
  transform(dateOfBirth?: string): number | null {
    if (!dateOfBirth) return null;

    // Parse the date of birth into a Date object
    const dob = new Date(dateOfBirth);

    // Calculate the age
    const today = new Date();
    const age = today.getFullYear() - dob.getFullYear();

    // Check if the birthday has occurred this year
    if (today.getMonth() < dob.getMonth() || (today.getMonth() === dob.getMonth() && today.getDate() < dob.getDate())) {
      return age - 1;
    }

    return age;
  }
}
