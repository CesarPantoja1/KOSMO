'use client';

interface Props {
	onCancel: () => void;
	onConfirm: () => void;
	title?: string;
	description?: string;
	cancelText?: string;
	confirmText?: string;
}

const ModalConfirmLeave = ({
	onCancel,
	onConfirm,
	title = 'Cambios sin guardar',
	description = 'Si sale ahora, perderá las modificaciones recientes.',
	cancelText = 'Cancelar',
	confirmText = 'Aceptar',
}: Props) => {
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
					{title}
				</h3>
				<p className='text-base-950 text-center mb-6'>
					{description}
				</p>
				<div className='flex justify-center gap-5 mt-9'>
					<button
						className='btn border bg-base-950 border-base-950 text-base-50 hover:bg-base-950/90'
						onClick={onCancel}
					>
						{cancelText}
					</button>
					<button
						className='btn border bg-primary-100 text-base-50 border-primary-100 hover:bg-primary-100/90'
						onClick={onConfirm}
					>
						{confirmText}
					</button>
				</div>
			</div>
		</div>
	);
};

export default ModalConfirmLeave;
