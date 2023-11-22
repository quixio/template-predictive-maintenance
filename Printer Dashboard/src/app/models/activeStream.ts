import { EventDefinition } from './eventDefinition';
import { ParameterDefinition } from './parameterDefinition';

/** Stands for an active stream running in the topic */
export interface ActiveStream {
	/** Stream Id */
	streamId: string;

	/** Topic Id */
	topicId: string;

	/** The human friendly name of the stream */
	name: string;

	/**
	 * Specify location of the stream in data catalogue.
	 * For example: /cars/ai/carA/.
	 */
	location: string;

	/** Additional metadata for the stream. */
	metadata: { [key: string]: string };

	/** The ids of streams this stream is derived from. */
	parents: string[];

	/**
	 * Indicates the time when data was originally recorded.
	 * This can be different than the time the data is streamed.
	 */
	timeOfRecording: Date | null;

	/** Parameters present in the stream */
	parameters: { [key: string]: ParameterDefinition };

	/** Events present in the stream */
	events: { [key: string]: EventDefinition };

	/** Indicates when the stream was seen for the first time. */
	firstSeen: Date | null;

	/** Indicates the last time the stream was seen. */
	lastSeen: Date | null;

	/** Status of the stream */
	status: string;

	/** Indicates the last time the stream received data. */
	lastData: Date | null;
}
