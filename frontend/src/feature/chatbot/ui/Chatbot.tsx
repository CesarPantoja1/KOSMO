'use client';

import { useState } from 'react';
import { useController, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Ai, Close } from '@/shared/ui';

const refinementSchema = z.object({
	instructions: z.string().max(500, 'Máximo 500 caracteres'),
});

type RefinementFormData = z.infer<typeof refinementSchema>;

interface Props {
	placeholder: string;
	onClose?: () => void;
	onSubmitInstructions?: (instructions: string) => Promise<void>;
}

export const Chatbot = ({ onClose, onSubmitInstructions, placeholder }: Props) => {
	const { control, handleSubmit } = useForm<RefinementFormData>({
		mode: 'onChange',
		resolver: zodResolver(refinementSchema),
		defaultValues: { instructions: '' },
	});

	const {
		field: { value, onChange, onBlur, ref },
	} = useController({ name: 'instructions', control });

	const [hasSubmitError, setHasSubmitError] = useState(false);
	const [errorMessage, setErrorMessage] = useState('');
	const [isSubmitting, setIsSubmitting] = useState(false);

	const charCount = value.length;
	const isOverLimit = charCount > 500;

	const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		onChange(e);
		if (hasSubmitError) {
			setHasSubmitError(false);
			setErrorMessage('');
		}
	};

	const onSubmit = async () => {
		const trimmed = value.trim();
		if (trimmed.length === 0 || charCount > 500) {
			setHasSubmitError(true);
			setErrorMessage(
				trimmed.length === 0
					? 'La instrucción no puede estar vacía'
					: 'Máximo 500 caracteres',
			);
			return;
		}

		if (!onSubmitInstructions) return;

		setIsSubmitting(true);
		try {
			await onSubmitInstructions(value);
		} catch (error) {
			console.error(error);
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<div className='flex h-full w-full flex-col overflow-hidden bg-base-50'>
			{/* Header */}
			<header className='flex items-center justify-between border-b border-stone-300 bg-ai px-5 py-4'>
				<div className='flex items-center gap-2'>
					<Ai size={20} color='text-base-50' />
					<div>
						<h3 className='font-semibold text-base-50'>Agente de refinamiento</h3>

						<p className='text-xs text-base-100'>Asistente IA</p>
					</div>
				</div>

				<button type='button' onClick={onClose} className='rounded p-1 hover:bg-white/10'>
					<Close color='text-base-50' />
				</button>
			</header>

			{/* Mensajes */}
			<div className='flex-1 overflow-y-auto px-5 py-5 space-y-5'>
				{/* IA */}
				<div className='flex items-start gap-3'>
					<div className='flex h-8 w-8 items-center justify-center rounded-full bg-ai'>
						<Ai size={16} color='text-base-50' />
					</div>

					<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3'>
						<p className='text-sm leading-6 text-stone-700'>
							Hola 👋. Indícame qué parte del documento deseas modificar y te ayudaré a
							refinarla.
						</p>
					</div>
				</div>

				{/* Usuario */}
				<div className='flex justify-end'>
					<div className='max-w-[85%] rounded-2xl rounded-br-sm bg-ai px-4 py-3'>
						<p className='text-sm leading-6 text-base-50'>
							Quiero que los requisitos sean más específicos.
						</p>
					</div>
				</div>

				{/* IA */}
				<div className='flex items-start gap-3'>
					<div className='flex h-8 w-8 items-center justify-center rounded-full bg-ai'>
						<Ai size={16} color='text-base-50' />
					</div>

					<div className='max-w-[85%] rounded-2xl rounded-tl-sm bg-stone-100 px-4 py-3'>
						<p className='text-sm leading-6 text-stone-700'>
							Puedo ayudarte con eso. ¿Deseas que utilice lenguaje EARS o requisitos
							tradicionales?
						</p>
					</div>
				</div>
			</div>

			{/* Input */}
			<form
				onSubmit={handleSubmit(onSubmit)}
				className='border-t border-stone-300 bg-white p-4'
			>
				<div
					className={`
				rounded-xl border bg-base-50 p-3 transition-all
				${hasSubmitError ? 'border-status-error' : 'border-stone-300 focus-within:border-ai'}
			`}
				>
					<textarea
						ref={ref}
						value={value}
						onChange={handleChange}
						onBlur={onBlur}
						placeholder={placeholder}
						maxLength={500}
						disabled={isSubmitting}
						className='
					min-h-24
					max-h-52
					w-full
					resize-none
					bg-transparent
					outline-none
				'
					/>

					<div className='mt-3 flex items-center justify-between'>
						{hasSubmitError ? (
							<p className='text-xs text-status-error'>{errorMessage}</p>
						) : (
							<span />
						)}

						<span
							className={`text-xs ${
								isOverLimit ? 'text-status-error' : 'text-stone-500'
							}`}
						>
							{charCount}/500
						</span>
					</div>
				</div>

				<button
					type='submit'
					disabled={isSubmitting || value.trim().length === 0 || isOverLimit}
					className='
				mt-4
				flex
				w-full
				items-center
				justify-center
				gap-2
				rounded-lg
				bg-ai
				px-4
				py-3
				font-medium
				text-base-50
				transition-colors
				hover:opacity-90
				disabled:cursor-not-allowed
				disabled:opacity-50
			'
				>
					<Ai size={18} color='text-base-50' />

					{isSubmitting ? 'Pensando...' : 'Enviar'}
				</button>
			</form>
		</div>
	);
};
