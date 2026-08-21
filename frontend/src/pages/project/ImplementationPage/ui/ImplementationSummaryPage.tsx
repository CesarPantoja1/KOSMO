'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
	buildFileTree,
	fetchImplementationFile,
	fetchPreviewUrl,
	useImplementationStore,
} from '@/entities/implementation';
import { useCharacteristicStore } from '@/entities/characteristic';
import { useProjectStore } from '@/entities/project';
import type { FileTreeNode, ImplementationMetric } from '@/entities/implementation';

const iconMap: Record<ImplementationMetric['icon'], React.ReactNode> = {
	screens: (
		<svg
			className='h-5 w-5 text-ai-600'
			viewBox='0 0 24 24'
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
		>
			<rect x='3' y='4' width='18' height='16' rx='2' />
			<path d='M3 9h18M8 14h3M8 17h6' />
		</svg>
	),
	entities: (
		<svg
			className='h-5 w-5 text-primary-600'
			viewBox='0 0 24 24'
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
		>
			<ellipse cx='12' cy='5' rx='7' ry='3' />
			<path d='M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5' />
			<path d='M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7' />
		</svg>
	),
	rules: (
		<svg
			className='h-5 w-5 text-warning-600'
			viewBox='0 0 24 24'
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
		>
			<path d='M13 2L3 14h9l-1 8 10-12h-9l1-8z' />
		</svg>
	),
	integrations: (
		<svg
			className='h-5 w-5 text-primary-600'
			viewBox='0 0 24 24'
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
		>
			<path d='M12 2l3 6 6 .9-4.5 4.4 1 6.2-5.5-3-5.5 3 1-6.2L3 8.9 9 8l3-6z' />
		</svg>
	),
	validations: (
		<svg
			className='h-5 w-5 text-info-700'
			viewBox='0 0 24 24'
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
		>
			<path d='M12 3l8 4v5c0 4.5-3.4 7.8-8 9-4.6-1.2-8-4.5-8-9V7l8-4z' />
			<path d='M9 12l2 2 4-4' />
		</svg>
	),
	actions: (
		<svg
			className='h-5 w-5 text-ai-600'
			viewBox='0 0 24 24'
			fill='none'
			stroke='currentColor'
			strokeWidth='2'
		>
			<path d='M5 4v16M5 8h8M13 8v4M13 12h6M19 12v4M13 16h6' />
		</svg>
	),
};

const folderIcon = (
	<svg
		className='h-4 w-4 shrink-0 text-warning-500'
		viewBox='0 0 24 24'
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z' />
	</svg>
);

const fileIcon = (
	<svg
		className='h-4 w-4 shrink-0 text-neutral-400'
		viewBox='0 0 24 24'
		fill='none'
		stroke='currentColor'
		strokeWidth='2'
	>
		<path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z' />
		<path d='M14 3v5h5' />
	</svg>
);

function FileTree({
	nodes,
	depth = 0,
	onSelect,
}: {
	nodes: FileTreeNode[];
	depth?: number;
	onSelect?: (path: string) => void;
}) {
	return (
		<ul className='space-y-1'>
			{nodes.map((node) => (
				<li key={node.path}>
					{node.children.length === 0 ? (
						<button
							type='button'
							onClick={() => onSelect?.(node.path)}
							className='flex items-center gap-2 rounded px-1 py-0.5 text-left transition-colors hover:bg-neutral-100'
							style={{ paddingLeft: depth * 16 }}
						>
							{fileIcon}
							<span className='font-mono text-xs text-neutral-700'>{node.name}</span>
						</button>
					) : (
						<>
							<div
								className='flex items-center gap-2 px-1 py-0.5'
								style={{ paddingLeft: depth * 16 }}
							>
								{folderIcon}
								<span className='font-mono text-xs font-medium text-neutral-700'>
									{node.name}
								</span>
							</div>
							<FileTree nodes={node.children} depth={depth + 1} onSelect={onSelect} />
						</>
					)}
				</li>
			))}
		</ul>
	);
}

