'use client';

interface Props {
	onCancel: () => void;
	onConfirm: () => void;
	title?: string;
	description?: string;
	cancelText?: string;
	confirmText?: string;
}

const ModalConfirm = ({
	onCancel,
	onConfirm,
	title = 'Cambios sin guardar',
	description = 'Si sale ahora, perderá las modificaciones recientes.',
	cancelText = 'Cancelar',
	confirmText = 'Aceptar',
}: Props) => {
	return (
		<div className='warning-popup' onClick={onCancel}>
			<div
				className='bg-neutral-0 rounded-xl shadow-lg py-8 px-10 w-full max-w-md mx-4 border border-neutral-200'
				onClick={(e) => e.stopPropagation()}
			>
				<h3 className='text-lg font-semibold text-neutral-800 mb-2 text-center'>
					{title}
				</h3>
				<p className='text-neutral-500 text-sm text-center mb-6'>{description}</p>
				<div className='flex justify-center gap-3 mt-6'>
					<button className='btn btn-secondary' onClick={onCancel}>
						{cancelText}
					</button>
					<button className='btn btn-primary' onClick={onConfirm}>
						{confirmText}
					</button>
				</div>
			</div>
		</div>
	);
};

export { ModalConfirm };
