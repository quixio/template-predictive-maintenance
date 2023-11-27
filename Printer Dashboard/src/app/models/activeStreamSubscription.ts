import { ActiveStream } from "./activeStream";
import { ActiveStreamAction } from "./activeStreamAction";

export interface ActiveStreamSubscription {
	streams?: ActiveStream[];
	action?: ActiveStreamAction;
}
