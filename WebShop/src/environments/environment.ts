// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const environment = {
	isProduction: false,
  TOKEN: process.env["TOKEN"],
  WORKSPACE_ID: process.env["WORKSPACE_ID"],
  CLICK_TOPIC: process.env["CLICK_TOPIC"],
  OFFERS_TOPIC: process.env["OFFERS_TOPIC"],
  DEPLOYMENT_ID: process.env["DEPLOYMENT_ID"]
};

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/plugins/zone-error';  // Included with Angular CLI.
