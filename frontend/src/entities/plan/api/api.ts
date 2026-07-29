import { apiClient } from '@/shared/api';
import { USE_MOCKS } from '@/shared/api/config';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Mock state ---
