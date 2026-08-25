import { describe, expect, it, vi, beforeEach, Mock } from 'vitest';
import { authApi } from './auth';
import { apiClient } from '@/shared/api/client';
import { useAuthStore } from '../model/store';


vi.mock('@/shared/api/client', () => ({
    apiClient: vi.fn(),
}));

vi.mock('@/shared/lib/clearAllStores', () => ({
    clearAllStores: vi.fn(),
}));

// Mock the Zustand store
vi.mock('../model/store', () => {
    const setTokens = vi.fn();
    const setUser = vi.fn();
    const clearAuth = vi.fn();
    
    return {
        useAuthStore: {
            getState: () => ({
                setTokens,
                setUser,
                clearAuth,
                refreshToken: 'refresh-token-mock',
            }),
            persist: { clearStorage: vi.fn() },
            setState: vi.fn(),
        },
    };
});

describe('authApi (PKCE Flow)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should complete the PKCE flow correctly on login', async () => {
        // 1. Mock API responses
        const mockAuthCodeResponse = { authorization_code: 'mock-auth-code', expires_in: 300 };
        const mockTokenResponse = {
            access: { token: 'mock-access', expires_in: 3600 },
            refresh: { token: 'mock-refresh', expires_in: 86400 }
        };
        const mockUserResponse = { id: 'usr-1', email: 'test@example.com', created_at: '2025-01-01' };

        (apiClient as Mock).mockImplementation((url: string) => {
            if (url === '/api/v1/auth/authorize') return Promise.resolve(mockAuthCodeResponse);
            if (url === '/api/v1/auth/token') return Promise.resolve(mockTokenResponse);
            if (url === '/api/v1/auth/me') return Promise.resolve(mockUserResponse);
            return Promise.reject(new Error('Unknown url'));
        });

        const storeState = useAuthStore.getState();

        // 2. Call login
        await authApi.login('test@example.com', 'password123');

        // 3. Verify interactions
        expect(apiClient).toHaveBeenCalledTimes(3);

        // Verify authorize (challenge step)
        expect(apiClient).toHaveBeenNthCalledWith(1, '/api/v1/auth/authorize', expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('code_challenge'),
        }));

        // Verify token exchange (verifier step)
        expect(apiClient).toHaveBeenNthCalledWith(2, '/api/v1/auth/token', expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('code_verifier'),
        }));

        // Verify store hydration
        expect(storeState.setTokens).toHaveBeenCalledWith('mock-access', 'mock-refresh');
        expect(storeState.setUser).toHaveBeenCalledWith(mockUserResponse);
    });
});

