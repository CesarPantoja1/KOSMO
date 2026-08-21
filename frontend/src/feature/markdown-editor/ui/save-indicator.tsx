'use client';

import { useEffect, useRef } from 'react';
import Load from '@/shared/ui/icons/Load';
import Check from '@/shared/ui/icons/Check';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface Props {
	status: SaveStatus;
	saveMessage?: string;
	savedMessage?: string;
	errorMessage?: string;
}

export function SaveIndicator({
	status,
	saveMessage = 'Guardando...',
	savedMessage = 'Guardado',
	errorMessage = 'No se pudo guardar',
}: Props) {
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const indicatorRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (timerRef.current) {
			clearTimeout(timerRef.current);
			timerRef.current = null;
		}

		const el = indicatorRef.current;
		if (!el) return;

		if (status === 'saved') {
			el.style.opacity = '1';
			el.style.transform = 'scale(1)';
			timerRef.current = setTimeout(() => {
				el.style.opacity = '0';
				el.style.transform = 'scale(0.8)';
			}, 2500);
		} else if (status === 'error') {
			el.style.opacity = '1';
			el.style.transform = 'translateX(0)';
			timerRef.current = setTimeout(() => {
				el.style.opacity = '0';
			}, 4000);
		}

		return () => {
			if (timerRef.current) {
				clearTimeout(timerRef.current);
			}
		};
	}, [status]);

	if (status === 'idle') return null;

	return (
		<div
			ref={indicatorRef}
			className='flex items-center gap-1.5 text-xs transition-all duration-300 ease-out'
			style={{
				opacity: status === 'saving' ? 1 : 0,
				transform: status === 'saving' ? 'none' : undefined,
			}}
		>
			{status === 'saving' && (
				// Al poner el color en este div, tanto el Load como el span se volverán neutrales
				<div className='flex items-center gap-1.5 text-neutral-500'>
					<Load size={14} />
					<span>{saveMessage}</span>
				</div>
			)}

			{status === 'saved' && (
				// Al poner el color en este div, tanto el Check como el span se volverán success
				<div className='flex items-center gap-1.5 text-success-500'>
					<Check size={14} />
					<span>{savedMessage}</span>
				</div>
			)}

			{status === 'error' && (
				<div className='flex items-center gap-1.5'>
					<span className='text-error-500 font-medium'>!</span>
					<span className='text-error-500'>{errorMessage}</span>
				</div>
			)}
		</div>
	);
}
