'use client';

import { Ai, toast } from '@/shared/ui';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { useController, useForm } from 'react-hook-form';

import { createProject } from '@/entities/project';
import { projectSchema, type ProjectFormData } from '../lib/schema';
import { CharacterCounter } from './CharacterCounter';

const alphaRegex = /[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]/g;

const CreateProjectForm = () => {
	const router = useRouter();
	const setProjectState = useAppStore((s) => s.setProjectState);
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
			<button className='btn btn-ai'>
				<Ai size={20} color='' />
				{isSubmitting ? 'Creando...' : 'Crear Proyecto'}
			</button>
			<div className='flex-1 flex flex-col gap-5 px-8 pt-8 mb-8 rounded-lg shadow-md border border-base-200'>
				<div className='w-full flex flex-col items-start gap-2'>
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
						className='w-full flex items-center px-3.5 py-2 justify-start border border-base-200 rounded-md focus:border-base-300 focus:ring-1 focus:ring-base-300 transition-colors duration-200'
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

				<div className='w-full flex-1 pb-5 flex flex-col gap-2'>
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
						className='w-full flex-1 px-3.5 py-2 border border-base-200 rounded-md focus:border-base-300 focus:ring-1 focus:ring-base-300 transition-colors duration-200 resize-none'
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
