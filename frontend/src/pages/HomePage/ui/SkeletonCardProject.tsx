const SkeletonCardProject = () => {
	return (
		/* Skeleton grid */
		<div className='grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5'>
			{Array.from({ length: 6 }).map((_, index) => (
				<div
					key={index}
					className='flex min-h-40 flex-col rounded-lg bg-neutral-0 p-5 shadow-sm border border-neutral-200'
				>
					<div className='h-6 w-3/4 rounded-md bg-neutral-100 animate-pulse' />
					<div className='mt-3 h-4 w-full rounded-md bg-neutral-100 animate-pulse' />
					<div className='mt-2 h-4 w-5/6 rounded-md bg-neutral-100 animate-pulse' />
					<div className='mt-auto flex items-center gap-3 pt-3 border-t border-neutral-100'>
						<div className='h-4 w-24 rounded-md bg-neutral-100 animate-pulse' />
						<div className='ml-auto h-5 w-20 rounded-md bg-neutral-100 animate-pulse' />
					</div>
				</div>
			))}
		</div>
	);
};

export default SkeletonCardProject;
