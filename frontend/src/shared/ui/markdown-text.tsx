'use client';

import type { ListItem, PhrasingContent, Root, RootContent } from 'mdast';
import { memo, useMemo, type ReactNode } from 'react';
import remarkParse from 'remark-parse';
import { unified } from 'unified';

const parser = unified().use(remarkParse);

function renderInline(node: PhrasingContent, key: number): ReactNode {
	switch (node.type) {
		case 'text':
			return node.value;
		case 'strong':
			return <strong key={key}>{renderInlines(node.children)}</strong>;
		case 'emphasis':
			return <em key={key}>{renderInlines(node.children)}</em>;
		case 'delete':
			return <s key={key}>{renderInlines(node.children)}</s>;
		case 'inlineCode':
			return (
				<code key={key} className='rounded bg-black/5 px-1'>
					{node.value}
				</code>
			);
		case 'break':
			return <br key={key} />;
		case 'link':
			return (
				<a
					key={key}
					href={node.url}
					target='_blank'
					rel='noreferrer'
					className='underline'
				>
					{renderInlines(node.children)}
				</a>
			);
		case 'image':
			return node.alt ?? '';
		case 'html':
			return node.value;
		default:
			return null;
	}
}

function renderInlines(nodes: PhrasingContent[]): ReactNode {
	return nodes.map((node, i) => renderInline(node, i));
}

function renderListItem(item: ListItem, key: number): ReactNode {
	return (
		<li key={key}>
			{item.children.map((child, i) =>
				child.type === 'paragraph'
					? renderInlines(child.children)
					: renderBlock(child, i),
			)}
		</li>
	);
}

function renderBlock(node: RootContent, key: number): ReactNode {
	switch (node.type) {
		case 'paragraph':
			return <p key={key}>{renderInlines(node.children)}</p>;
		case 'heading':
			return (
				<p
					key={key}
					className={node.depth <= 2 ? 'font-semibold text-[1.1em]' : 'font-semibold'}
				>
					{renderInlines(node.children)}
				</p>
			);
		case 'list':
			return node.ordered ? (
				<ol key={key} className='list-decimal space-y-0.5 pl-4'>
					{node.children.map((item, i) => renderListItem(item, i))}
				</ol>
			) : (
				<ul key={key} className='list-disc space-y-0.5 pl-4'>
					{node.children.map((item, i) => renderListItem(item, i))}
				</ul>
			);
		case 'blockquote':
			return (
				<blockquote
					key={key}
					className='border-l-2 border-current pl-2 italic opacity-80'
				>
					{renderBlocks(node.children)}
				</blockquote>
			);
		case 'code':
			return (
				<pre key={key} className='overflow-x-auto rounded bg-black/5 p-2 text-[0.9em]'>
					<code>{node.value}</code>
				</pre>
			);
		case 'thematicBreak':
			return <hr key={key} className='my-1 border-current opacity-30' />;
		case 'html':
			return node.value;
		default:
			return null;
	}
}

function renderBlocks(nodes: RootContent[]): ReactNode {
	return nodes.map((node, i) => renderBlock(node, i));
}

interface Props {
	content: string;
	className?: string;
}

export const MarkdownText = memo(function MarkdownText({ content, className }: Props) {
	const blocks = useMemo(() => {
		const tree = parser.parse(content) as Root;
		return renderBlocks(tree.children);
	}, [content]);

	return <div className={`space-y-1 ${className ?? ''}`}>{blocks}</div>;
});
