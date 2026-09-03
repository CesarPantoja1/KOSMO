'use client';

import {
	createProject,
	pushProjectToGitHub,
	useProjectStore,
	type Project,
} from '@/entities/project';
import { formatApiError } from '@/shared/api';
import {
	CharacterCounter,
	ConfirmacionVisibilidadRepositorio,
	GitHub,
	InfoCircleIcon,
	Send,
	toast,
	WarningIcon,
} from '@/shared/ui';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useController, useForm } from 'react-hook-form';
import { createProjectSchema, type ProjectFormData } from '../model/types';

const alphaRegex = /[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]/g;

const CreateProjectForm = () => {
	const router = useRouter();
	const setProjectState = useProjectStore((s) => s.setProjectState);
	const projects = useProjectStore((s) => s.projects);
	const getProjects = useProjectStore((s) => s.getProjects);
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [phase, setPhase] = useState<'creating-project' | 'creating-repo' | null>(null);
	const [showPublicConfirm, setShowPublicConfirm] = useState(false);
	const [pendingValues, setPendingValues] = useState<ProjectFormData | null>(null);
	const createdProjectRef = useRef<Project | null>(null);

	useEffect(() => {
		if (projects.length === 0) getProjects();
	}, [projects.length, getProjects]);

	const { control, handleSubmit, setValue, watch } = useForm<ProjectFormData>({
		mode: 'onSubmit',
		resolver: zodResolver(createProjectSchema(projects)),
		defaultValues: {
			name: '',
			description: '',
			repo_name: 'kosmo-repositorio',
			is_public: false,
		},
	});

	const {
		field: { value: nameValue, onChange: nameOnChange, onBlur: nameOnBlur, ref: nameRef },
		fieldState: { error: nameError },
	} = useController({ name: 'name', control });

	const {
		field: { value: descValue, onChange: descOnChange, onBlur: descOnBlur, ref: descRef },
		fieldState: { error: descError },
	} = useController({ name: 'description', control });

	const {
		field: { value: repoNameValue, ref: repoNameRef },
		fieldState: { error: repoNameError },
	} = useController({ name: 'repo_name', control });

	const {
		field: { value: isPublic, onChange: isPublicOnChange },
	} = useController({ name: 'is_public', control });

	const watchedName = watch('name');

	useEffect(() => {
		const repoName = watchedName.trim()
			? `kosmo-${watchedName.toLowerCase().replace(/\s+/g, '-')}`
			: 'kosmo-repositorio';
		setValue('repo_name', repoName);
	}, [watchedName, setValue]);

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

	const doSubmit = async (data: ProjectFormData) => {
		setIsSubmitting(true);
		setPhase('creating-project');
		try {
			const project =
				createdProjectRef.current ??
				(await createProject({ name: data.name, description: data.description }));
			createdProjectRef.current = project;

			setPhase('creating-repo');
			await pushProjectToGitHub(project.id, {
				repo_name: data.repo_name,
				is_public: data.is_public,
			});

			useProjectStore.getState().addProject(project);
			setProjectState(project);
			router.replace('/proyecto/descubrimiento');
		} catch (err) {
			toast.error(formatApiError(err, 'Error al crear el repositorio'));
			setPhase(null);
			setIsSubmitting(false);
		}
	};

	const onSubmit = (data: ProjectFormData) => {
		if (data.is_public) {
			setPendingValues(data);
			setShowPublicConfirm(true);
			return;
		}
		doSubmit(data);
	};

	const handleConfirmPublic = () => {
		setShowPublicConfirm(false);
		if (pendingValues) doSubmit(pendingValues);
	};

	const handleCancelConfirm = () => {
		setShowPublicConfirm(false);
		setPendingValues(null);
		setValue('is_public', false);
	};

	return (
		<>
			<form
				onSubmit={handleSubmit(onSubmit)}
				className='flex-1 flex flex-col gap-5 px-0.5'
				noValidate
			>
				{/* Form card */}
				<div className='flex flex-col px-8 pt-8 pb-6 rounded-xl shadow-sm border border-neutral-200 bg-neutral-0'>
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
							className='w-full min-h-30 px-4 py-3 text-neutral-800 placeholder:text-neutral-400 bg-neutral-50 border border-neutral-300 rounded-md focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none transition-all duration-200 resize-none'
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

					{/* Repository section */}
					<div className='flex flex-col gap-5 pt-4'>
						<div className='flex items-center gap-2'>
							<div className='flex h-8 w-8 items-center justify-center rounded-md bg-neutral-100'>
								<GitHub size={18} color='text-neutral-800' />
							</div>
							<h3 className='text-sm font-semibold text-neutral-800'>
								Repositorio en GitHub
							</h3>
						</div>

						{/* Repo name field */}
						<div className='flex flex-col gap-2'>
							<label
								htmlFor='repo-name'
								className='text-xs font-semibold text-neutral-500 uppercase tracking-wider'
							>
								Nombre del repositorio
							</label>
							<input
								ref={repoNameRef}
								id='repo-name'
								type='text'
								value={repoNameValue}
								readOnly
								disabled
								placeholder='ej. kosmo-gestion-inventarios'
								className='w-full min-h-11 px-4 py-2.5 font-mono text-sm text-neutral-500 bg-neutral-100 border border-neutral-200 rounded-md cursor-not-allowed'
								autoComplete='off'
								maxLength={100}
							/>
							{repoNameError ? (
								<p className='text-error-500 text-xs' role='alert'>
									{repoNameError.message}
								</p>
							) : (
								<p className='text-neutral-400 text-xs'>
									Se genera automáticamente a partir del nombre del proyecto.
								</p>
							)}
						</div>

						{/* Visibility toggle */}
						<div className='flex flex-col gap-2'>
							<span className='text-xs font-semibold text-neutral-500 uppercase tracking-wider'>
								Visibilidad
							</span>
							<div className='flex gap-2'>
								<button
									type='button'
									onClick={() => isPublicOnChange(false)}
									className={`flex-1 rounded-lg border px-4 py-3 text-left transition-all duration-150 ${
										!isPublic
											? 'border-primary-500 bg-primary-50 shadow-sm'
											: 'border-neutral-200 bg-neutral-50 hover:border-neutral-300'
									}`}
								>
									<span
										className={`block text-sm font-semibold ${
											!isPublic ? 'text-primary-600' : 'text-neutral-800'
										}`}
									>
										Privado
									</span>
									<span className='text-xs text-neutral-500'>
										Solo tú y los colaboradores que invites podrán ver el código.
									</span>
								</button>
								<button
									type='button'
									onClick={() => isPublicOnChange(true)}
									className={`flex-1 rounded-lg border px-4 py-3 text-left transition-all duration-150 ${
										isPublic
											? 'border-warning-500 bg-warning-50 shadow-sm'
											: 'border-neutral-200 bg-neutral-50 hover:border-neutral-300'
									}`}
								>
									<span
										className={`block text-sm font-semibold ${
											isPublic ? 'text-warning-600' : 'text-neutral-800'
										}`}
									>
										Público
									</span>
									<span className='text-xs text-neutral-500'>
										Cualquier persona podrá ver el código fuente.
									</span>
								</button>
							</div>
						</div>

						{/* Railway deployment notice */}
						{!isPublic ? (
							<div className='flex items-start gap-3 rounded-lg border border-warning-200 bg-warning-50 px-4 py-3 mt-2'>
								<WarningIcon size={20} color='text-warning-600' />
								<div className='flex flex-col gap-1'>
									<p className='text-sm font-semibold text-warning-700'>
										No podrás desplegar en Railway
									</p>
									<p className='text-sm text-warning-700/80'>
										Los repositorios privados no son compatibles con el despliegue en
										Railway. Si deseas publicar tu aplicación, selecciona la visibilidad{' '}
										<span className='font-semibold'>Pública</span>.
									</p>
								</div>
							</div>
						) : (
							<div className='flex items-start gap-3 rounded-lg border border-info-200 bg-info-50 px-4 py-3 mt-2'>
								<InfoCircleIcon size={20} color='text-info-600' />
								<div className='flex flex-col gap-1'>
									<p className='text-sm font-semibold text-info-700'>
										Despliegue en Railway disponible
									</p>
									<p className='text-sm text-info-700/80'>
										Con un repositorio público podrás publicar tu aplicación en Railway
										directamente desde la plataforma.
									</p>
								</div>
							</div>
						)}
					</div>

					{/* Actions — al final del formulario */}
					<div className='flex items-center justify-end gap-3 pt-2 mt-4'>
						<button
							type='button'
							onClick={() => router.push('/proyecto')}
							className='btn btn-secondary'
						>
							Cancelar
						</button>
						<button type='submit' disabled={isSubmitting} className='btn btn-primary'>
							<Send color='-rotate-45' size={18} />
							{phase === 'creating-project'
								? 'Creando proyecto...'
								: phase === 'creating-repo'
									? 'Creando repositorio...'
									: 'Crear proyecto'}
						</button>
					</div>
				</div>
			</form>

			{showPublicConfirm && pendingValues && (
				<ConfirmacionVisibilidadRepositorio
					repoName={pendingValues.repo_name}
					onCancel={handleCancelConfirm}
					onConfirm={handleConfirmPublic}
					confirmLoading={isSubmitting}
				/>
			)}
		</>
	);
};

export { CreateProjectForm };
