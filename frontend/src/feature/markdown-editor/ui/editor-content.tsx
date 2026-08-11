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
import { SaveIndicator, type SaveStatus } from './save-indicator';

interface Props {
	markdown: string;
	onChange: (value: string) => void;
	isMaximized?: boolean;
	onMaximize?: () => void;
	onMinimize?: () => void;
	saveStatus?: SaveStatus;
	saveMessage?: string;
	savedMessage?: string;
	errorMessage?: string;
}

export const EditorContent = forwardRef<HTMLDivElement, Props>(function EditorContent(
	{
		markdown,
		onChange,
		isMaximized,
		onMaximize,
		onMinimize,
		saveStatus = 'idle',
		saveMessage,
		savedMessage,
		errorMessage,
	},
	ref,
) {
	return (
		<div ref={ref} className='flex-1 min-h-0 overflow-y-auto'>
			<MDXEditor
				markdown={markdown}
				onChange={onChange}
				contentEditableClassName='prose max-w-none px-10 py-8 bg-neutral-0 focus:outline-none'
				plugins={[
					headingsPlugin(),
					listsPlugin(),
					quotePlugin(),
					thematicBreakPlugin(),
					markdownShortcutPlugin(),
					toolbarPlugin({
						toolbarClassName: 'bg-neutral-100 border-b border-neutral-200',
						toolbarContents: () => (
							<div className='flex w-full items-center justify-between'>
								<div className='flex items-center gap-2'>
									<UndoRedo />
									<BoldItalicUnderlineToggles />
									<BlockTypeSelect />
									<ListsToggle />
								</div>
								<div className='flex items-center gap-3'>
									<SaveIndicator
										status={saveStatus}
										saveMessage={saveMessage}
										savedMessage={savedMessage}
										errorMessage={errorMessage}
									/>
									<button
										type='button'
										className='cursor-pointer text-neutral-500 hover:text-neutral-800 transition-colors'
										onClick={isMaximized ? onMinimize : onMaximize}
										title={isMaximized ? 'Restablecer' : 'Expandir'}
									>
										{isMaximized ? (
											<MinEditor size={20} color='currentColor' />
										) : (
											<MaxEditor size={20} color='currentColor' />
										)}
									</button>
								</div>
							</div>
						),
					}),
				]}
			/>
		</div>
	);
});
