'use client';

import type { ReactNode } from 'react';

export type OAuthIntegrationProps = {
	label: string;
	icon: ReactNode;
	loading: boolean;
	actionLoading: boolean;
	isConnected: boolean;
	username?: string | null;
	onConnect: () => void;
	onDisconnect: () => void;
};

export function OAuthIntegration({
	label,
	icon,
	loading,
	actionLoading,
	isConnected,
	username,
	onConnect,
	onDisconnect,
}: OAuthIntegrationProps) {
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
									? `${username ? `@${username}` : ''}`
									: 'No conectado'}
						</p>
					</div>
				</div>
				{!loading && (
					<button
						type='button'
						onClick={isConnected ? onDisconnect : onConnect}
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
