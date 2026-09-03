import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/api', () => ({
	getIntegrationStatus: vi.fn(),
	connectIntegration: vi.fn(),
	disconnectIntegration: vi.fn(),
}));

vi.mock('@/shared/api', () => ({
	authApi: { getMe: vi.fn() },
	formatApiError: (_err: unknown, fallback: string) => fallback,
}));

vi.mock('@/shared/model', () => ({
	useAuthStore: { getState: () => ({ setUser: vi.fn() }) },
}));

vi.mock('@/shared/ui/toast/toast', () => ({
	toast: { success: vi.fn(), error: vi.fn() },
}));

import { getIntegrationStatus, connectIntegration, disconnectIntegration } from '../api/api';
import { authApi } from '@/shared/api';
import { toast } from '@/shared/ui/toast/toast';
import { useOAuthIntegration } from './useOAuthIntegration';

const api = {
	getIntegrationStatus: vi.mocked(getIntegrationStatus),
	connectIntegration: vi.mocked(connectIntegration),
	disconnectIntegration: vi.mocked(disconnectIntegration),
};

const baseParams = {
	provider: 'github' as const,
	label: 'GitHub',
	messageType: 'github-oauth-code',
	buildAuthUrl: (redirectUri: string) => `https://auth.example.com?redirect=${redirectUri}`,
	redirectUri: 'https://app.example.com/perfil',
};

describe('useOAuthIntegration', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('consulta el estado de la integración al montar y lo expone', async () => {
		// Arrange
		api.getIntegrationStatus.mockResolvedValue({
			provider: 'github',
			is_connected: true,
			username: 'octocat',
		});
		const onStatusChange = vi.fn();

		// Act
		const { result } = renderHook(() => useOAuthIntegration({ ...baseParams, onStatusChange }));

		// Assert
		await waitFor(() => expect(result.current.loading).toBe(false));
		expect(result.current.isConnected).toBe(true);
		expect(result.current.username).toBe('octocat');
		expect(onStatusChange).toHaveBeenCalledWith(
			expect.objectContaining({ is_connected: true }),
		);
	});

	it('muestra un toast de error si falla la consulta de estado', async () => {
		// Arrange
		api.getIntegrationStatus.mockRejectedValue(new Error('network error'));

		// Act
		const { result } = renderHook(() => useOAuthIntegration(baseParams));

		// Assert
		await waitFor(() => expect(result.current.loading).toBe(false));
		expect(vi.mocked(toast.error)).toHaveBeenCalled();
	});

	it('handleConnect abre un popup con la URL de autorización', async () => {
		// Arrange
		api.getIntegrationStatus.mockResolvedValue({ provider: 'github', is_connected: false });
		const openSpy = vi.spyOn(window, 'open').mockReturnValue(null);
		const { result } = renderHook(() => useOAuthIntegration(baseParams));
		await waitFor(() => expect(result.current.loading).toBe(false));

		// Act
		act(() => {
			result.current.handleConnect();
		});

		// Assert
		expect(openSpy).toHaveBeenCalledWith(
			'https://auth.example.com?redirect=https://app.example.com/perfil',
			'oauth-github',
			'width=600,height=700',
		);
	});

	it('ignora mensajes postMessage de origen distinto', async () => {
		// Arrange
		api.getIntegrationStatus.mockResolvedValue({ provider: 'github', is_connected: false });
		const { result } = renderHook(() => useOAuthIntegration(baseParams));
		await waitFor(() => expect(result.current.loading).toBe(false));

		// Act
		act(() => {
			window.dispatchEvent(
				new MessageEvent('message', {
					origin: 'https://otro-origen.com',
					data: { type: 'github-oauth-code', code: 'abc' },
				}),
			);
		});

		// Assert
		expect(api.connectIntegration).not.toHaveBeenCalled();
	});

	it('procesa el código recibido por postMessage y conecta la integración', async () => {
		// Arrange
		api.getIntegrationStatus.mockResolvedValue({ provider: 'github', is_connected: false });
		api.connectIntegration.mockResolvedValue({
			provider: 'github',
			is_connected: true,
			username: 'octocat',
		});
		vi.mocked(authApi.getMe).mockResolvedValue({ subject: 'usr_1' } as never);
		const { result } = renderHook(() => useOAuthIntegration(baseParams));
		await waitFor(() => expect(result.current.loading).toBe(false));

		// Act
		await act(async () => {
			window.dispatchEvent(
				new MessageEvent('message', {
					origin: window.location.origin,
					data: { type: 'github-oauth-code', code: 'abc123' },
				}),
			);
		});

		// Assert
		await waitFor(() => expect(result.current.isConnected).toBe(true));
		expect(api.connectIntegration).toHaveBeenCalledWith('github', {
			code: 'abc123',
			redirect_uri: baseParams.redirectUri,
		});
		expect(vi.mocked(toast.success)).toHaveBeenCalled();
	});

	it('muestra un toast de error cuando el popup reporta oauth-error', async () => {
		// Arrange
		api.getIntegrationStatus.mockResolvedValue({ provider: 'github', is_connected: false });
		const { result } = renderHook(() => useOAuthIntegration(baseParams));
		await waitFor(() => expect(result.current.loading).toBe(false));

		// Act
		act(() => {
			window.dispatchEvent(
				new MessageEvent('message', {
					origin: window.location.origin,
					data: { type: 'oauth-error', error: 'access_denied' },
				}),
			);
		});

		// Assert
		expect(vi.mocked(toast.error)).toHaveBeenCalledWith(expect.stringContaining('access_denied'));
	});

	it('handleDisconnect actualiza el estado a desconectado', async () => {
		// Arrange
		api.getIntegrationStatus.mockResolvedValue({ provider: 'github', is_connected: true });
		api.disconnectIntegration.mockResolvedValue(undefined);
		const { result } = renderHook(() => useOAuthIntegration(baseParams));
		await waitFor(() => expect(result.current.isConnected).toBe(true));

		// Act
		await act(async () => {
			result.current.handleDisconnect();
			await Promise.resolve();
		});

		// Assert
		await waitFor(() => expect(result.current.isConnected).toBe(false));
		expect(vi.mocked(toast.success)).toHaveBeenCalled();
	});
});
