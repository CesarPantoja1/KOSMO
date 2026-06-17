import { unified } from 'unified';
import remarkParse from 'remark-parse';
import { visit } from 'unist-util-visit';

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

	visit(tree, 'heading', (node: unknown) => {
		const headingNode = node as {
			depth: number;
			children: Array<{ type: string; value?: string }>;
		};
		const text = headingNode.children
			.filter((child) => child.type === 'text')
			.map((child) => child.value || '')
			.join('');

		headings.push({
			id: slugify(text),
			text,
			depth: headingNode.depth,
		});
	});

	return headings;
}
