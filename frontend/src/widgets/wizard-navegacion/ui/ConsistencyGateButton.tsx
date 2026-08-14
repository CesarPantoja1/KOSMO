'use client';

import { useRouter } from 'next/navigation';
import { useAppStore } from 'app/store/app.store';
import {
	CONSISTENCY_REVIEW_ROUTES,
	firstPhaseToReview,
	sumPhaseStatus,
} from '@/entities/consistency';
import type { ConsistencyStatusResponse } from '@/entities/consistency';

interface ConsistencyGateButtonProps {
	status: ConsistencyStatusResponse | null;
}

export function ConsistencyGateButton({ status }: ConsistencyGateButtonProps) {
	const router = useRouter();

	const pending = sumPhaseStatus(status, 'pending');
	const evaluating = sumPhaseStatus(status, 'evaluating');
	const failed = sumPhaseStatus(status, 'failed');

	if (pending === 0 && evaluating === 0 && failed === 0) return null;

	const goToReview = () => {
		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		const route = CONSISTENCY_REVIEW_ROUTES[firstPhaseToReview(status)];
		if (hasUnsavedChanges) {
			setPendingNavigationPath(route);
		} else {
			router.push(route);
		}
	};

	if (pending > 0) {
		return (
			<button
				type='button'
				onClick={goToReview}
				title='Revisar cambios pendientes'
				className='flex cursor-pointer items-center rounded-full bg-primary-500 px-4 py-1.5 text-sm font-semibold text-neutral-0 transition-colors hover:bg-primary-600'
			>
				Revisar consistencia ({pending})
			</button>
		);
	}

	if (failed > 0) {
		return (
			<button
				type='button'
				onClick={goToReview}
				title='Revisar fallos de evaluación'
				className='flex cursor-pointer items-center rounded-full bg-error-500 px-4 py-1.5 text-sm font-semibold text-neutral-0 transition-colors hover:bg-error-600'
			>
				Fallos de consistencia
			</button>
		);
	}

	return (
		<span className='flex items-center gap-2 rounded-full bg-neutral-100 px-4 py-1.5 text-sm font-medium text-neutral-600'>
			<span className='h-2 w-2 animate-pulse rounded-full bg-warning-500' />
			Analizando consistencia…
		</span>
	);
}
