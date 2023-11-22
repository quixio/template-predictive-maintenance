export interface Alert {
  status?: string,
  parameter_name?: string,
  message?: string,
  alert_timestamp?: number,
  alert_temperature?: number,
  disabled?: boolean;
}
