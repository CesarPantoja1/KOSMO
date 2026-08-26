'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/entities/user';
import { AiConfigForm } from '@/features/ai-config';
import { useAiConfigStore } from '@/entities/ai-config';

export function AiConfigTab() {
	const user = useAuthStore((state) => state.user);
	const { fetchConfig } = useAiConfigStore();
	const subject = user?.subject || 'No disponible';
	const scopes = user?.scopes || [];

	useEffect(() => {
		fetchConfig();
	}, [fetchConfig]);

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

			<AiConfigForm onSaved={fetchConfig} />
		</div>
	);
}
