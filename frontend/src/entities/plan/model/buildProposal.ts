import type { PlanChange } from './types';

const FUTURE_HINTS = [
	'futur',
	'no contempl',
	'pendiente',
	'proxim',
	'roadmap',
	'potencial',
	'fuera de alcance',
	'no incluido',
	'a considerar',
];

interface HeadingMatch {
	start: number;
	end: number;
	text: string;
}

function normalize(text: string): string {
	return text.replace(/\s+/g, '').toLowerCase();
}

function findAllHeadings(markdown: string): HeadingMatch[] {
	const matches: HeadingMatch[] = [];
	const re = /^(#{1,6})\s+(.+)$/gm;
	let m: RegExpExecArray | null;
	while ((m = re.exec(markdown)) !== null) {
		matches.push({ start: m.index, end: m.index + m[0].length, text: m[2] });
	}
	return matches;
}

function findSectionRange(markdown: string, sectionName: string): { start: number; end: number } | null {
	const allHeadings = findAllHeadings(markdown);
	const normalizedQuery = normalize(sectionName);

	for (let i = 0; i < allHeadings.length; i++) {
		const normalizedHeading = normalize(allHeadings[i].text);
		if (normalizedHeading === normalizedQuery || normalizedHeading.includes(normalizedQuery)) {
			const start = allHeadings[i].start;
			const end = i + 1 < allHeadings.length ? allHeadings[i + 1].start : markdown.length;
			return { start, end };
		}
	}
	return null;
}

function findFutureBoundary(sectionMd: string): number | null {
	const re = /^(#{1,6})\s+(.+)$/gm;
	const headings: HeadingMatch[] = [];
	let m: RegExpExecArray | null;
	while ((m = re.exec(sectionMd)) !== null) {
		headings.push({ start: m.index, end: m.index + m[0].length, text: m[2] });
	}
	for (let i = 1; i < headings.length; i++) {
		const headingText = normalize(headings[i].text);
		if (FUTURE_HINTS.some((hint) => headingText.includes(hint))) {
			const boundary = sectionMd.lastIndexOf('\n\n', headings[i].start);
			return boundary >= 0 ? boundary : headings[i].start;
		}
	}
	return null;
}

function insertInSection(
	markdown: string,
	secStart: number,
	secEnd: number,
	content: string,
): string {
	const sectionMd = markdown.slice(secStart, secEnd);
	const re = /^(#{1,6})\s+(.+)$/gm;
	const headings: HeadingMatch[] = [];
	let m: RegExpExecArray | null;
	while ((m = re.exec(sectionMd)) !== null) {
		headings.push({ start: m.index, end: m.index + m[0].length, text: m[2] });
	}

	if (headings.length >= 3) {
		let insertPos = findFutureBoundary(sectionMd);
		if (insertPos === null) {
			const lastHeading = headings[headings.length - 1];
			const pos = sectionMd.lastIndexOf('\n\n', lastHeading.start);
			insertPos = pos >= 0 ? pos : lastHeading.start;
		}
		const head = markdown.slice(secStart, secStart + insertPos).replace(/\s+$/, '');
		const tail = markdown.slice(secStart + insertPos, secEnd).replace(/^\n+/, '');
		return (
			markdown.slice(0, secStart) +
			head +
			'\n' +
			content.trim() +
			'\n\n' +
			tail +
			markdown.slice(secEnd)
		);
	}

	const head = markdown.slice(0, secEnd).replace(/\s+$/, '');
	const tail = markdown.slice(secEnd).replace(/^\n+/, '');
	return head + '\n' + content.trim() + '\n\n' + tail;
}

export function buildProposal(original: string, changes: PlanChange[]): string {
	let result = original;
	for (const change of changes) {
		if (change.diff.before && result.includes(change.diff.before)) {
			result = result.replace(change.diff.before, change.diff.after);
		} else if (!change.diff.before && change.diff.after) {
			if (change.section) {
				const range = findSectionRange(result, change.section);
				if (range) {
					result = insertInSection(result, range.start, range.end, change.diff.after);
				} else {
					result += '\n\n' + change.diff.after;
				}
			} else {
				result += '\n\n' + change.diff.after;
			}
		}
	}
	return result;
}
