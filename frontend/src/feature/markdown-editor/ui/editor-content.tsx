'use client';

import {
	headingsPlugin,
	listsPlugin,
	markdownShortcutPlugin,
	MDXEditor,
	quotePlugin,
	thematicBreakPlugin,
	toolbarPlugin,
	UndoRedo,
	BoldItalicUnderlineToggles,
	CreateLink,
	ListsToggle,
	BlockTypeSelect,
} from '@mdxeditor/editor';

import '@mdxeditor/editor/style.css';

interface Props {
	markdown: string;
	onChange: (value: string) => void;
}

export function EditorContent({ markdown, onChange }: Props) {
	return (
		<div className='flex h-full min-h-0 flex-1 flex-col overflow-y-auto bg-snow'>
			<MDXEditor
				markdown={markdown}
				onChange={onChange}
				contentEditableClassName='prose dark:prose-invert max-w-none px-10 py-20 focus:outline-none overflow-y-auto'
				plugins={[
					headingsPlugin(),
					listsPlugin(),
					quotePlugin(),
					thematicBreakPlugin(),
					markdownShortcutPlugin(),
					toolbarPlugin({
						toolbarContents: () => (
							<>
								<UndoRedo />
								<BoldItalicUnderlineToggles />
								<BlockTypeSelect />
								{/* <CreateLink /> */}
								<ListsToggle />
							</>
						),
					}),
				]}
			/>
		</div>
	);
}
