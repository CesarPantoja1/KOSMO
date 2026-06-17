'use client';

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

export function EditorContent({ markdown, onChange }: Props) {
	return (
		<div className='flex h-full min-h-0 flex-1 flex-col overflow-y-auto bg-base-300'>
			<MDXEditor
				markdown={markdown}
				onChange={onChange}
				contentEditableClassName='prose max-w-none px-10 py-20 bg-base-50 focus:outline-none overflow-y-auto'
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
