import remarkParse from 'remark-parse';
import { unified } from 'unified';
import { visit } from 'unist-util-visit';
import type { Heading } from 'mdast';

import { HeadingItem } from '../types/heading';

function slugify(text: string) {
	return text
		.toLowerCase()
		.replace(/[^a-z0-9\s-]/g, '')
		.trim()
		.replace(/\s+/g, '-');
}

function extractText(node: { type: string; value?: string; children?: unknown[] }): string {
	if ('value' in node && typeof node.value === 'string') return node.value;
	if ('children' in node && Array.isArray(node.children)) {
		return node.children.map((child) => extractText(child as { type: string; value?: string; children?: unknown[] })).join('');
	}
	return '';
}

export function extractHeadings(markdown: string): HeadingItem[] {
	const tree = unified().use(remarkParse).parse(markdown);

	const headings: HeadingItem[] = [];

	visit(tree, 'heading', (node: Heading) => {
		const text = extractText(node);
		if (!text.trim()) return;

		headings.push({
			id: slugify(text),
			text,
			depth: node.depth,
		});
	});

	return headings;
}
