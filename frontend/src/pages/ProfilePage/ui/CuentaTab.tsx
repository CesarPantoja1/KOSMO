import type { IntegrationStatus } from '@/entities/integration';
import {
	connectIntegration,
	disconnectIntegration,
	getIntegrationStatus,
} from '@/entities/integration';
import { User } from '@/entities/user';
import { GITHUB_CLIENT_ID, GITHUB_SCOPES, PUBLIC_APP_DOMAIN } from '@/shared/api';
import { toast } from '@/shared/ui/toast/toast';
import { useCallback, useEffect, useRef, useState } from 'react';

type CuentaTabProps = {
	user: User | null;
};

const CuentaTab = ({ user }: CuentaTabProps) => {
	const subject = user?.subject || 'No disponible';
	const scopes = user?.scopes || [];

	return (
		<div className='flex flex-col gap-6 animate-fade-in'>
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
				<h3 className='text-lg font-semibold text-neutral-800 mb-4'>
					Información del usuario
				</h3>
				<div className='flex flex-col gap-4'>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
							Subject
						</label>
						<p className='text-neutral-800 font-mono text-sm bg-neutral-50 border border-neutral-300 rounded-lg px-3 py-2.5'>
							{subject}
						</p>
					</div>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
							Scopes
						</label>
						<div className='flex flex-wrap gap-2'>
							{scopes.length > 0 ? (
								scopes.map((scope) => (
									<span
										key={scope}
										className='text-xs font-medium px-2.5 py-1 rounded-full bg-primary-500/10 text-primary-600 border border-primary-500/20'
									>
										{scope}
									</span>
								))
							) : (
								<span className='text-neutral-400 text-sm'>Sin scopes</span>
							)}
						</div>
					</div>
					<div>
						<label className='text-neutral-500 text-sm font-medium mb-1.5 block'>
							Estado
						</label>
						<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-success-50 text-success-700 border border-success-500/20'>
							Activo
						</span>
					</div>
				</div>
			</div>
			<GitHubIntegration />
		</div>
	);
};

export { CuentaTab };

function GitHubIntegration() {
	const [status, setStatus] = useState<IntegrationStatus | null>(null);
	const [loading, setLoading] = useState(true);
	const [actionLoading, setActionLoading] = useState(false);
	const popupRef = useRef<Window | null>(null);

	useEffect(() => {
		getIntegrationStatus('github')
			.then(setStatus)
			.catch(() =>
				toast.error('No se pudo verificar el estado de la integración con GitHub.'),
			)
			.finally(() => setLoading(false));
	}, []);

	const handleOAuthMessage = useCallback((event: MessageEvent) => {
		if (event.origin !== window.location.origin) return;
		if (event.data?.type !== 'github-oauth-code') return;

		const code = event.data.code as string;
		if (!code) return;

		setActionLoading(true);
		connectIntegration('github', {
			code,
			redirect_uri: `${PUBLIC_APP_DOMAIN}/perfil`,
		})
			.then((result) => {
				setStatus(result);
				toast.success(
					`Cuenta de GitHub vinculada como @${result.username ?? 'desconocido'}.`,
				);
			})
			.catch(() =>
				toast.error('Error al vincular la cuenta de GitHub. Intenta de nuevo.'),
			)
			.finally(() => setActionLoading(false));

		popupRef.current?.close();
		popupRef.current = null;
	}, []);

	useEffect(() => {
		window.addEventListener('message', handleOAuthMessage);
		return () => window.removeEventListener('message', handleOAuthMessage);
	}, [handleOAuthMessage]);

	const handleConnect = () => {
		const redirectUri = `${PUBLIC_APP_DOMAIN}/perfil`;
		const url = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=${GITHUB_SCOPES}&redirect_uri=${encodeURIComponent(redirectUri)}`;
		popupRef.current = window.open(url, 'github-oauth', 'width=600,height=700');
	};

	const handleDisconnect = () => {
		setActionLoading(true);
		disconnectIntegration('github')
			.then(() => {
				setStatus({ provider: 'github', is_connected: false });
				toast.success('Cuenta de GitHub desconectada.');
			})
			.catch(() =>
				toast.error('Error al desconectar la cuenta de GitHub. Intenta de nuevo.'),
			)
			.finally(() => setActionLoading(false));
	};

	const isConnected = status?.is_connected ?? false;

	return (
		<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
			<h3 className='text-lg font-semibold text-neutral-800 mb-4'>Integraciones</h3>
			<div className='flex items-center justify-between'>
				<div className='flex items-center gap-3'>
					<svg
						className='w-6 h-6 text-neutral-800'
						viewBox='0 0 24 24'
						fill='currentColor'
					>
						<path d='M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z' />
					</svg>
					<div>
						<p className='text-neutral-800 font-medium'>GitHub</p>
						<p className='text-neutral-500 text-sm'>
							{loading
								? 'Verificando...'
								: isConnected
									? `Conectado${status?.username ? ` como @${status.username}` : ''}`
									: 'No conectado'}
						</p>
					</div>
				</div>
				{!loading && (
					<button
						type='button'
						onClick={isConnected ? handleDisconnect : handleConnect}
						disabled={actionLoading}
						className={
							isConnected ? 'btn btn-sm btn-destructive' : 'btn btn-primary btn-sm'
						}
					>
						{actionLoading ? 'Procesando...' : isConnected ? 'Desconectar' : 'Conectar'}
					</button>
				)}
			</div>
		</div>
	);
}
