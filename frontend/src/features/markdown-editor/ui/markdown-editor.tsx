'use client';

import type { MDXEditorMethods } from '@mdxeditor/editor';
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

import { EditorContent } from './editor-content';
import { TocSidebar } from './toc-sidebar';

import { useHeadings } from '../model/use-headings';
import type { SaveStatus } from './save-indicator';

export interface MarkdownEditorHandle {
	readonly isDirty: boolean;
}

interface Props {
	markdown: string;
	onChange?: (markdown: string) => void;
	isMaximized?: boolean;
	onMaximize?: () => void;
	onMinimize?: () => void;
	saveStatus?: SaveStatus;
	saveMessage?: string;
	savedMessage?: string;
	errorMessage?: string;
	readOnly?: boolean;
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
		{ markdown, onChange, isMaximized, onMaximize, onMinimize, saveStatus = 'idle', saveMessage, savedMessage, errorMessage, readOnly },
		ref,
	) {
		const [localMarkdown, setLocalMarkdown] = useState(markdown);
		const [headingsMarkdown, setHeadingsMarkdown] = useState(markdown);
		const [activeId, setActiveId] = useState('');
		const prevMarkdownRef = useRef(markdown);
		const localMarkdownRef = useRef(localMarkdown);
		const isDirtyRef = useRef(false);
		const mdxEditorRef = useRef<MDXEditorMethods>(null);
		const isReadyRef = useRef(false);

		useEffect(() => {
			isReadyRef.current = true;
		}, []);

		const headings = useHeadings(headingsMarkdown);

		// Solo se dispara cuando el contenido cambia por una fuente EXTERNA
		// (generación IA, sugerencias de chat aplicadas, recarga de datos), no
		// cuando el cambio se origina dentro del propio editor (ver handleChange,
		// que ya marca prevMarkdownRef como sincronizado antes de propagar hacia
		// afuera). MDXEditor solo lee la prop `markdown` en el montaje inicial,
		// por lo que las actualizaciones externas deben empujarse de forma
		// imperativa via `setMarkdown` para reflejarse en el editor ya montado.
		useEffect(() => {
			if (markdown !== prevMarkdownRef.current) {
				setLocalMarkdown(markdown);
				setHeadingsMarkdown(markdown);
				prevMarkdownRef.current = markdown;
				mdxEditorRef.current?.setMarkdown(markdown);
			}
		}, [markdown]);

		useEffect(() => {
			if (saveStatus === 'saved') {
				setHeadingsMarkdown(localMarkdownRef.current);
			}
		}, [saveStatus]);

		useEffect(() => {
			localMarkdownRef.current = localMarkdown;
		}, [localMarkdown]);

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
			// MDXEditor emite onChange de forma síncrona durante su montaje al
			// normalizar el contenido inicial; antes de que React termine de
			// montar, cualquier setState dispararía el warning de React.
			if (!isReadyRef.current) return;
			// El cambio se origina dentro del propio editor (usuario tecleando):
			// marcamos este valor como ya sincronizado para que, cuando la prop
			// `markdown` "rebote" desde el padre con el mismo contenido, el
			// efecto de arriba no lo interprete como una actualización externa
			// y no dispare `setMarkdown()` (lo que reiniciaría cursor/historial).
			prevMarkdownRef.current = value;
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
				.filter((heading) => heading.id)
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
						editorRef={mdxEditorRef}
						markdown={localMarkdown}
						onChange={handleChange}
						isMaximized={isMaximized}
						onMaximize={onMaximize}
						onMinimize={onMinimize}
						saveStatus={saveStatus}
						saveMessage={saveMessage}
						savedMessage={savedMessage}
						errorMessage={errorMessage}
						readOnly={readOnly}
					/>
				</section>
			</div>
		);
	},
);
