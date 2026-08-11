'use client';

import { Ai, CharacterCounter, toast } from '@/shared/ui';
import { zodResolver } from '@hookform/resolvers/zod';
import { useProjectStore } from '@/entities/project';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { useController, useForm } from 'react-hook-form';

import { createProject } from '@/entities/project';
import { projectSchema, type ProjectFormData } from '../model/types';

const alphaRegex = /[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]/g;

const CreateProjectForm = () => {
	const router = useRouter();
	const setProjectState = useProjectStore((s) => s.setProjectState);
	const [isSubmitting, setIsSubmitting] = useState(false);

	const {
		control,
		handleSubmit,
		formState: { isValid },
	} = useForm<ProjectFormData>({
		mode: 'onSubmit',
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
		value = value.replace(alphaRegex, '');
		if (value.length > 25) {
			value = value.slice(0, 25);
		}
		nameOnChange(value);
	};

	const handleDescChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		let value = e.target.value;
		if (value.length > 1000) {
			value = value.slice(0, 1000);
		}
		descOnChange(value);
	};

	const onSubmit = useCallback(
		async (data: ProjectFormData) => {
			setIsSubmitting(true);
			try {
				const project = await createProject(data);
				useProjectStore.getState().addProject(project);
				setProjectState(project);
				router.replace('/proyecto/descubrimiento');
			} catch (err) {
				const message = err instanceof Error ? err.message : 'Error al crear el proyecto';
				toast.error(message);
				setIsSubmitting(false);
			}
		},
		[router, setProjectState],
	);

	return (
		<form
			onSubmit={handleSubmit(onSubmit)}
			className='flex-1 flex flex-col gap-5 px-0.5'
			noValidate
		>
			{/* Form card */}
			<div className='flex flex-col gap-6 px-8 pt-8 pb-6 rounded-xl shadow-sm border border-neutral-200 bg-neutral-0'>
				{/* Name field */}
				<div className='flex flex-col gap-2'>
					<label
						htmlFor='project-name'
						className='text-xs font-semibold text-neutral-500 uppercase tracking-wider'
					>
						Nombre del proyecto
					</label>
					<input
						ref={nameRef}
						id='project-name'
						type='text'
						value={nameValue}
						onBlur={nameOnBlur}
						onChange={handleNameChange}
						placeholder='Ej. Ferretería'
						className='w-full min-h-11 px-4 py-2.5 text-neutral-800 placeholder:text-neutral-400 bg-neutral-50 border border-neutral-300 rounded-md focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none transition-all duration-200'
						autoComplete='off'
					/>
					<div className='flex justify-between items-center gap-2'>
						{nameError ? (
							<p className='text-error-500 text-xs' role='alert'>
								{nameError.message}
							</p>
						) : (
							<span />
						)}
						<CharacterCounter current={nameValue.length} max={25} />
					</div>
				</div>

				{/* Description field */}
				<div className='flex flex-col gap-2'>
					<label
						htmlFor='project-description'
						className='text-xs font-semibold text-neutral-500 uppercase tracking-wider'
					>
						Descripción
					</label>
					<textarea
						ref={descRef}
						id='project-description'
						value={descValue}
						onBlur={descOnBlur}
						onChange={handleDescChange}
						placeholder='Describe el problema de negocio que quieres resolver...'
						className='w-full min-h-40 px-4 py-3 text-neutral-800 placeholder:text-neutral-400 bg-neutral-50 border border-neutral-300 rounded-md focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none transition-all duration-200 resize-none'
					/>
					<div className='flex justify-between items-center gap-2'>
						{descError ? (
							<p className='text-error-500 text-xs' role='alert'>
								{descError.message}
							</p>
						) : (
							<span />
						)}
						<CharacterCounter current={descValue.length} max={1000} />
					</div>
				</div>

				{/* Actions — al final del formulario */}
				<div className='flex items-center justify-end gap-3 pt-2 border-t border-neutral-100'>
					<button
						type='button'
						onClick={() => router.push('/proyecto')}
						className='btn btn-secondary'
					>
						Cancelar
					</button>
					<button type='submit' disabled={isSubmitting} className='btn btn-ai'>
						<Ai size={18} color='' />
						{isSubmitting ? 'Creando proyecto...' : 'Crear proyecto'}
					</button>
				</div>
			</div>
		</form>
	);
};

export { CreateProjectForm };
