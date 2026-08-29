import type { ReactNode } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { IntegrationProvider, IntegrationStatus } from '@/entities/integration';
import {
	connectIntegration,
	disconnectIntegration,
	getIntegrationStatus,
} from '@/entities/integration';
import { User } from '@/entities/user';
import {
	GITHUB_CLIENT_ID,
	GITHUB_SCOPES,
	PUBLIC_APP_DOMAIN,
	RAILWAY_CLIENT_ID,
	RAILWAY_SCOPES,
	formatApiError,
} from '@/shared/api';
import { GitHub, Railway } from '@/shared/ui';
import { toast } from '@/shared/ui/toast/toast';

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
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
				<h3 className='text-lg font-semibold text-neutral-800 mb-4'>Integraciones</h3>
				<div className='flex flex-col divide-y divide-neutral-100'>
					<OAuthIntegrationRow
						provider='github'
						label='GitHub'
						icon={<GitHub size={24} color='text-neutral-800' />}
						messageType='github-oauth-code'
						buildAuthUrl={(redirectUri) =>
							`https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=${GITHUB_SCOPES}&redirect_uri=${encodeURIComponent(redirectUri)}&state=github`
						}
					/>
					<OAuthIntegrationRow
						provider='railway'
						label='Railway'
						icon={<Railway size={24} color='text-neutral-800' />}
						messageType='railway-oauth-code'
						buildAuthUrl={(redirectUri) =>
							`https://backboard.railway.com/oauth/auth?response_type=code&client_id=${RAILWAY_CLIENT_ID}&scope=${encodeURIComponent(RAILWAY_SCOPES)}&redirect_uri=${encodeURIComponent(redirectUri)}&state=railway&prompt=consent`
						}
					/>
				</div>
			</div>
		</div>
	);
};

export { CuentaTab };

type OAuthIntegrationRowProps = {
	provider: IntegrationProvider;
	label: string;
	icon: ReactNode;
	messageType: string;
	buildAuthUrl: (redirectUri: string) => string;
};

function OAuthIntegrationRow({
	provider,
	label,
	icon,
	messageType,
	buildAuthUrl,
}: OAuthIntegrationRowProps) {
	const [status, setStatus] = useState<IntegrationStatus | null>(null);
	const [loading, setLoading] = useState(true);
	const [actionLoading, setActionLoading] = useState(false);
	const popupRef = useRef<Window | null>(null);
	const processingCodeRef = useRef<string | null>(null);

	useEffect(() => {
		getIntegrationStatus(provider)
			.then(setStatus)
			.catch((err) =>
				toast.error(
					formatApiError(
						err,
						`No se pudo verificar el estado de la integración con ${label}.`,
					),
				),
			)
			.finally(() => setLoading(false));
	}, [provider, label]);

	const handleOAuthMessage = useCallback(
		(event: MessageEvent) => {
			if (event.origin !== window.location.origin) return;
			if (event.data?.type === 'oauth-error') {
				toast.error(`Error en la autorización de ${label}: ${event.data.error || 'Acceso denegado'}`);
				popupRef.current?.close();
				popupRef.current = null;
				return;
			}
			if (event.data?.type !== messageType) return;

			const code = event.data.code as string;
			if (!code || processingCodeRef.current === code) return;
			processingCodeRef.current = code;

			setActionLoading(true);
			connectIntegration(provider, {
				code,
				redirect_uri: `${PUBLIC_APP_DOMAIN}/perfil`,
			})
				.then((result) => {
					setStatus(result);
					toast.success(
						`Cuenta de ${label} vinculada como @${result.username ?? 'desconocido'}.`,
					);
				})
				.catch((err) =>
					toast.error(
						formatApiError(
							err,
							`Error al vincular la cuenta de ${label}. Intenta de nuevo.`,
						),
					),
				)
				.finally(() => {
					setActionLoading(false);
					processingCodeRef.current = null;
				});

			popupRef.current?.close();
			popupRef.current = null;
		},
		[provider, label, messageType],
	);

	useEffect(() => {
		window.addEventListener('message', handleOAuthMessage);
		return () => window.removeEventListener('message', handleOAuthMessage);
	}, [handleOAuthMessage]);

	const handleConnect = () => {
		const redirectUri = `${PUBLIC_APP_DOMAIN}/perfil`;
		popupRef.current = window.open(
			buildAuthUrl(redirectUri),
			`oauth-${provider}`,
			'width=600,height=700',
		);
	};

	const handleDisconnect = () => {
		setActionLoading(true);
		disconnectIntegration(provider)
			.then(() => {
				setStatus({ provider, is_connected: false });
				toast.success(`Cuenta de ${label} desconectada.`);
			})
			.catch(() =>
				toast.error(`Error al desconectar la cuenta de ${label}. Intenta de nuevo.`),
			)
			.finally(() => setActionLoading(false));
	};

	const isConnected = status?.is_connected ?? false;

	return (
		<div className='flex flex-col gap-4 py-4 first:pt-0 last:pb-0'>
			<div className='flex items-center justify-between'>
				<div className='flex items-center gap-3'>
					{icon}
					<div>
						<p className='text-neutral-800 font-medium'>{label}</p>
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
