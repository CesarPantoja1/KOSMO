'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { MarkdownEditor } from '@/feature';
import { Ai, ArrowRight, Loading, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';

import type { Characteristic } from '@/entities/characteristic';
import {
	generateCharacteristicRequirements,
	getCharacteristicRequirements,
	getCharacteristics,
	saveCharacteristicRequirements,
} from '@/entities/characteristic';

import { CursorClickFill } from './icons';
import { Requirements } from '@/widgets/main-navbar/ui/icons';

import ModalConfirmLeave from './ModalConfirmLeave';

const RequirementsPage = () => {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isGenerating, setIsGenerating] = useState(false);

	const [markdown, setMarkdown] = useState('');
	const [savedContent, setSavedContent] = useState('');
	const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);

	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const hasRequirements = useAppStore((s) => s.hasRequirements);
	const setHasRequirements = useAppStore((s) => s.setHasRequirements);

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
				const content = await getCharacteristicRequirements(
					projectId,
					characteristicId,
				);
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
		} catch (_err) {
			toast.error('Error al generar los requisitos');
			console.log(_err);
		} finally {
			setIsGenerating(false);
		}
	};

	const handleSave = async () => {
		if (!selectedCharacteristic || !currentProject) return;
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
			toast.success('Requisitos guardados con éxito.');
		} catch (_err) {
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

	if (isLoading) {
		return (
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-6 pt-8 pb-1'>
				<div className='flex justify-between items-start'>
					<div>
						<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>
						<p className='text-base-800 text-lg mt-2'>
							Usa el asistente de IA para desglosar y estructurar los requisitos específicos
							de cada función de la lista.
						</p>
					</div>
					<div className='inline-flex justify-end items-start gap-3 mt-2'>
						<button
							disabled
							className='px-5 py-2 cursor-pointer rounded-sm disabled:opacity-50 bg-base-600 text-base-50 font-medium inline-flex items-center gap-2'
						>
							Guardar
						</button>
						<Link
							href='modelo'
							onClick={(e) => e.preventDefault()}
							className='px-5 py-2 inline-flex gap-2 items-center cursor-pointer text-base-50 bg-ai rounded-sm font-medium'
						>
							Modelado
							<ArrowRight color='text-base-50' size={24} />
						</Link>
					</div>
				</div>

				<div className='flex gap-4 flex-1 min-h-0 pb-4'>
					<div className='w-[22rem] pt-2 bg-base-100/50 rounded-sm flex flex-col gap-3 p-3 animate-pulse'>
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
			{pendingCharSwitch && (
				<ModalConfirmLeave
					onCancel={handleCancelSwitch}
					onConfirm={handleConfirmSwitch}
				/>
			)}

			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{isGenerating && <Loading title='Generando requisitos...' description='Desglosando la característica seleccionada en especificaciones técnicas.' />}

			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-6 pt-8 pb-1'>
				<div className='flex justify-between items-start'>
					<div>
						<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>
						<p className='text-base-800 text-lg mt-2'>
							Usa el asistente de IA para desglosar y estructurar los requisitos específicos
							de cada función de la lista.
						</p>
					</div>
					<div className='inline-flex justify-end items-start gap-3 mt-2'>
						<button
							onClick={handleSave}
							disabled={!selectedCharacteristic || !hasUnsavedChanges}
							className={`px-5 py-2 cursor-pointer rounded-sm disabled:opacity-50 font-medium inline-flex items-center gap-2 ${
								hasUnsavedChanges
									? 'bg-primary-100 text-base-50 hover:bg-primary-100/90'
									: 'bg-base-600 text-base-50'
							}`}
						>
							Guardar
						</button>

						<Link
							href='modelo'
							onClick={handleNextLink('modelo')}
							className='px-5 py-2 inline-flex gap-2 items-center cursor-pointer text-base-50 bg-ai rounded-sm hover:bg-ai/90 transition-colors duration-200 font-medium'
						>
							Modelado
							<ArrowRight color='text-base-50' size={24} />
						</Link>
					</div>
				</div>

				<div className='flex gap-4 flex-1 min-h-0 pb-4'>
					<aside className='w-[22rem] pt-3 bg-base-100/50 rounded-sm flex flex-col'>
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
												<Requirements size={20} color={isSelected ? 'text-primary-100' : 'text-base-600'} />
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
											Comienza a trabajar
										</div>
									</div>
									<div className='self-stretch p-2.5 inline-flex justify-center items-center gap-2.5'>
										<div className='flex-1 text-center justify-start text-base-600 text-lg font-medium'>
											Selecciona una característica del listado lateral para ver su
											detalle
											<br />o generar nuevos requisitos.
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

						{selectedCharacteristic && !isLoadingRequirements && selectedCharacteristic.requirements && (
							<div className='flex flex-col flex-1 min-h-0 gap-4'>
								<div className='flex flex-col gap-2 px-2'>
									<div className='inline-flex justify-start gap-3 items-center'>
										<span className='text-2xl font-bold text-base-800'>
											{selectedCharacteristic.display_id}
										</span>
										<span className='text-2xl font-bold text-primary-100'>
											{selectedCharacteristic.title}
										</span>
									</div>
									<p className='text-base-600 text-base'>
										{selectedCharacteristic.description}
									</p>
								</div>
								<div className='flex-1 min-h-0 mt-2'>
									<MarkdownEditor markdown={markdown} onChange={setMarkdown} />
								</div>
							</div>
						)}

						{selectedCharacteristic && !isLoadingRequirements && !selectedCharacteristic.requirements && (
							<section className='flex flex-col h-full justify-center items-center gap-5 px-20'>
								<Ai color='text-ai' size={70} />

								<span className='text-center justify-start text-base-800 text-2xl font-medium'>
									Sin requisitos generados
								</span>

								<p className='text-base-800 text-lg text-center'>
									Esta característica aún no tiene requisitos asociados. Haz clic en el
									botón <span className='text-xl font-bold'>Generar </span>
									para generarlos automáticamente basados en la descripción.
								</p>

								<button
									onClick={handleGenerate}
									className='px-5 py-2 text-base-50 cursor-pointer bg-ai rounded-sm font-medium mt-2 hover:bg-ai/90 transition-colors'
								>
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
