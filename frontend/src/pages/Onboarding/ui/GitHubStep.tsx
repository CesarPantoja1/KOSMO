'use client';

import { useCallback } from 'react';
import { useGithubOAuth } from '@/entities/integration';
import { GitHub, OAuthIntegration } from '@/shared/ui';

interface GitHubStepProps {
	onStatusChange?: (connected: boolean) => void;
}

export function GitHubStep({ onStatusChange }: GitHubStepProps) {
	const handleStatusChange = useCallback(
		(status: { is_connected: boolean }) => {
			onStatusChange?.(status.is_connected);
		},
		[onStatusChange],
	);

	const github = useGithubOAuth({ onStatusChange: handleStatusChange });

	return (
		<div className='flex flex-col gap-4'>
			<div>
				<h3 className='text-lg font-semibold text-neutral-800'>
					Conecta tu cuenta de GitHub
				</h3>
				<p className='text-neutral-500 text-sm mt-1'>
					Obligatorio. Necesitas conectar GitHub para sincronizar el código de tus
					proyectos.
				</p>
			</div>
			<OAuthIntegration
				label='GitHub'
				icon={<GitHub size={24} color='text-neutral-800' />}
				loading={github.loading}
				actionLoading={github.actionLoading}
				isConnected={github.isConnected}
				username={github.username}
				onConnect={github.handleConnect}
				onDisconnect={github.handleDisconnect}
			/>
		</div>
	);
}
