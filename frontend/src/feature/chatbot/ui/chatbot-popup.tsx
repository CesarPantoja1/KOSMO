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

interface ChatbotPopupProps {
	onClose?: () => void;
}

export const ChatbotPopup = ({ onClose }: ChatbotPopupProps) => {
	const { control, handleSubmit } = useForm<RefinementFormData>({
		mode: 'onChange',
		resolver: zodResolver(refinementSchema),
		defaultValues: { instructions: '' },
	});

	const {
		field: { value, onChange, onBlur, ref },
	} = useController({ name: 'instructions', control });

	const [hasSubmitError, setHasSubmitError] = useState(false);

	const charCount = value.length;
	const isOverLimit = charCount > 500;

	const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		onChange(e);
		if (hasSubmitError) setHasSubmitError(false);
	};

	const onSubmit = () => {
		if (charCount === 0 || charCount > 500) {
			setHasSubmitError(true);
			return;
		}
		// TODO: implementar envío
	};

	return (
		<div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50'>
			<div className='absolute bottom-32 right-12  w-105 h-105 rounded-xl bg-base-50 shadow-2xl outline outline-stone-300 flex flex-col overflow-hidden'>
				<div className='w-full p-6 bg-ai border-b border-stone-300 flex justify-between items-center'>
					<h4 className='flex items-center gap-2 text-lg font-medium text-base-50'>
						<Ai size={20} color='text-base-50' />
						Agente de refinamiento
					</h4>

					<button type='button' className='cursor-pointer' onClick={onClose}>
						<Close color='text-base-50' />
					</button>
				</div>

				<form
					onSubmit={handleSubmit(onSubmit)}
					className='flex-1 p-6 flex flex-col gap-6'
				>
					<p className='text-base font-bold text-stone-700'>Instrucciones para la IA</p>

					<div
						className={`
          flex-1
          p-4
          bg-white
          rounded-xl
          outline
          ${hasSubmitError ? 'outline-status-error' : 'outline-neutral-500'}
          focus-within:outline-neutral-500
          flex
          flex-col
        `}
					>
						<textarea
							ref={ref}
							value={value}
							onChange={handleChange}
							onBlur={onBlur}
							placeholder='ej., Haz que la visión del producto sea más concisa y enfócate en los resultados estratégicos'
							className='
            flex-1
            w-full
            resize-none
            overflow-y-auto
            bg-transparent
            outline-none
            border-none
            focus:outline-none
            focus:ring-0
          '
						/>

						<div className='mt-2 flex justify-end'>
							<span
								className={`text-sm font-mono ${isOverLimit ? 'text-status-error' : 'text-base-600'}`}
							>
								{charCount}/500
							</span>
						</div>
					</div>

					<button
						type='submit'
						className='flex items-center justify-center gap-2 rounded-sm bg-ai px-4 py-2 text-base-50 cursor-pointer'
					>
						<Ai size={20} color='text-base-50' />
						Refinar
					</button>
				</form>
			</div>
		</div>
	);
};
