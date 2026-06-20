'use client';

import { MarkdownEditor, type MarkdownEditorHandle } from '@/feature';
import { useAppStore } from 'app/store/app.store';
import { Ai, toast } from '@/shared/ui';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { getDiscovery, saveDiscovery } from '../api/api';
import LoadingDiscovery from './LoadingDiscovery';
import ModalConfimLeave from './ModalConfimLeave';
import Link from 'next/link';

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const [markdown, setMarkdown] = useState('');
	const currentProject = useAppStore((s) => s.currentProject);
	const [isLoading, setIsLoading] = useState(!!currentProject);
	const [isSaving, setIsSaving] = useState(false);
	const savedContentRef = useRef('');
	const router = useRouter();

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);

	const [hasUnsavedChanges, setHasUnsavedChangesLocal] = useState(false);

	useEffect(() => {
		setHasUnsavedChangesLocal(markdown !== savedContentRef.current);
	}, [markdown]);

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

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
				savedContentRef.current = data.content;
			} catch (err) {
				const errorStatus =
					err && typeof err === 'object' && 'status' in err
						? (err as { status: unknown }).status
						: undefined;
				const errorMessage = err instanceof Error ? err.message : '';
				if (
					errorStatus === 404 ||
					errorMessage.includes('404') ||
					errorMessage.includes('no existe')
				) {
					setMarkdown(
						'## Visión del producto\n\nAún no hay descubrimiento para este proyecto.',
					);
					savedContentRef.current = '';
				} else {
					toast.error(errorMessage || 'Error al cargar el descubrimiento');
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
			savedContentRef.current = markdown;
			setHasUnsavedChangesLocal(false);
			toast.success('Cambios guardados con éxito.');
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'No se pudo guardar los cambios';
			toast.error(message);
		} finally {
			setIsSaving(false);
		}
	};

	const handleNextLink = (href: string) => (e: React.MouseEvent) => {
		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			e.preventDefault();
			setPendingNavigationPath(href);
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

	return (
		<>
			{pendingNavigationPath && (
				<ModalConfimLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{isLoading && <LoadingDiscovery />}
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8 pb-4'>
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
							className='px-3.5 py-1.5 cursor-pointer bg-primary-100 text-base-50 rounded-sm hover:bg-primary-100/90 disabled:opacity-50'
							onClick={handleSave}
							disabled={isSaving}
						>
							{isSaving ? 'Guardando...' : 'Guardar'}
						</button>

						<Link
							href='caracteristicas'
							onClick={handleNextLink('caracteristicas')}
							className='flex justify-center cursor-pointer items-center px-3.5 py-1.5 gap-1 rounded-sm bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
						>
							<Ai size={20} color='text-base-50' />
							<span className='text-center font-semibold'> Generar características</span>
						</Link>
					</div>
				</div>

				{!isLoading && (
					<div className='flex-1 min-h-0'>
						<MarkdownEditor ref={editorRef} markdown={markdown} onChange={setMarkdown} />
					</div>
				)}
			</div>
		</>
	);
};

export { DiscoveryPage };
