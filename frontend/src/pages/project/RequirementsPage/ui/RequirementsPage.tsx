'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { MarkdownEditor } from '@/feature';
import { Ai, ArrowRight, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';

import type { Characteristic } from '@/entities/characteristic';
import {
	generateCharacteristicRequirements,
	getCharacteristics,
	saveCharacteristicRequirements,
} from '@/entities/characteristic';

import { CursorClickFill } from './icons';
import LoadingRequirements from './LoadingRequirements';
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
	const selectedCharRef = useRef<string | null>(null);

	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);

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
		if (!selectedCharacteristic) return;
		if (selectedCharRef.current === selectedCharacteristic.id) return;
		selectedCharRef.current = selectedCharacteristic.id;
		setMarkdown(selectedCharacteristic.requirements);
		setSavedContent(selectedCharacteristic.requirements);
	}, [selectedCharacteristic]);

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
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
				<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>

				<p className='text-base-800 text-lg'>
					Usa el asistente de IA para desglosar y estructurar los requisitos específicos
					de cada función de la lista.
				</p>

				<div className='inline-flex justify-end items-start gap-2.5'>
					<button
						onClick={handleSave}
						disabled={!selectedCharacteristic || !hasUnsavedChanges}
						className={`px-5 py-1 cursor-pointer rounded-sm disabled:opacity-50 ${
							hasUnsavedChanges
								? 'bg-primary-100 text-base-50'
								: 'bg-base-600 text-base-50'
						}`}
					>
						Guardar
					</button>

					<Link
						href='modelo'
						onClick={handleNextLink('modelo')}
						className='px-5 py-1 inline-flex gap-2.5 cursor-pointer text-base-50 bg-ai rounded-sm hover:bg-ai/90 transition-colors duration-200'
					>
						<ArrowRight color='text-base-50' size={24} />
						Modelado
					</Link>
				</div>
				<div className='flex gap-1 flex-1 min-h-0 pb-4'>
					<div className='w-80 pt-2 bg-base-100/50 rounded-sm flex flex-col gap-3 p-3 animate-pulse'>
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

			{isGenerating && <LoadingRequirements />}

			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8 pb-1'>
				<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>

				<p className='text-base-800 text-lg'>
					Usa el asistente de IA para desglosar y estructurar los requisitos específicos
					de cada función de la lista.
				</p>

				<div className='inline-flex justify-end items-start gap-2.5'>
					<button
						onClick={handleSave}
						disabled={!selectedCharacteristic || !hasUnsavedChanges}
						className={`px-5 py-1 cursor-pointer rounded-sm disabled:opacity-50 ${
							hasUnsavedChanges
								? 'bg-primary-100 text-base-50'
								: 'bg-base-600 text-base-50'
						}`}
					>
						Guardar
					</button>

					<Link
						href='modelo'
						onClick={handleNextLink('modelo')}
						className='px-5 py-1 inline-flex gap-2.5 cursor-pointer text-base-50 bg-ai rounded-sm hover:bg-ai/90 transition-colors duration-200'
					>
						<ArrowRight color='text-base-50' size={24} />
						Modelado
					</Link>
				</div>

				<div className='flex gap-1 flex-1 min-h-0 pb-4'>
					<aside className='w-80 pt-2 bg-base-100/50 rounded-sm inline-flex flex-col justify-start items-start'>
						<h3 className='text-primary-100 text-xl font-semibold px-3 pb-2'>
							Lista de Características
						</h3>

						<div className='self-stretch flex-1 px-1 flex flex-col justify-start items-start gap-1 overflow-y-auto'>
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
										className={`self-stretch p-2.5 inline-flex justify-start items-center gap-2.5 text-left cursor-pointer transition-colors ${
											isSelected
												? 'border-l-4 border-base-950 bg-base-200/50'
												: 'border-l-4 border-transparent hover:bg-base-200/30'
										}`}
									>
										<span
											className={`justify-start text-lg font-medium ${
												isSelected ? 'text-base-950' : 'text-base-600'
											}`}
										>
											{c.code}
										</span>
										<p
											className={`flex-1 justify-start text-base font-normal truncate ${
												isSelected ? 'text-base-950' : 'text-base-600'
											}`}
										>
											{c.title}
										</p>
										{c.requirements && (
											<span className='w-2 h-2 rounded-full bg-status-success shrink-0' />
										)}
									</button>
								);
							})}
						</div>
					</aside>

					<div className='flex-1 flex flex-col gap-5 pl-2.5 pt-2 bg-base-100/50 min-h-0 overflow-hidden'>
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

						{selectedCharacteristic && selectedCharacteristic.requirements && (
							<div className='flex flex-col flex-1 min-h-0 gap-4'>
								<div className='inline-flex justify-start gap-2.5 items-center'>
									<span className='self-stretch text-center justify-center text-lg font-medium leading-8'>
										{selectedCharacteristic.code}
									</span>
									<span className='justify-center text-primary-100 text-lg font-bold'>
										{selectedCharacteristic.title}
									</span>
								</div>
								<p className='text-base-800 text-base'>
									{selectedCharacteristic.description}
								</p>
								<div className='flex-1 min-h-0'>
									<MarkdownEditor markdown={markdown} onChange={setMarkdown} />
								</div>
							</div>
						)}

						{selectedCharacteristic && !selectedCharacteristic.requirements && (
							<section className='flex flex-col h-full justify-center items-center gap-5 px-20'>
								<Ai color='text-ai' size={70} />

								<span className='text-center justify-start text-base-800 text-2xl font-medium'>
									Sin requisitos generados
								</span>

								<p className='text-base-800 text-lg'>
									Esta característica aún no tiene requisitos asociados. Haz clic en el
									botón <span className='text-xl font-bold'>Generar </span>
									para generarlos automáticamente basados en la descripción.
								</p>

								<button
									onClick={handleGenerate}
									className='px-5 py-2 text-base-50 cursor-pointer bg-ai rounded-sm'
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
