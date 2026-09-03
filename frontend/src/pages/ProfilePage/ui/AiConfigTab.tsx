'use client';

import { useEffect } from 'react';
import { AiConfigForm } from '@/features/ai-config';
import { useAiConfigStore } from '@/entities/ai-config';

export function AiConfigTab() {
	const { fetchConfig } = useAiConfigStore();

	useEffect(() => {
		fetchConfig();
	}, [fetchConfig]);

	return (
		<div className='flex flex-col gap-6'>
			<AiConfigForm onSaved={fetchConfig} />
		</div>
	);
}
