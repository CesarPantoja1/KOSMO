'use client';

import { useProjectStore } from '@/entities/project/model/store';
import { Ai } from '@/shared/ui';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { useController, useForm } from 'react-hook-form';
import { createProject } from '../api/create-project';
import { projectSchema, type ProjectFormData } from '../lib/schema';
import { CharacterCounter } from './CharacterCounter';

const emojiRegex = /\p{Extended_Pictographic}/gu;

const CreateProjectForm = () => {
	const router = useRouter();
	const setProjectId = useProjectStore((s) => s.setProjectId);
	const [isSubmitting, setIsSubmitting] = useState(false);

	const {
		control,
		handleSubmit,
		formState: { isValid },
	} = useForm<ProjectFormData>({
		mode: 'onBlur',
		resolver: zodResolver(projectSchema),
		defaultValues: { name: '', description: '' },
	});

	const {
		field: { value: nameValue, onChange: nameOnChange, onBlur: nameOnBlur, ref: nameRef },
		fieldState: { error: nameError },
	} = useController({ name: 'name', control });

	const {
		field: { value: descValue, onChange: descOnChange, onBlur: descOnBlur, ref: descRef },
		fieldState: { error: descError },
	} = useController({ name: 'description', control });

	const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		let value = e.target.value;
		value = value.replace(emojiRegex, '');
		if (value.length > 25) {
			value = value.slice(0, 25);
		}
		nameOnChange(value);
	};

	const handleDescChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		let value = e.target.value;
		value = value.replace(emojiRegex, '');
		if (value.length > 1000) {
			value = value.slice(0, 1000);
		}
		descOnChange(value);
	};

	const onSubmit = useCallback(
		async (data: ProjectFormData) => {
			setIsSubmitting(true);
			try {
				const { id } = await createProject(data);
				setProjectId(id);
				router.replace('/proyecto/descubrimiento');
			} catch {
				setIsSubmitting(false);
			}
		},
		[router, setProjectId],
	);

	return (
		<form
			onSubmit={handleSubmit(onSubmit)}
			className='flex-1 min-h-0 flex flex-col gap-2.5'
			noValidate
		>
			<div className='flex justify-end'>
				<button
					disabled={!isValid || isSubmitting}
					className='px-4 py-2 text-base flex items-center rounded-lg min-w-20 cursor-pointer bg-ai text-base-50 hover:bg-ai/90 disabled:cursor-not-allowed disabled:bg-base-600'
				>
					<Ai size={24} color='text-base-50' />
					{isSubmitting ? 'Generando...' : 'Generar Proyecto'}
				</button>
			</div>
			<div className='flex-1 min-h-0 px-8 py-3 rounded-lg shadow-[0px_4px_4px_0px_rgba(0,0,0,0.25)] outline outline-1 outline-base-600 flex flex-col gap-3'>
				<div className='w-full flex flex-col justify-center items-start gap-2.5'>
					<label htmlFor='project-name' className='text-base-800 text-2xl font-semibold'>
						Nombre
					</label>

					<input
						ref={nameRef}
						id='project-name'
						type='text'
						value={nameValue}
						onBlur={nameOnBlur}
						onChange={handleNameChange}
						placeholder='Ej. Ferretería'
						className='w-full flex items-center px-3.5 py-1 justify-start outline-base-100 rounded-sm outline outline-2'
						autoComplete='off'
					/>

					<div className='w-full flex justify-end gap-1 items-center'>
						{nameError && (
							<p className='text-status-error text-sm' role='alert'>
								{nameError.message}
							</p>
						)}
						<CharacterCounter current={nameValue.length} max={25} />
					</div>
				</div>

				<div className='w-full flex-1 pb-5 flex flex-col justify-center items-start gap-2.5'>
					<label
						htmlFor='project-description'
						className='text-base-800 text-2xl font-semibold'
					>
						Descripción
					</label>
					<textarea
						ref={descRef}
						id='project-description'
						value={descValue}
						onBlur={descOnBlur}
						onChange={handleDescChange}
						placeholder='Ej. App para la gestión integral de las sucursales'
						className='w-full flex-1 px-3.5 py-1  rounded-sm outline outline-2  outline-base-100 resize-none'
					/>
					<div className='w-full flex justify-end gap-1 items-center'>
						{descError && (
							<p className='text-status-error text-sm' role='alert'>
								{descError.message}
							</p>
						)}
						<CharacterCounter current={descValue.length} max={1000} />
					</div>
				</div>
			</div>
		</form>
	);
};

export { CreateProjectForm };
