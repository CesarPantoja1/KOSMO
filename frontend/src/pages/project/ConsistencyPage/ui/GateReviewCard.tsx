'use client';

import type { ReviewCard } from '@/entities/consistency';
import { PlantUmlViewer } from '@/feature/plantuml-viewer';
import { wrapPlantUmlSource } from '@/feature/plantuml-viewer/lib/wrap-plantuml';
import { MarkdownText } from '@/shared/ui/markdown-text';
import { useEffect, useRef, useState } from 'react';

const ACTION_LABELS: Record<string, string> = {
	update: 'Actualizar',
	create: 'Crear',
	delete: 'Eliminar',
	new: 'Nuevo',
};

const ACTION_STYLES: Record<string, string> = {
	update: 'bg-primary-50 text-primary-600',
	create: 'bg-neutral-100 text-neutral-600',
	delete: 'bg-error-50 text-error-600',
	new: 'bg-neutral-100 text-neutral-600',
};

interface GateReviewCardProps {
	card: ReviewCard;
	busy: boolean;
	onApply: () => void;
	onDiscard: () => void;
}

function DiagramDiffPane({
	source,
	fragment,
	hasFullDiagram,
}: {
	source: string;
	fragment: string;
	hasFullDiagram: boolean;
}) {
	const containerRef = useRef<HTMLDivElement>(null);
	const [visible, setVisible] = useState(
		() => typeof IntersectionObserver === 'undefined',
	);

	useEffect(() => {
		if (visible) return;
		const el = containerRef.current;
		if (!el) return;
		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) {
						setVisible(true);
						observer.disconnect();
					}
				}
			},
			{ rootMargin: '200px' },
		);
		observer.observe(el);
		return () => observer.disconnect();
	}, [visible]);

	if (!visible) {
		return (
			<div ref={containerRef} className='py-3 text-center text-[11px] text-neutral-400'>
				Preparando diagrama…
			</div>
		);
	}

	return (
		<PlantUmlViewer
			source={source}
			showControls={hasFullDiagram}
			fallbackContent={fragment}
		/>
	);
}

export const GateReviewCard = ({ card, busy, onApply, onDiscard }: GateReviewCardProps) => {
	const [showFullRationale, setShowFullRationale] = useState(false);
	const actionLabel = ACTION_LABELS[card.action] ?? card.action;
	const actionStyles = ACTION_STYLES[card.action] ?? ACTION_STYLES.update;

	const before = card.diff?.before ?? '';
	const after = card.diff?.after ?? '';
	const beforeDiagram = card.diff?.before_diagram ?? '';
	const afterDiagram = card.diff?.after_diagram ?? '';
	const hasDiff = before !== '' || after !== '';
	const isDeletion = after === '' && before !== '';
	const isDiagram = card.artifact_type === 'ActivityDiagram';

	const renderDiffContent = (fragment: string, fullDiagram: string) => {
		if (!isDiagram) {
			return <MarkdownText content={fragment} />;
		}
		const source = fullDiagram.trim() ? fullDiagram : wrapPlantUmlSource(fragment);
		return (
			<DiagramDiffPane
				source={source}
				fragment={fragment}
				hasFullDiagram={Boolean(fullDiagram.trim())}
			/>
		);
	};

	return (
		<article className='flex flex-col gap-3 rounded-lg border border-neutral-200 bg-neutral-0 p-4 shadow-sm'>
			<header className='flex flex-wrap items-center justify-between gap-2'>
				<div className='flex items-center gap-2 min-w-0'>
					<span className='rounded-md bg-neutral-100 px-2 py-0.5 font-mono text-xs font-semibold text-neutral-700'>
						{card.target_display_id || card.target_artifact_id}
					</span>
					<h3 className='truncate text-sm font-semibold text-neutral-800'>
						{card.target_title}
					</h3>
				</div>
				<span
					className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${actionStyles}`}
				>
					{actionLabel}
				</span>
			</header>

			{card.rationale && (
				<p
					className={`text-sm leading-6 text-neutral-600 ${
						showFullRationale ? '' : 'line-clamp-2'
					}`}
				>
					{card.rationale}
					{card.rationale.length > 150 && (
						<button
							type='button'
							onClick={() => setShowFullRationale((v) => !v)}
							className='ml-1 cursor-pointer text-xs font-medium text-ai-600 hover:underline'
						>
							{showFullRationale ? 'Ver menos' : 'Ver más'}
						</button>
					)}
				</p>
			)}

			{hasDiff && (
				<div className='flex flex-col gap-1.5 overflow-hidden rounded-md border border-neutral-200 text-xs'>
					{isDeletion && (
						<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
							<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
								- Eliminar
							</div>
							{renderDiffContent(before, beforeDiagram)}
						</div>
					)}
					{before !== '' && !isDeletion && (
						<div className='border-l-2 border-error-500 bg-error-50 p-2.5 text-error-700 [&_pre]:!bg-error-50 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
							<div className='mb-1 font-mono text-[10px] font-semibold text-error-500 uppercase tracking-wider'>
								- Anterior
							</div>
							{renderDiffContent(before, beforeDiagram)}
						</div>
					)}
					{!isDeletion && after !== '' && (
						<div className='border-l-2 border-primary-500 bg-primary-50 p-2.5 text-primary-900 [&_pre]:!bg-primary-100 [&_code]:!bg-transparent [&_pre]:my-1 [&_p]:my-0.5'>
							<div className='mb-1 font-mono text-[10px] font-semibold text-primary-500 uppercase tracking-wider'>
								+ Propuesto
							</div>
							{renderDiffContent(after, afterDiagram)}
						</div>
					)}
				</div>
			)}

			{card.status === 'failed' && card.failure_reason && (
				<p className='rounded-md bg-error-50 px-3 py-2 text-xs text-error-700'>
					{card.failure_reason}
				</p>
			)}

			<footer className='flex items-center justify-end gap-2'>
				<button
					type='button'
					onClick={onDiscard}
					disabled={busy}
					className='btn btn-secondary btn-sm disabled:opacity-60'
				>
					Descartar
				</button>
				<button
					type='button'
					onClick={onApply}
					disabled={busy}
					className='btn btn-primary btn-sm disabled:opacity-60'
				>
					{busy ? 'Aplicando…' : 'Aplicar'}
				</button>
			</footer>
		</article>
	);
};
