export type Visibility = '+' | '-' | '#';

export interface UmlItem {
	id: string;
	visibility: Visibility;
	name: string;
	type?: string; // Para atributos (int...) o retorno de métodos (void...)
	params?: string; // Para métodos: ej. "id: string"
	isStatic?: boolean;
}

export interface UmlNodeData {
	name: string;
	stereotype?: string; // ej. "<<interface>>" o "<<enum>>"
	isAbstract?: boolean;
	attributes: UmlItem[];
	methods: UmlItem[];
	// Trazabilidad a RQ - ids
	requirementIds: string[];
	// Opcional para Enums
	values?: string[];
}

export type UmlRelationType =
	| 'association'
	| 'aggregation'
	| 'composition'
	| 'inheritance'
	| 'dependency'
	| 'realization';

export interface UmlEdgeData {
	relationType: UmlRelationType;
	sourceCardinality?: string;
	targetCardinality?: string;
}
