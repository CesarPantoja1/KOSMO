'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/entities/user';
import { AiConfigTab } from './AiConfigTab';
import { CuentaTab } from './CuentaTab';
import { RootNavbar } from '@/widgets';

type TabType = 'cuenta' | 'ia';

function ProfilePage() {
	const user = useAuthStore((state) => state.user);
	const [activeTab, setActiveTab] = useState<TabType>('cuenta');

	useEffect(() => {
		if (typeof window === 'undefined') return;
		if (!window.opener || window.opener === window) return;

		const params = new URLSearchParams(window.location.search);
		const code = params.get('code');
		const error = params.get('error') || params.get('error_description');
		const state = (params.get('state') || params.get('provider') || '').toLowerCase();

		if (code || error) {
			const type = state === 'railway' ? 'railway-oauth-code' : 'github-oauth-code';
			try {
				if (code) {
					window.opener.postMessage({ type, code }, window.location.origin);
				} else if (error) {
					window.opener.postMessage(
						{ type: 'oauth-error', error },
						window.location.origin,
					);
				}
			} catch {
				// Noop si el opener no está accesible
			}
			window.close();
		}
	}, []);

	return (
		<>
			<RootNavbar />

			<div className='min-h-screen p-6'>
				<div className='max-w-3xl mx-auto'>
					<div className='mb-6'>
						<h1 className='text-2xl font-bold text-neutral-800'>Perfil</h1>
						<p className='text-neutral-500 mt-1'>Gestiona tu cuenta y configuración</p>
					</div>

					<div className='flex gap-1 border-b border-neutral-200 mb-6'>
						<button
							type='button'
							onClick={() => setActiveTab('cuenta')}
							className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
								activeTab === 'cuenta'
									? 'text-primary-500 border-primary-500'
									: 'text-neutral-500 border-transparent hover:text-neutral-700'
							}`}
						>
							Cuenta
						</button>
						<button
							type='button'
							onClick={() => setActiveTab('ia')}
							className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
								activeTab === 'ia'
									? 'text-primary-500 border-primary-500'
									: 'text-neutral-500 border-transparent hover:text-neutral-700'
							}`}
						>
							Inteligencia Artificial
						</button>
					</div>

					{activeTab === 'cuenta' && <CuentaTab user={user} />}
					{activeTab === 'ia' && <AiConfigTab />}
				</div>
			</div>
		</>
	);
}

export { ProfilePage };
