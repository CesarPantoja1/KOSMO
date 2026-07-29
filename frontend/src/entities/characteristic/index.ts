// MODELS
export type { CharacteristicResponse, SuggestCharacteristic } from './model/types';

// STORE
export { useCharacteristicStore } from './model/store';

// API
export {
	getCharacteristics,
	generateCharacteristics,
	getSuggestCharacteristics,
	addCharacteristic,
} from './api/api';
