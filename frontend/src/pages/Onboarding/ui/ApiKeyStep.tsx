'use client';

import { AiConfigForm } from '@/features/ai-config';
import { useAiConfigStore } from '@/entities/ai-config';
import { useEffect } from 'react';

interface ApiKeyStepProps {
	onComplete?: () => void;
}

export function ApiKeyStep({ onComplete }: ApiKeyStepProps) {
	const { fetchConfig } = useAiConfigStore();

	useEffect(() => {
		fetchConfig();
	}, [fetchConfig]);

	return (
		<div className='flex flex-col gap-4'>
			<AiConfigForm onSaved={onComplete} embedded />
		</div>
	);
}
