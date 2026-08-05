// MODELS
export type { CharacteristicResponse, SuggestCharacteristic, CharacteristicChatResponse } from './model/types';
export type { CharacteristicResponse as Characteristic } from './model/types';

// STORE
export { useCharacteristicStore } from './model/store';

// API
export {
	getCharacteristics,
	generateCharacteristics,
	getSuggestCharacteristics,
	addCharacteristic,
	deleteFeature,
} from './api/api';
