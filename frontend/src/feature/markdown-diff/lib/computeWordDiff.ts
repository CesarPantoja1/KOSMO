import { diffWords } from 'diff';

export type { Change } from 'diff';

export interface Segment {
	text: string;
	highlight: boolean;
}

export type Line = Segment[];

export function computeWordDiff(original: string, proposal: string) {
	return diffWords(original, proposal);
}

export function buildPanelLines(chunks: { value: string; added?: boolean; removed?: boolean }[], side: 'left' | 'right'): Line[] {
	const lines: Line[] = [[]];

	for (const chunk of chunks) {
		const isRelevant = side === 'left' ? !chunk.added : !chunk.removed;
		if (!isRelevant) continue;

		const highlight = side === 'left' ? !!chunk.removed : !!chunk.added;
		const parts = chunk.value.split('\n');

		for (let i = 0; i < parts.length; i++) {
			if (i > 0) lines.push([]);
			if (parts[i]) {
				lines[lines.length - 1].push({ text: parts[i], highlight });
			}
		}
	}

	return lines;
}
