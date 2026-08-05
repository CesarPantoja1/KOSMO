import { useMemo, type ReactNode } from 'react';
import type { Change } from 'diff';
import { buildPanelLines, type Line, type Segment } from '../lib/computeWordDiff';

interface Props {
	chunks: Change[];
	side: 'left' | 'right';
	className?: string;
}

const HEADING_RE = /^(#{1,6})\s+/;
const INLINE_RE = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(~~(.+?)~~)/g;

function getHeadingLevel(line: Line): number | null {
	const raw = line.map((s) => s.text).join('');
	const match = raw.match(HEADING_RE);
	return match ? match[1].length : null;
}

function stripHeadingFromLine(line: Line, level: number): Line {
	const prefix = '#'.repeat(level) + ' ';
	const result = [...line];
	if (result.length > 0 && result[0].text.startsWith(prefix)) {
		result[0] = { ...result[0], text: result[0].text.slice(prefix.length) };
	}
	return result;
}

function renderInlineMarkdown(text: string): ReactNode[] {
	const nodes: ReactNode[] = [];
	let lastIndex = 0;
	let key = 0;

	for (const match of text.matchAll(INLINE_RE)) {
		if (match.index > lastIndex) {
			nodes.push(<span key={key++}>{text.slice(lastIndex, match.index)}</span>);
		}
		if (match[2]) {
			nodes.push(<strong key={key++}>{match[2]}</strong>);
		} else if (match[4]) {
			nodes.push(<em key={key++}>{match[4]}</em>);
		} else if (match[6]) {
			nodes.push(
				<code key={key++} className='rounded bg-black/5 px-1 font-mono text-[0.9em]'>
					{match[6]}
				</code>,
			);
		} else if (match[8]) {
			nodes.push(<s key={key++}>{match[8]}</s>);
		}
		lastIndex = match.index + match[0].length;
	}

	if (lastIndex < text.length) {
		nodes.push(<span key={key++}>{text.slice(lastIndex)}</span>);
	}

	return nodes.length > 0 ? nodes : [<span key={0}>{text}</span>];
}

function renderSegment(seg: Segment, key: number) {
	const content = renderInlineMarkdown(seg.text);
	if (!seg.highlight) {
		return <span key={key}>{content}</span>;
	}
	return (
		<span
			key={key}
			className='rounded bg-red-100 text-red-700 line-through decoration-red-300'
		>
			{content}
		</span>
	);
}

function renderSegmentAdded(seg: Segment, key: number) {
	const content = renderInlineMarkdown(seg.text);
	if (!seg.highlight) {
		return <span key={key}>{content}</span>;
	}
	return (
		<span key={key} className='rounded bg-green-100 text-green-700'>
			{content}
		</span>
	);
}

function renderLine(line: Line, lineIdx: number, side: 'left' | 'right') {
	if (line.length === 0) {
		return <div key={lineIdx} className='h-4' />;
	}

	const headingLevel = getHeadingLevel(line);
	const processedLine = headingLevel ? stripHeadingFromLine(line, headingLevel) : line;
	const renderSeg = side === 'left' ? renderSegment : renderSegmentAdded;

	const headingClasses: Record<number, string> = {
		1: 'text-2xl font-bold my-2',
		2: 'text-xl font-bold my-1.5',
		3: 'text-lg font-semibold my-1',
	};
	const lineClass = headingLevel
		? headingClasses[headingLevel] ?? 'font-semibold my-1'
		: 'leading-relaxed';

	return (
		<div key={lineIdx} className={lineClass}>
			{processedLine.map((seg, i) => renderSeg(seg, i))}
		</div>
	);
}

export function WordDiffView({ chunks, side, className }: Props) {
	const lines = useMemo(() => buildPanelLines(chunks, side), [chunks, side]);

	return (
		<div className={`px-10 py-20 text-base text-base-900 ${className ?? ''}`}>
			{lines.map((line, i) => renderLine(line, i, side))}
		</div>
	);
}
