export function MarkdownEditorSkeleton() {
	return (
		<div className='flex h-full min-h-0 overflow-hidden bg-neutral-0 gap-1'>
			<aside className='sticky top-0 h-full shrink-0 flex flex-col bg-neutral-50 border-r border-neutral-200 w-[260px] pt-1'>
				<div className='mb-4 flex items-center justify-between px-4 pt-2 shrink-0'>
					<div className='h-3 w-16 animate-pulse rounded-md bg-neutral-200' />
					<div className='h-4 w-4 animate-pulse rounded bg-neutral-200' />
				</div>
				<nav className='space-y-1 px-3 flex-1 overflow-y-auto pb-4'>
					<div className='h-3 w-32 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 8 }} />
					<div className='h-3 w-40 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 20 }} />
					<div className='h-3 w-28 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 20 }} />
					<div className='h-3 w-36 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 32 }} />
					<div className='h-3 w-24 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 32 }} />
					<div className='h-3 w-32 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 8 }} />
					<div className='h-3 w-28 animate-pulse rounded bg-neutral-200' style={{ paddingLeft: 20 }} />
				</nav>
			</aside>

			<section className='flex flex-col min-h-0 flex-1 overflow-hidden bg-neutral-0 rounded-lg border border-neutral-200'>
				<div className='bg-neutral-100 border-b border-neutral-200 px-4 py-3 shrink-0 rounded-t-lg'>
					<div className='flex w-full items-center justify-between'>
						<div className='flex items-center gap-2'>
							<div className='h-4 w-4 animate-pulse rounded bg-neutral-200' />
							<div className='h-4 w-4 animate-pulse rounded bg-neutral-200' />
							<div className='h-4 w-4 animate-pulse rounded bg-neutral-200' />
							<div className='h-4 w-4 animate-pulse rounded bg-neutral-200' />
						</div>
						<div className='h-5 w-5 animate-pulse rounded bg-neutral-200' />
					</div>
				</div>
				<div className='flex-1 min-h-0 overflow-y-auto space-y-4 px-10 py-8'>
					<div className='h-5 w-3/4 animate-pulse rounded-md bg-neutral-200' />
					<div className='h-5 w-full animate-pulse rounded-md bg-neutral-200' />
					<div className='h-5 w-5/6 animate-pulse rounded-md bg-neutral-200' />
					<div className='h-5 w-full animate-pulse rounded-md bg-neutral-200' />
					<div className='h-5 w-2/3 animate-pulse rounded-md bg-neutral-200' />
					<div className='h-5 w-4/5 animate-pulse rounded-md bg-neutral-200' />
					<div className='h-28 w-full animate-pulse rounded-lg bg-neutral-200' />
				</div>
			</section>
		</div>
	);
}
