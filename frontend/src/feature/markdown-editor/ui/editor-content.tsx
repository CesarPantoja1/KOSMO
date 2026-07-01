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
import { MaxEditor, MinEditor } from './icons';

interface Props {
	markdown: string;
	onChange: (value: string) => void;
	isMaximized?: boolean;
	onMaximize?: () => void;
	onMinimize?: () => void;
}

export const EditorContent = forwardRef<HTMLDivElement, Props>(function EditorContent(
	{ markdown, onChange, isMaximized, onMaximize, onMinimize },
	ref,
) {
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
							<div className='flex w-full items-center justify-between'>
								<div className='flex items-center gap-2'>
									<UndoRedo />
									<BoldItalicUnderlineToggles />
									<BlockTypeSelect />
									<ListsToggle />
								</div>
								<button
									type='button'
									className='cursor-pointer'
									onClick={isMaximized ? onMinimize : onMaximize}
								>
									{isMaximized ? (
										<MinEditor size={24} color='currentColor' />
									) : (
										<MaxEditor size={24} color='currentColor' />
									)}
								</button>
							</div>
						),
					}),
				]}
			/>
		</div>
	);
});
