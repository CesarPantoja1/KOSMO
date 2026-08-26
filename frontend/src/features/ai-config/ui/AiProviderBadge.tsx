'use client';

import { DEFAULT_AI_PROVIDER, useAiConfigStore } from '@/entities/ai-config';

interface AiProviderBadgeProps {
	showLink?: boolean;
	onConfigureClick?: () => void;
}

export function AiProviderBadge({
	showLink = false,
	onConfigureClick,
}: AiProviderBadgeProps) {
	const { config, providers } = useAiConfigStore();

	const isCustom = config?.is_custom ?? false;
	const providerValue = config?.provider ?? DEFAULT_AI_PROVIDER;
	// Obtiene el label del catálogo dinámico; fallback al valor del proveedor
	const providerLabel =
		providers.find((p) => p.value === providerValue)?.label ?? providerValue;

	if (isCustom) {
		return (
			<div className='flex items-center gap-2'>
				<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-success-50 text-success-700 border border-success-500/20'>
					{providerLabel} (Personalizado)
				</span>
				{config?.masked_key && (
					<span className='text-neutral-400 font-mono text-xs'>{config.masked_key}</span>
				)}
			</div>
		);
	}

	return (
		<div className='flex items-center gap-2'>
			<span className='text-xs font-medium px-2.5 py-1 rounded-full bg-neutral-100 text-neutral-600'>
				Proveedor predeterminado
			</span>
			{showLink && onConfigureClick && (
				<button
					type='button'
					onClick={onConfigureClick}
					className='text-xs text-primary-500 hover:text-primary-600 underline transition-colors'
				>
					Configurar IA propia
				</button>
			)}
		</div>
	);
}
