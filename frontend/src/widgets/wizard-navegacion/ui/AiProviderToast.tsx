'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useAiConfigStore } from '@/entities/ai-config';

export function AiProviderToast() {
	const { config, fetchConfig } = useAiConfigStore();

	useEffect(() => {
		fetchConfig();
	}, [fetchConfig]);

	if (config?.is_custom || config?.has_api_key) {
		return null;
	}

	return (
		<div className='mb-4 flex items-center gap-3 rounded-lg border border-info-200 bg-info-50 px-4 py-3'>
			<svg
				className='h-5 w-5 shrink-0 text-info-600'
				viewBox='0 0 24 24'
				fill='none'
				stroke='currentColor'
				strokeWidth='2'
			>
				<circle cx='12' cy='12' r='9' />
				<path d='M12 8v4M12 16h.01' />
			</svg>
			<p className='text-sm text-info-700'>
				Estás utilizando el proveedor predeterminado de KOSMO.{' '}
				<Link href='/perfil?tab=ia' className='font-medium underline hover:text-info-800 transition-colors'>
					Configura tu propia clave de IA
				</Link>{' '}
				para controlar costos y proveedor.
			</p>
		</div>
	);
}
