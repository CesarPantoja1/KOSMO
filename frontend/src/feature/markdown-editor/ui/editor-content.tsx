'use client';

import { forwardRef } from 'react';

import {
	BlockTypeSelect,
	BoldItalicUnderlineToggles,
	headingsPlugin,
	listsPlugin,
	ListsToggle,
	markdownShortcutPlugin,
	MDXEditor,
	quotePlugin,
	thematicBreakPlugin,
	toolbarPlugin,
	UndoRedo,
} from '@mdxeditor/editor';

import '@mdxeditor/editor/style.css';

interface Props {
	markdown: string;
	onChange: (value: string) => void;
}

export const EditorContent = forwardRef<HTMLDivElement, Props>(
	function EditorContent({ markdown, onChange }, ref) {
		return (
			<div ref={ref} className='flex-1 min-h-0 overflow-y-auto'>
				<MDXEditor
					markdown={markdown}
					onChange={onChange}
					contentEditableClassName='prose max-w-none px-10 py-20 bg-base-50 focus:outline-none'
					plugins={[
						headingsPlugin(),
						listsPlugin(),
						quotePlugin(),
						thematicBreakPlugin(),
						markdownShortcutPlugin(),
						toolbarPlugin({
							toolbarClassName: 'bg-base-300',
							toolbarContents: () => (
								<>
									<UndoRedo />
									<BoldItalicUnderlineToggles />
									<BlockTypeSelect />
									<ListsToggle />
								</>
							),
						}),
					]}
				/>
			</div>
		);
	},
);
