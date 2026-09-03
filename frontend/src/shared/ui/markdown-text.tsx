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

function renderGherkinLine(line: string, lineKey: number): ReactNode {
	const trimmed = line.trimStart();
	const indent = line.slice(0, line.length - trimmed.length);

	const gherkinKeywords = [
		{ regex: /^(Dado|Given)\b/, color: 'text-emerald-700 font-semibold' },
		{ regex: /^(Cuando|When)\b/, color: 'text-sky-700 font-semibold' },
		{ regex: /^(Entonces|Then)\b/, color: 'text-amber-700 font-semibold' },
		{ regex: /^(Y|And)\b/, color: 'text-purple-700 font-semibold' },
		{ regex: /^(Pero|But)\b/, color: 'text-rose-700 font-semibold' },
		{
			regex:
				/^(Escenario|Scenario|Característica|Feature|Esquema del escenario|Scenario Outline|Ejemplos|Examples):/,
			color: 'text-primary-100 font-bold',
		},
	];

	for (const { regex, color } of gherkinKeywords) {
		const match = trimmed.match(regex);
		if (match) {
			const keyword = match[0];
			const rest = trimmed.slice(keyword.length);
			return (
				<div key={lineKey} className='whitespace-pre-wrap wrap-break-word'>
					{indent}
					<span className={color}>{keyword}</span>
					{rest}
				</div>
			);
		}
	}

	return (
		<div key={lineKey} className='whitespace-pre-wrap wrap-break-word'>
			{line}
		</div>
	);
}

function renderCodeBlock(value: string, lang?: string | null, key?: number): ReactNode {
	const isGherkin =
		lang === 'gherkin' ||
		/^\s*(Dado|Cuando|Entonces|Given|When|Then|Escenario|Feature)/m.test(value);

	if (isGherkin) {
		const lines = value.split('\n');
		return (
			<pre
				key={key}
				className='rounded bg-black/5 p-2 text-xs font-mono text-stone-800 whitespace-pre-wrap wrap-break-word max-w-full overflow-hidden'
			>
				<code>{lines.map((line, i) => renderGherkinLine(line, i))}</code>
			</pre>
		);
	}

	return (
		<pre
			key={key}
			className='rounded bg-black/5 p-2 text-xs font-mono whitespace-pre-wrap wrap-break-word max-w-full overflow-hidden'
		>
			<code>{value}</code>
		</pre>
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
			return renderCodeBlock(node.value, node.lang, key);
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
