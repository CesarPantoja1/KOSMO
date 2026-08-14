'use client';

import { useEffect, useId, useRef } from 'react';

interface Props {
	onCancel: () => void;
	onConfirm: () => void;
	title?: string;
	description?: string;
	cancelText?: string;
	confirmText?: string;
}

const ModalConfirm = ({
	onCancel,
	onConfirm,
	title = 'Cambios sin guardar',
	description = 'Si sale ahora, perderá las modificaciones recientes.',
	cancelText = 'Cancelar',
	confirmText = 'Aceptar',
}: Props) => {
	const titleId = useId();
	const confirmRef = useRef<HTMLButtonElement>(null);

	useEffect(() => {
		confirmRef.current?.focus();
	}, []);

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Escape') {
				onCancel();
			}
		};
		document.addEventListener('keydown', handleKeyDown);
		return () => document.removeEventListener('keydown', handleKeyDown);
	}, [onCancel]);

	return (
		<div className='warning-popup' onClick={onCancel}>
			<div
				role='dialog'
				aria-modal='true'
				aria-labelledby={titleId}
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-10 w-full max-w-md mx-4 border border-neutral-200'
				onClick={(e) => e.stopPropagation()}
			>
				<h3
					id={titleId}
					className='text-lg font-semibold text-neutral-800 mb-2 text-center'
				>
					{title}
				</h3>
				<p className='text-neutral-500 text-sm text-center mb-6'>{description}</p>
				<div className='flex justify-center gap-3 mt-6'>
					<button type='button' className='btn btn-secondary' onClick={onCancel}>
						{cancelText}
					</button>
					<button
						type='button'
						ref={confirmRef}
						className='btn btn-primary'
						onClick={onConfirm}
					>
						{confirmText}
					</button>
				</div>
			</div>
		</div>
	);
};

export { ModalConfirm };
