import remarkParse from 'remark-parse';
import { unified } from 'unified';
import { visit } from 'unist-util-visit';
import type { Heading, Text } from 'mdast';

import { HeadingItem } from '../types/heading';

function slugify(text: string) {
	return text
		.toLowerCase()
		.replace(/[^a-z0-9\s-]/g, '')
		.trim()
		.replace(/\s+/g, '-');
}

export function extractHeadings(markdown: string): HeadingItem[] {
	const tree = unified().use(remarkParse).parse(markdown);

	const headings: HeadingItem[] = [];

	visit(tree, 'heading', (node: Heading) => {
		const text = node.children
			.filter((child): child is Text => child.type === 'text')
			.map((child) => child.value)
			.join('');

		headings.push({
			id: slugify(text),
			text,
			depth: node.depth,
		});
	});

	return headings;
}
