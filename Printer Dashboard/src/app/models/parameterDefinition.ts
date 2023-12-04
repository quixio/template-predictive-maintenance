/** Describes additional context for the parameter */
export interface ParameterDefinition {
	/** Human friendly display name of the parameter */
	name: string;

	/** Description of the parameter */
	description: string;

	/** Type of data received on this parameter */
	dataType: string;

	/** Minimum value of the parameter */
	minimumValue: number | null;

	/** Maximum value of the parameter */
	maximumValue: number | null;

	/** Unit of the parameter  */
	unit: string;

	/** The formatting to apply on the value for display purposes */
	format: string;

	/**
	 * Optional field for any custom properties that do not exist on the parameter.
	 * For example this could be a json string, describing the optimal value range of this parameter
	 */
	customProperties: string;

	/**
	 * Specifies the location of the parameter in the parameter groups hierarchy.
	 * For example: /Chassis/Engine
	 */
	location: string;
}
