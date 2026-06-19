'use client';

interface Props {
	onCancel: () => void;
	onConfirm: () => void;
}

const ModalConfimLeave = ({ onCancel, onConfirm }: Props) => {
	return (
		<div
			className='fixed inset-0 z-50 flex items-center justify-center bg-black/50'
			onClick={onCancel}
		>
			<div
				className='bg-base-50 rounded-lg shadow-xl py-7 px-12 w-full max-w-lg mx-4'
				onClick={(e) => e.stopPropagation()}
			>
				<h3 className='text-xl font-semibold text-base-950 mb-4 text-center'>
					Cambios sin guardar
				</h3>
				<p className='text-base-950 text-center mb-6'>
					Si sale ahora, perderá las modificaciones recientes.
				</p>
				<div className='flex justify-center gap-5 mt-9'>
					<button
						className='px-5 py-1 rounded-sm border cursor-pointer bg-base-950 border-base-950 text-base-50  hover:bg-base-50 hover:text-base-950'
						onClick={onCancel}
					>
						Cancelar
					</button>
					<button
						className='px-5 py-1 rounded-sm border cursor-pointer bg-primary-100 text-base-50 border-primary-100 hover:bg-base-50 hover:text-primary-100'
						onClick={onConfirm}
					>
						Aceptar
					</button>
				</div>
			</div>
		</div>
	);
};

export default ModalConfimLeave;
