export interface CharacteristicResponse {
	id: string;
	project_id: string;
	number: number;
	title: string;
	slug: string;
	description: string;
	origin: string;
	display_id: string;
}

export interface SuggestCharacteristic {
	number: number;
	title: string;
	description: string;
	origin: string;
}

export interface CharacteristicSave {
	title: string;
	description: string;
	rationale: string;
}
