import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as integrationApi from '@/entities/integration/api/api';
import { ProfilePage } from './ProfilePage';
import { CuentaTab } from './CuentaTab';

vi.mock('next/navigation', () => ({
	useRouter: () => ({
		push: vi.fn(),
		replace: vi.fn(),
		back: vi.fn(),
	}),
	usePathname: () => '/perfil',
}));

vi.mock('@/entities/user', () => {
	const fakeState = {
		user: {
			subject: 'usr_01HTESTUSER1234567890',
			name: 'Gianfranco Dev',
			email: 'gian@example.com',
			avatar_url: null,
			scopes: ['agent:run', 'profile:read'],
		},
	};
	const useAuthStoreFn = (selector: (state: typeof fakeState) => unknown) => selector(fakeState);
	useAuthStoreFn.getState = () => ({
		user: fakeState.user,
		setUser: vi.fn(),
	});
	return {
		useAuthStore: useAuthStoreFn,
		authApi: {
			getMe: vi.fn().mockResolvedValue({
				subject: 'usr_01HTESTUSER1234567890',
				name: 'Octo Cat',
				email: 'octo@github.com',
				avatar_url: 'https://github.com/images/octocat.png',
				scopes: ['agent:run', 'profile:read'],
			}),
		},
	};
});

vi.mock('@/shared/api', async (importOriginal) => {
	const actual = await importOriginal<typeof import('@/shared/api')>();
	return {
		...actual,
		authApi: {
			...actual.authApi,
			logout: vi.fn().mockResolvedValue(undefined),
		},
	};
});

vi.mock('@/features/app-state', () => ({
	clearAllStores: vi.fn(),
}));

vi.mock('@/features/ai-config', () => ({
	AiConfigForm: () => <div data-testid='ai-config-form'>AI Config Form</div>,
}));

vi.mock('@/shared/ui/toast/toast', () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
		info: vi.fn(),
	},
}));

describe('ProfilePage and CuentaTab OAuth flow', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('renderiza la información del usuario con nombre y correo', async () => {
		vi.spyOn(integrationApi, 'getIntegrationStatus').mockResolvedValue({
			provider: 'github',
			is_connected: false,
		});

		render(<ProfilePage />);

		expect(screen.getByText('Perfil')).toBeInTheDocument();
		expect(screen.getByText('Gianfranco Dev')).toBeInTheDocument();
		expect(screen.getByText('gian@example.com')).toBeInTheDocument();
		expect(screen.getByText('GD')).toBeInTheDocument();
	});

	it('abre el popup de OAuth con la URL correcta al pulsar Conectar', async () => {
		vi.spyOn(integrationApi, 'getIntegrationStatus').mockResolvedValue({
			provider: 'github',
			is_connected: false,
		});

		const windowOpenSpy = vi.spyOn(window, 'open').mockReturnValue(null);

		render(<CuentaTab user={{ subject: 'usr_1', scopes: [] }} />);

		await waitFor(() => {
			expect(screen.getAllByRole('button', { name: 'Conectar' }).length).toBeGreaterThan(0);
		});

		const connectButtons = screen.getAllByRole('button', { name: 'Conectar' });
		fireEvent.click(connectButtons[0]);

		expect(windowOpenSpy).toHaveBeenCalledTimes(1);
		const openedUrl = windowOpenSpy.mock.calls[0][0] as string;
		expect(openedUrl).toContain('https://github.com/login/oauth/authorize');
		expect(openedUrl).toContain('state=github');
		expect(openedUrl).toContain('scope=repo');
	});

	it('procesa el mensaje de postMessage en CuentaTab y actualiza el estado a conectado', async () => {
		vi.spyOn(integrationApi, 'getIntegrationStatus').mockResolvedValue({
			provider: 'github',
			is_connected: false,
		});

		const connectSpy = vi.spyOn(integrationApi, 'connectIntegration').mockResolvedValue({
			provider: 'github',
			is_connected: true,
			username: 'octocat',
			connected_at: new Date().toISOString(),
		});

		render(<CuentaTab user={{ subject: 'usr_1', scopes: [] }} />);

		await waitFor(() => {
			expect(screen.getAllByRole('button', { name: 'Conectar' }).length).toBeGreaterThan(0);
		});

		// Simulamos el postMessage emitido por el popup
		window.dispatchEvent(
			new MessageEvent('message', {
				origin: window.location.origin,
				data: {
					type: 'github-oauth-code',
					code: 'fake-oauth-auth-code-123',
				},
			}),
		);

		await waitFor(() => {
			expect(connectSpy).toHaveBeenCalledWith('github', {
				code: 'fake-oauth-auth-code-123',
				redirect_uri: expect.stringContaining('/perfil'),
			});
		});

		await waitFor(() => {
			expect(screen.getByText('@octocat')).toBeInTheDocument();
		});
	});

	it('detecta cuando ProfilePage se monta dentro de un popup y emite postMessage al opener cerrando la ventana', async () => {
		const mockOpener = {
			postMessage: vi.fn(),
		};
		const closeSpy = vi.spyOn(window, 'close').mockImplementation(() => {});

		// Simulamos window.opener y query params
		Object.defineProperty(window, 'opener', {
			value: mockOpener,
			writable: true,
			configurable: true,
		});

		delete (window as { location?: unknown }).location;
		window.location = new URL('http://localhost:3000/perfil?code=github_code_abc&state=github') as unknown as Location;

		render(<ProfilePage />);

		expect(mockOpener.postMessage).toHaveBeenCalledWith(
			{
				type: 'github-oauth-code',
				code: 'github_code_abc',
			},
			'http://localhost:3000',
		);
		expect(closeSpy).toHaveBeenCalled();

		// Cleanup
		Object.defineProperty(window, 'opener', {
			value: null,
			writable: true,
			configurable: true,
		});
	});
});
