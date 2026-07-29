import { apiClient } from '@/shared/api';
import type { SuggestCharacteristic, CharacteristicResponse } from '../model/types';

export const getCharacteristics = async (
	projectId: string,
): Promise<CharacteristicResponse[]> => {
	const data = await apiClient<CharacteristicResponse[]>(
		`/api/v1/projects/${projectId}/features`,
		{ method: 'GET' },
	);
	return data;
};

export const generateCharacteristics = async (
	projectId: string,
): Promise<CharacteristicResponse[]> => {
	const data = await apiClient<CharacteristicResponse[]>(
		`/api/v1/projects/${projectId}/features`,
		{ method: 'POST' },
	);
	return data;
};

export const getSuggestCharacteristics = async (
	projectId: string,
): Promise<SuggestCharacteristic[]> => {
	const data = await apiClient<SuggestCharacteristic[]>(
		`/api/v1/projects/${projectId}/features/suggest`,
		{ method: 'POST' },
	);