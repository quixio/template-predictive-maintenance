/** Provides additional data for events */
export interface EventDefinition {
	/** The display name of the event */
	name: string;

	/** Description of the event */
	description: string;

	/**
	 * Optional field for any custom properties that do not exist on the event.
	 * For example this could be a json string, describing all possible event values
	 */
	customProperties: string;

	/**
	 * The level of the event. Defaults to @see EventLevel.Information
	 */
	level: EventLevel;

	/**
	 * Specifies the location of the event in the event groups hierarchy.
	 * For example: /Chassis/Engine
	 */
	location: string;
}

/** The severity of the event */
export enum EventLevel {
	Trace = 0,
	Debug = 1,
	Information = 2,
	Warning = 3,
	Error = 4,
	Critical = 5
}
