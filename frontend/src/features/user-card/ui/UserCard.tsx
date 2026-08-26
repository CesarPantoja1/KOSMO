interface Props {
	name: string;
}

export function UserCard({ name }: Props) {
	return (
		<div className='p-4 border rounded-xl'>
			<p className='text-lg font-semibold'>{name}</p>
		</div>
	);
}
