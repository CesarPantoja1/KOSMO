import { Edith, Trash } from './icons';

type Props = {
  code: string
  title: string
  description: string
}

const CardCharacterist = ({ code, title, description }: Props) => {
	return (
		<div className='outline outline-base-300 m-0.5 px-8 py-4 inline-flex justify-start items-center gap-7 hover:shadow-md'>
			<div className='w-14 inline-flex flex-col text-xl font-semibold justify-center items-center gap-2.5'>
				{code}
			</div>
			<div className='flex-1 inline-flex flex-col justify-center gap-2.5'>
				<h3 className='text-primary-100 text-xl font-semibold'>
					{title}
				</h3>
				<p>
					{description}
				</p>
			</div>
			<div className='py-3 flex flex-col justify-end items-center gap-2'>
				<button className='cursor-pointer'>
					<Edith color='text-base-600 hover:text-status-success' size={24} />
				</button>
				<button className='cursor-pointer'>
					<Trash color='text-base-600 hover:text-status-error' size={24} />
				</button>
			</div>
		</div>
	);
};

export default CardCharacterist;
