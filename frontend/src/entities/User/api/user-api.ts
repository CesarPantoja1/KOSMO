import { apiClient } from '@/shared/api';
import type { User } from '../model/user-schema';

export const getUser = () => {
	return apiClient<User>('/api/user');
};
