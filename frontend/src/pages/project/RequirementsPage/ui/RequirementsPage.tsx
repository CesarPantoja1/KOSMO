'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ChatbotPopup, MarkdownEditor } from '@/feature';
import { Ai, ArrowRight, Loading, ModalConfirmLeave, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';

import type { Characteristic } from '@/entities/characteristic';
import {
	generateCharacteristicRequirements,
	getCharacteristicRequirements,
	getCharacteristics,
	refineCharacteristicRequirements,
	saveCharacteristicRequirements,
} from '@/entities/characteristic';

import { CursorClickFill } from './icons';
import { Requirements } from '@/widgets/main-navbar/ui/icons';

const RequirementsPage = () => {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isGenerating, setIsGenerating] = useState(false);
	const [isChatbotOpen, setIsChatbotOpen] = useState(false);

	const [markdown, setMarkdown] = useState('');
	const [savedContent, setSavedContent] = useState('');
	const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);
	const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>(
		'idle',
	);

	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const hasRequirements = useAppStore((s) => s.hasRequirements);
	const setHasRequirements = useAppStore((s) => s.setHasRequirements);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);

	const selectedCharacteristic = characteristics.find((c) => c.id === selectedId) ?? null;
	const hasUnsavedChanges = markdown !== savedContent;

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const fetch = async () => {
			setIsLoading(true);
			try {
				const data = await getCharacteristics(currentProject.id);
				setCharacteristics(data);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : 'Error al cargar las características';
				toast.error(message);
			} finally {
				setIsLoading(false);
			}
		};

		fetch();
	}, [currentProject, router]);

	useEffect(() => {
		if (!selectedId || !currentProject) return;

		let cancelled = false;
		const projectId = currentProject.id;
		const characteristicId = selectedId;

		const load = async () => {
			setIsLoadingRequirements(true);
			setMarkdown('');
			setSavedContent('');
			try {
				const content = await getCharacteristicRequirements(projectId, characteristicId);
				if (cancelled) return;
				if (content) {
					setHasRequirements(characteristicId, true);
				}
				setCharacteristics((prev) =>
					prev.map((c) =>
						c.id === characteristicId ? { ...c, requirements: content } : c,
					),
				);
				setMarkdown(content);
				setSavedContent(content);
				setSaveStatus('idle');
			} catch {
				if (!cancelled) toast.error('Error al cargar los requisitos');
			} finally {
				if (!cancelled) setIsLoadingRequirements(false);
			}
		};

		load();

		return () => {
			cancelled = true;
		};
	}, [selectedId, currentProject]);

	const handleSelectCharacteristic = (id: string) => {
		if (id === selectedId) return;
		if (hasUnsavedChanges) {
			setPendingCharSwitch(id);
		} else {
			applySelected(id);
		}
	};

	const applySelected = (id: string) => {
		setSelectedId(id);
		setPendingCharSwitch(null);
	};

	const handleConfirmSwitch = () => {
		if (pendingCharSwitch) applySelected(pendingCharSwitch);
	};

	const handleCancelSwitch = () => {
		setPendingCharSwitch(null);
	};

	const handleGenerate = async () => {
		if (!selectedCharacteristic || !currentProject) return;
		setIsGenerating(true);
		try {
			const content = await generateCharacteristicRequirements(
				currentProject.id,
				selectedCharacteristic.id,
			);
			await saveCharacteristicRequirements(
				currentProject.id,
				selectedCharacteristic.id,
				content,
			);
			if (content) {
				setHasRequirements(selectedCharacteristic.id, true);
			}
			setCharacteristics((prev) =>
				prev.map((c) =>
					c.id === selectedCharacteristic.id ? { ...c, requirements: content } : c,
				),
			);
			setMarkdown(content);
			setSavedContent(content);
			setSaveStatus('idle');
		} catch (_err) {
			toast.error('Error al generar los requisitos');
			console.log(_err);
		} finally {
			setIsGenerating(false);
		}
	};

	const handleRefine = async (instructions: string) => {
		if (!selectedCharacteristic || !currentProject) return;

		try {
			const data = await refineCharacteristicRequirements(
				currentProject.id,
				selectedCharacteristic.id,
				instructions,
			);
			const newContent = data.requirements_markdown;
			setMarkdown(newContent);
			setSavedContent(newContent);
			setCharacteristics((prev) =>
				prev.map((c) =>
					c.id === selectedCharacteristic.id ? { ...c, requirements: newContent } : c,
				),
			);
			toast.success('Requisitos refinados correctamente');
			setIsChatbotOpen(false);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Error al refinar';
			toast.error(errorMessage);
			throw err;
		}
	};

	const handleSave = async () => {
		if (!selectedCharacteristic || !currentProject) return;
		setSaveStatus('saving');
		try {
			await saveCharacteristicRequirements(
				currentProject.id,
				selectedCharacteristic.id,
				markdown,
			);
			if (markdown) {
				setHasRequirements(selectedCharacteristic.id, true);
			}
			setSavedContent(markdown);
			setCharacteristics((prev) =>
				prev.map((c) =>
					c.id === selectedCharacteristic.id ? { ...c, requirements: markdown } : c,
				),
			);
			setSaveStatus('saved');
		} catch (_err) {
			setSaveStatus('error');
			toast.error('Error al guardar los requisitos');
			console.log(_err);
		}
	};

	const handleNextLink = (href: string) => (e: React.MouseEvent) => {
		const { hasUnsavedChanges: unsaved, setPendingNavigationPath: setPath } =
			useAppStore.getState();
		if (unsaved) {
			e.preventDefault();
			setPath(href);
		}
	};

	const confirmLeave = useCallback(() => {
		const path = pendingNavigationPath;
		setPendingNavigationPath(null);
		setHasUnsavedChanges(false);
		if (!path) return;
		router.push(path);
	}, [pendingNavigationPath, setPendingNavigationPath, setHasUnsavedChanges, router]);

	const cancelLeave = useCallback(() => {
		setPendingNavigationPath(null);
	}, [setPendingNavigationPath]);

	useEffect(() => {
		if (hasUnsavedChanges) {
			const handler = (e: BeforeUnloadEvent) => {
				e.preventDefault();
			};
			window.addEventListener('beforeunload', handler);
			return () => window.removeEventListener('beforeunload', handler);
		}
	}, [hasUnsavedChanges]);

	useEffect(() => {
		const handler = () => {
			if (hasUnsavedChanges) {
				setPendingNavigationPath(window.location.href);
			}
		};
		window.addEventListener('popstate', handler);
		return () => window.removeEventListener('popstate', handler);
	}, [hasUnsavedChanges, setPendingNavigationPath]);

	useEffect(() => {
		if (markdown === savedContent) return;

		const timer = setTimeout(() => {
			handleSave();
		}, 3000);

		return () => clearTimeout(timer);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [markdown]);

	if (isLoading) {
		return (
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-6 pt-8 pb-1'>
				<div className='flex flex-col gap-3'>
					<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>
					<p className='text-base-600 text-lg'>
						Usa el asistente de IA para desglosar y estructurar los requisitos específicos
						de cada función de la lista.
					</p>
					<div className='inline-flex justify-end items-start gap-3 text-base-50'>
						<button disabled className='btn text-base-50 disabled:opacity-50 bg-ai'>
							<Ai color='' size={20} />
							Refinar
						</button>


						<Link
							href='modelo'
							aria-disabled
							onClick={(e) => e.preventDefault()}
							className='btn text-base-50 disabled:opacity-50 bg-primary-100 hover:bg-primary-100/90'
						>
							Ir a modelo
							<ArrowRight color='' size={20} />
						</Link>
					</div>
				</div>

				<div className='flex gap-4 flex-1 min-h-0 pb-4'>
					<div className='w-88 pt-2 bg-base-100/50 rounded-sm flex flex-col gap-3 p-3 animate-pulse'>
						<div className='h-7 bg-base-200 rounded w-48' />
						{[1, 2, 3, 4].map((i) => (
							<div key={i} className='h-14 bg-base-200 rounded' />
						))}
					</div>
					<div className='flex-1 bg-base-100/50 rounded-sm animate-pulse' />
				</div>
			</div>
		);
	}

	return (
		<>
			{isChatbotOpen && (
				<ChatbotPopup
					onClose={() => setIsChatbotOpen(false)}
					onSubmitInstructions={handleRefine}
				/>
			)}
			{pendingCharSwitch && (
				<ModalConfirmLeave
					onCancel={handleCancelSwitch}
					onConfirm={handleConfirmSwitch}
				/>
			)}

			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{isGenerating && (
				<Loading
					title='Refinando requisitos EARS...'
					description='Estructurando la característica seleccionada bajo el estándar EARS.'
				/>
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header'>
					<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>
					<p className='text-base-600 text-lg'>
						Usa el asistente de IA para desglosar y estructurar los requisitos específicos
						de cada función de la lista.
					</p>

					{!isEditorMaximized && (
						<div className='inline-flex justify-end items-start gap-3 text-base-50'>
							<button 
								onClick={() => setIsChatbotOpen(true)}
								className='btn text-base-50 bg-ai rounded-sm font-medium cursor-pointer hover:bg-ai/90'
							>
								<Ai color='' size={20} />
								Refinar
							</button>

							<Link
								href='modelo'
								onClick={handleNextLink('modelo')}
								className='btn text-base-50 bg-primary-100 hover:bg-primary-100/90 rounded-sm'
							>
								Ir a modelo
								<ArrowRight color='' size={20} />
							</Link>
						</div>
					)}
				</div>

				<div className='flex gap-4 flex-1 min-h-0 pb-4'>
					<aside className='w-88 pt-3 bg-base-100/50 rounded-sm flex flex-col'>
						<h3 className='text-primary-100 text-lg font-bold px-4 pb-3'>
							Lista de Características
						</h3>

						<div className='flex-1 px-2 flex flex-col gap-1 overflow-y-auto pb-4'>
							{characteristics.length === 0 && (
								<p className='text-base-600 text-sm px-3 py-2'>
									No hay características disponibles.
								</p>
							)}
							{characteristics.map((c) => {
								const isSelected = c.id === selectedId;
								return (
									<button
										key={c.id}
										onClick={() => handleSelectCharacteristic(c.id)}
										className={`w-full p-3 flex justify-start items-start gap-3 text-left cursor-pointer transition-colors ${
											isSelected
												? 'bg-primary-100/10 border-l-4 border-primary-100'
												: 'border-l-4 border-transparent hover:bg-base-200/30'
										}`}
									>
										<span
											className={`text-base font-bold mt-0.5 shrink-0 ${
												isSelected ? 'text-base-800' : 'text-base-800'
											}`}
										>
											{c.display_id}
										</span>
										<p
											className={`flex-1 text-sm font-medium leading-snug pt-0.5 ${
												isSelected ? 'text-primary-100' : 'text-base-600'
											}`}
										>
											{c.title}
										</p>
										{(c.requirements || hasRequirements[c.id]) && (
											<div className='shrink-0 mt-0.5'>
												<Requirements
													size={20}
													color={isSelected ? 'text-primary-100' : 'text-base-600'}
												/>
											</div>
										)}
									</button>
								);
							})}
						</div>
					</aside>

					<div className='flex-1 flex flex-col pl-2 pt-2 bg-base-100/50 min-h-0 overflow-hidden'>
						{!selectedCharacteristic && (
							<div className='flex flex-col items-center justify-center h-full gap-3'>
								<CursorClickFill color='text-base-800' size={70} />
								<div className='self-stretch px-24 flex flex-col justify-start items-start'>
									<div className='self-stretch p-2.5 inline-flex justify-center items-center gap-2.5'>
										<div className='text-center justify-start text-base-800 text-2xl font-semibold'>
											Selecciona una Característica
										</div>
									</div>
									<div className='self-stretch p-2.5 inline-flex justify-center items-center gap-2.5'>
										<div className='flex-1 text-center justify-start text-base-600 text-lg font-medium'>
											Selecciona una característica del listado lateral para ver su
											detalle
											<br />o comenzar a refinar sus requisitos EARS.
										</div>
									</div>
								</div>
							</div>
						)}

						{selectedCharacteristic && isLoadingRequirements && (
							<div className='flex flex-1 items-center justify-center'>
								<span className='text-base-600 text-lg'>Cargando requisitos...</span>
							</div>
						)}

						{selectedCharacteristic &&
							!isLoadingRequirements &&
							selectedCharacteristic.requirements && (
								<div className='flex flex-col flex-1 min-h-0 gap-4'>
									<div className='flex flex-col gap-2 px-2'>
										<div className='inline-flex justify-between items-center w-full'>
											<div className='inline-flex justify-start gap-3 items-center'>
												<span className='text-2xl font-bold text-base-800'>
													{selectedCharacteristic.display_id}
												</span>
												<span className='text-2xl font-bold text-primary-100'>
													{selectedCharacteristic.title}
												</span>
											</div>
											<div className='inline-flex items-center gap-3'>
												{saveStatus === 'saving' && (
													<span className='text-sm font-medium text-base-600 animate-pulse'>
														Guardando...
													</span>
												)}
												{saveStatus === 'saved' && (
													<span className='text-sm font-medium text-status-success'>
														Guardado
													</span>
												)}
												{saveStatus === 'error' && (
													<span className='text-sm font-medium text-status-error'>
														Error al guardar
													</span>
												)}
												{(saveStatus === 'idle' || hasUnsavedChanges) &&
													saveStatus !== 'saving' &&
													saveStatus !== 'error' && (
														<span className='text-sm font-medium text-base-500'>
															{hasUnsavedChanges ? 'Cambios sin guardar' : ''}
														</span>
													)}
											</div>
										</div>
										<p className='text-base-600 text-base'>
											{selectedCharacteristic.description}
										</p>
									</div>
									<div className='flex-1 min-h-0 mt-2'>
										<MarkdownEditor
											markdown={markdown}
											onChange={setMarkdown}
											isMaximized={isEditorMaximized}
											onMaximize={() => setEditorMaximized(true)}
											onMinimize={() => setEditorMaximized(false)}
										/>
									</div>
								</div>
							)}

						{selectedCharacteristic &&
							!isLoadingRequirements &&
							!selectedCharacteristic.requirements && (
								<section className='flex flex-col h-full justify-center items-center gap-5 px-20'>
									<Ai color='text-ai' size={70} />

									<span className='text-center justify-start text-base-800 text-2xl font-medium'>
										Requisitos EARS no refinados
									</span>

									<p className='text-base-800 text-lg text-center'>
										Esta característica aún no tiene requisitos estructurados. Haz clic en
										el botón <span className='text-xl font-bold'>Refinar con IA </span>
										para estructurarlos y completarlos automáticamente bajo el formato
										EARS.
									</p>

									<button
										onClick={handleGenerate}
										className='btn text-base-50 bg-ai mt-2 hover:bg-ai/90'
									>
										<Ai color='' size={20} />
										Generar
									</button>
								</section>
							)}
					</div>
				</div>
			</div>
		</>
	);
};

export { RequirementsPage };