const ImplementationSummaryPage = () => {
	const router = useRouter();
	const summary = useImplementationStore((s) => s.summary);
	const [selectedFile, setSelectedFile] = useState<string | null>(null);
	const [fileContent, setFileContent] = useState<string | null>(null);
	const [fileLoading, setFileLoading] = useState(false);
	const [fileError, setFileError] = useState<string | null>(null);
	const [previewUrl, setPreviewUrl] = useState<string | null>(null);
	const [previewLoading, setPreviewLoading] = useState(false);

	const loadImplementation = useImplementationStore((s) => s.loadImplementation);
	const selectedCharacteristic = useCharacteristicStore(
		(s) => s.currentCharacteristics.find((c) => c.id === s.selectedId) ?? null,
	);

	// Si el resumen no está en el store (recarga de página), se reconstruye desde el servidor.
	useEffect(() => {
		if (summary || !selectedCharacteristic) return;
		loadImplementation(
			selectedCharacteristic.id,
			selectedCharacteristic.title,
			selectedCharacteristic.display_id,
		);
	}, [summary, selectedCharacteristic, loadImplementation]);

	// La vista previa es por proyecto (un puerto propio): se consulta al backend.
	useEffect(() => {
		const project = useProjectStore.getState().currentProject;
		if (!project) return;
		let cancelled = false;
		fetchPreviewUrl(project.id)
			.then((url) => {
				if (!cancelled) setPreviewUrl(url);
			})
			.catch(() => {
				if (!cancelled) setPreviewUrl(null);
			})
			.finally(() => {
				if (!cancelled) setPreviewLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, []);

	const handleSelectFile = async (path: string) => {
		if (!summary) return;
		setSelectedFile(path);
		setFileContent(null);
		setFileError(null);
		setFileLoading(true);
		try {
			const content = await fetchImplementationFile(`impl_${summary.featureId}`, path);
			setFileContent(content);
		} catch (error) {
			setFileError(
				error instanceof Error ? error.message : 'No se pudo leer el archivo.',
			);
		} finally {
			setFileLoading(false);
		}
	};

	if (!summary) {
		return (
			<section className='page-container'>
				<div className='flex flex-col items-center justify-center min-h-[60vh] gap-4'>
					<p className='text-neutral-500'>No hay resumen disponible.</p>
					<Link href='/proyecto/codigo' className='btn btn-secondary'>
						Volver a Implementación
					</Link>
				</div>
			</section>
		);
	}

	return (
		<section className='page-container'>
			<div className='page-header'>
				<div className='flex items-start justify-between gap-4'>
					<div className='flex flex-col gap-1'>
						<h1 className='text-neutral-800 text-lg md:text-xl font-bold'>
							Resumen de implementación
						</h1>
						<p className='text-neutral-500 text-sm md:text-base'>
							Estos son los elementos que forman parte de tu proyecto.
						</p>
					</div>
					<button onClick={() => router.back()} className='btn btn-secondary shrink-0'>
						Volver
					</button>
				</div>

				<div className='grid lg:grid-cols-2 gap-6 mt-6'>
					<div className='flex flex-col gap-6'>
						<div className='grid grid-cols-2 gap-3'>
							{summary.metrics.map((metric) => (
								<div
									key={metric.label}
									className='rounded-lg border border-neutral-100 bg-neutral-50 p-4'
								>
									<div
										className={`mb-3 flex h-9 w-9 items-center justify-center rounded-md ${metric.iconBg}`}
									>
										{iconMap[metric.icon]}
									</div>
									<p className='text-2xl font-bold text-neutral-900'>{metric.value}</p>
									<p className='mt-1 text-xs text-neutral-500'>{metric.label}</p>
								</div>
							))}
						</div>

						<div>
							<h3 className='mb-3 text-sm font-semibold text-neutral-800'>Tecnologías</h3>
							<div className='flex flex-wrap gap-2'>
								{summary.technologies.map((t) => (
									<span
										key={t}
										className='rounded-full bg-neutral-100 px-3 py-1.5 text-xs font-medium text-neutral-700'
									>
										{t}
									</span>
								))}
							</div>
						</div>

						<div>
							<h3 className='mb-3 text-sm font-semibold text-neutral-800'>
								¿Qué puedes hacer ahora?
							</h3>
							<div className='space-y-3'>
								{summary.nextSteps.map((step) => (
									<div key={step} className='flex items-start gap-3'>
										<div className='mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success-50'>
											<svg
												className='h-3.5 w-3.5 text-success-700'
												viewBox='0 0 24 24'
												fill='none'
												stroke='currentColor'
												strokeWidth='3'
											>
												<path d='M5 12l4 4L19 6' />
											</svg>
										</div>
										<p className='text-sm text-neutral-600'>{step}</p>
									</div>
								))}
							</div>
						</div>
					</div>

					<div className='flex flex-col items-center justify-center gap-6 rounded-xl bg-ai-50/40 border border-neutral-200 p-8'>
						<div className='relative mx-auto flex h-36 w-36 items-center justify-center'>
							<div className='absolute inset-4 rounded-2xl bg-ai-100' />
							<div className='relative flex h-20 w-20 items-center justify-center rounded-xl border-2 border-ai-500 bg-neutral-0 shadow-2'>
								<svg
									className='h-10 w-10 text-ai-600'
									viewBox='0 0 24 24'
									fill='none'
									stroke='currentColor'
									strokeWidth='1.7'
								>
									<path d='M8 9l-4 3 4 3M16 9l4 3-4 3M14 6l-4 12' />
								</svg>
							</div>
							<div className='absolute right-1 top-1 flex h-10 w-10 items-center justify-center rounded-full bg-success-500 shadow-2'>
								<svg
									className='h-5 w-5 text-neutral-0'
									viewBox='0 0 24 24'
									fill='none'
									stroke='currentColor'
									strokeWidth='3'
								>
									<path d='M5 12l4 4L19 6' />
								</svg>
							</div>
							<div className='absolute left-0 top-4 text-ai-500'>
								<svg className='h-5 w-5' viewBox='0 0 24 24' fill='currentColor'>
									<path d='M12 1l1.5 6.5L20 9l-6.5 1.5L12 17l-1.5-6.5L4 9l6.5-1.5L12 1z' />
								</svg>
							</div>
							<div className='absolute bottom-3 right-0 text-ai-500'>
								<svg className='h-4 w-4' viewBox='0 0 24 24' fill='currentColor'>
									<path d='M12 2l1.2 8.8L22 12l-8.8 1.2L12 22l-1.2-8.8L2 12l8.8-1.2L12 2z' />
								</svg>
							</div>
						</div>

						<div className='text-center'>
							<h3 className='text-lg font-bold text-neutral-900'>
								¡Tu aplicación está lista!
							</h3>
							<p className='mx-auto mt-2 max-w-xs text-sm text-neutral-500'>
								Hemos generado la estructura y lógica de tu proyecto a partir de todo lo
								que definiste en KOSMO.
							</p>
							{previewLoading ? (
								<button type='button' disabled className='btn btn-primary mt-4'>
									Preparando vista previa...
								</button>
							) : previewUrl ? (
								<a
									href={previewUrl}
									target='_blank'
									rel='noopener noreferrer'
									className='btn btn-primary mt-4'
								>
									Ver aplicación
								</a>
							) : (
								<button type='button' disabled className='btn btn-primary mt-4'>
									Vista previa no disponible
								</button>
							)}
						</div>

						<div className='w-full rounded-lg border border-ai-100 bg-neutral-0 p-4 text-left'>
							<div className='flex gap-3'>
								<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-ai-50'>
									<svg
										className='h-4 w-4 text-ai-600'
										viewBox='0 0 24 24'
										fill='none'
										stroke='currentColor'
										strokeWidth='2'
									>
										<circle cx='12' cy='12' r='9' />
										<path d='M12 11v5M12 8h.01' />
									</svg>
								</div>
								<div>
									<p className='text-sm font-semibold text-neutral-800'>
										¿Qué hemos generado?
									</p>
									<p className='mt-1 text-xs leading-5 text-neutral-500'>
										La estructura, datos, reglas y lógica necesarios para que puedas
										continuar construyendo tu aplicación.
									</p>
								</div>
							</div>
						</div>

						<div className='w-full rounded-lg border border-primary-100 bg-primary-50 p-4 text-left'>
							<div className='flex gap-3'>
								<div className='flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-100'>
									<svg
										className='h-4 w-4 text-primary-600'
										viewBox='0 0 24 24'
										fill='none'
										stroke='currentColor'
										strokeWidth='2'
									>
										<path d='M12 3v18M3 12h18' />
									</svg>
								</div>
								<div>
									<p className='text-sm font-semibold text-primary-900'>
										No necesitas escribir código
									</p>
									<p className='mt-1 text-xs leading-5 text-primary-900/70'>
										KOSMO se encarga de la parte técnica para que puedas enfocarte en tu
										aplicación.
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>
	);
};

export { ImplementationSummaryPage };
