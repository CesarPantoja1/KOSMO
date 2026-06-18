'use client';

import { MarkdownEditor, type MarkdownEditorHandle } from '@/feature';
import { Ai } from '@/shared/ui';
import { useAppStore } from '@/shared/store/app.store';
import { useRef, useState, useEffect } from 'react';
import { getDiscovery, saveDiscovery, generateDiscovery } from '../api/api';
import LoadingDiscovery from './LoadingDiscovery';
import { useRouter } from 'next/navigation';

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const [markdown, setMarkdown] = useState('');
	const currentProject = useAppStore((s) => s.currentProject);
	const [isLoading, setIsLoading] = useState(!!currentProject);
	const [isSaving, setIsSaving] = useState(false);
	const [isGenerating, setIsGenerating] = useState(false);
	const router = useRouter();

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const fetchDiscovery = async () => {
			setIsLoading(true);
			try {
				const data = await getDiscovery(currentProject.id);
				setMarkdown(data.content);
			} catch (err) {
				const errorStatus = err && typeof err === 'object' && 'status' in err ? (err as { status: unknown }).status : undefined;
				const errorMessage = err instanceof Error ? err.message : '';
				if (errorStatus === 404 || errorMessage.includes('404') || errorMessage.includes('no existe')) {
					// No discovery yet
					setMarkdown('## Visión del producto\n\nAún no hay descubrimiento para este proyecto.');
				} else {
					console.error('Error fetching discovery', err);
				}
			} finally {
				setIsLoading(false);
			}
		};

		fetchDiscovery();
	}, [currentProject, router]);

	const handleSave = async () => {
		if (!currentProject) return;
		
		setIsSaving(true);
		try {
			await saveDiscovery(currentProject.id, markdown);
			alert('Guardado exitosamente');
		} catch (err) {
			console.error('Error al guardar', err);
			alert('Error al guardar');
		} finally {
			setIsSaving(false);
		}
	};

	const handleGenerate = async () => {
		if (!currentProject) return;
		
		setIsGenerating(true);
		setIsLoading(true);
		try {
			const data = await generateDiscovery(currentProject.id);
			setMarkdown(data.content);
		} catch (err) {
			console.error('Error al generar', err);
			alert('Error al generar descubrimiento');
		} finally {
			setIsGenerating(false);
			setIsLoading(false);
		}
	};

	return (
		<>
			{isLoading && <LoadingDiscovery />}
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8 p-6'>
				<div className='flex flex-col gap-3'>
					<div className='flex flex-col'>
						<h3 className='text-base-800 text-3xl font-bold'>
							Descripción general del producto
						</h3>
						<p className='text-base-600 mt-2'>
							Visualiza y valida las especificaciones técnicas base de tu proyecto.
						</p>
					</div>
					<div className='flex justify-end gap-3'>
						<button
							className='px-3.5 py-1.5 bg-primary-100 text-base-50 rounded-sm hover:bg-primary-hover disabled:opacity-50'
							onClick={handleSave}
							disabled={isSaving || isGenerating}
						>
							{isSaving ? 'Guardando...' : 'Guardar'}
						</button>

						<button 
							onClick={handleGenerate}
							disabled={isGenerating || isSaving}
							className='flex justify-center items-center px-3.5 py-1.5 gap-3 rounded-sm bg-ai text-base-50 hover:bg-ai-hover disabled:opacity-50'
						>
							<Ai size={20} color='text-base-50' />
							<span className='text-center font-semibold'>
								{isGenerating ? 'Generando...' : 'Generar características'}
							</span>
						</button>
					</div>
				</div>

				{!isLoading && (
					<MarkdownEditor ref={editorRef} markdown={markdown} onChange={setMarkdown} />
				)}
			</div>
		</>
	);
};

export { DiscoveryPage };
