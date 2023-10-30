import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { USERS } from 'src/app/constants/users';
import { EventData } from 'src/app/models/eventData';
import { User } from 'src/app/models/user';

@Component({
  selector: 'app-dialog',
  templateUrl: './dialog.component.html',
  styleUrls: ['./dialog.component.scss']
})
export class DialogComponent {

  constructor(
    private dialogRef: MatDialogRef<DialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: EventData
  ) {}

  close(): void {
    this.dialogRef.close();
  }
}
