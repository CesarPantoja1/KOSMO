'use client';

import { useRouter } from 'next/navigation';
import type { User } from '@/entities/user';
import { useGithubOAuth, useRailwayOAuth } from '@/entities/integration';
import { clearAllStores } from '@/features/app-state';
import { GitHub, OAuthIntegration, Railway } from '@/shared/ui';
import { authApi } from '@/shared/api';

type CuentaTabProps = {
	user: User | null;
};

const CuentaTab = ({ user }: CuentaTabProps) => {
	const router = useRouter();
	const displayName = user?.name || user?.email || 'Usuario';
	const initials =
		displayName
			.split(' ')
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0].toUpperCase())
			.join('') || 'U';

	const github = useGithubOAuth();
	const railway = useRailwayOAuth();

	const handleLogout = async () => {
		await authApi.logout();
		clearAllStores();
		router.push('/');
	};

	return (
		<div className='flex flex-col gap-6'>
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
				<div className='flex items-center justify-between mb-5'>
					<h3 className='text-lg font-semibold text-neutral-800'>Información del usuario</h3>
					<button
						type='button'
						onClick={handleLogout}
						className='btn btn-destructive btn-sm'
					>
						Cerrar sesión
					</button>
				</div>
				<div className='flex items-center gap-5'>
					{user?.avatar_url ? (
						// eslint-disable-next-line @next/next/no-img-element
						<img
							src={user.avatar_url}
							alt={displayName}
							className='w-16 h-16 rounded-full object-cover border-2 border-neutral-200 shadow-sm'
						/>
					) : (
						<div className='w-16 h-16 rounded-full bg-primary-500/10 text-primary-600 flex items-center justify-center text-xl font-bold border border-primary-500/20 shadow-sm'>
							{initials}
						</div>
					)}
					<div className='flex flex-col gap-1 min-w-0'>
						<h4 className='text-xl font-bold text-neutral-800 truncate'>{displayName}</h4>
						{user?.email && (
							<p className='text-sm text-neutral-500 truncate'>{user.email}</p>
						)}
					</div>
				</div>
	
			</div>
			<div className='bg-neutral-0 border border-neutral-200 rounded-xl shadow-sm p-6'>
				<h3 className='text-lg font-semibold text-neutral-800 mb-4'>Integraciones</h3>
				<div className='flex flex-col divide-y divide-neutral-100'>
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
					<OAuthIntegration
						label='Railway'
						icon={<Railway size={24} color='text-neutral-800' />}
						loading={railway.loading}
						actionLoading={railway.actionLoading}
						isConnected={railway.isConnected}
						username={railway.username}
						onConnect={railway.handleConnect}
						onDisconnect={railway.handleDisconnect}
					/>
				</div>
			</div>
		</div>
	);
};

export { CuentaTab };
