export interface Characteristic {
	id: string;
	project_id: string;
	number: number;
	title: string;
	slug: string;
	description: string;
	requirements: string;
	rationale: string;
	inferred_from: string[];
	display_id: string;
}

export interface AlternativeCharacteristic {
	id: string;
	number: number;
	title: string;
	description: string;
	rationale: string;
	inferred_from: string[];
}

export interface CharacteristicSave {
	title: string;
	description: string;
	rationale: string;
}
