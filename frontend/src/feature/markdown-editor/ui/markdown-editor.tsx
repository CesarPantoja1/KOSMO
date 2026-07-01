'use client';

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

import { EditorContent } from './editor-content';
import { TocSidebar } from './toc-sidebar';

import { useHeadings } from '../hooks/use-headings';

export interface MarkdownEditorHandle {
	readonly isDirty: boolean;
}

interface Props {
	markdown: string;
	onChange?: (markdown: string) => void;
	isMaximized?: boolean;
	onMaximize?: () => void;
	onMinimize?: () => void;
}

function slugify(text: string) {
	return text
		.toLowerCase()
		.replace(/[^a-z0-9\s-]/g, '')
		.trim()
		.replace(/\s+/g, '-');
}

export const MarkdownEditor = forwardRef<MarkdownEditorHandle, Props>(
	function MarkdownEditor(
		{ markdown, onChange, isMaximized, onMaximize, onMinimize },
		ref,
	) {
		const [localMarkdown, setLocalMarkdown] = useState(markdown);
		const [activeId, setActiveId] = useState('');
		const prevMarkdownRef = useRef(markdown);
		const isDirtyRef = useRef(false);

		const headings = useHeadings(localMarkdown);

		useEffect(() => {
			if (markdown !== prevMarkdownRef.current) {
				setLocalMarkdown(markdown);
				prevMarkdownRef.current = markdown;
			}
		}, [markdown]);

		useEffect(() => {
			isDirtyRef.current = localMarkdown !== markdown;
		}, [localMarkdown, markdown]);

		useImperativeHandle(
			ref,
			() => ({
				get isDirty() {
					return isDirtyRef.current;
				},
			}),
			[],
		);

		const handleChange = (value: string) => {
			setLocalMarkdown(value);
			onChange?.(value);
		};

		const editorRef = useRef<HTMLDivElement>(null);

		useEffect(() => {
			const editor = editorRef.current;
			if (!editor) return;

			headings.forEach((heading) => {
				const headingElements = Array.from(
					editor.querySelectorAll('h1, h2, h3, h4, h5, h6'),
				);

				headingElements.forEach((element) => {
					if (element.textContent === heading.text) {
						element.id = slugify(heading.text);
					}
				});
			});

			const elements = headings
				.map((heading) => editor.querySelector(`#${CSS.escape(heading.id)}`))
				.filter((el): el is HTMLElement => el !== null);

			if (elements.length === 0) return;

			const observer = new IntersectionObserver(
				(entries) => {
					entries.forEach((entry) => {
						if (entry.isIntersecting) {
							setActiveId(entry.target.id);
						}
					});
				},
				{
					root: editor,
					rootMargin: '-20% 0px -70% 0px',
				},
			);

			elements.forEach((element) => observer.observe(element));

			return () => {
				elements.forEach((element) => observer.unobserve(element));
			};
		}, [headings]);

		return (
			<div className='flex h-full min-h-0 overflow-hidden'>
				<TocSidebar headings={headings} activeId={activeId} />
				<section className='relative flex min-h-0 flex-1 overflow-hidden'>
					<EditorContent
						ref={editorRef}
						markdown={localMarkdown}
						onChange={handleChange}
						isMaximized={isMaximized}
						onMaximize={onMaximize}
						onMinimize={onMinimize}
					/>
				</section>
			</div>
		);
	},
);
