'use client';

type ButtonProps = {
	children: React.ReactNode;
	icon?: React.ReactNode;
	onClick?: () => void;
	variant?: 'primary' | 'secondary' | 'destructive' | 'ai';
	disabled?: boolean;
};

/**
 * ButtonSM
 *
 * Uso: Acciones secundarias.
 * #### Props:
 * - children: contenido del botón (texto o elementos)
 * - icon?: elemento React para icono (opcional)
 * - onClick?: función llamada al hacer click
 * - variant?: 'primary' | 'secondary' | 'destructive' (afecta estilo)
 * - disabled?: boolean (deshabilita el botón)
 */
export function ButtonSM({
	children,
	icon,
	onClick,
	variant = 'primary',
	disabled = false,
}: ButtonProps) {
	switch (variant) {
		case 'primary':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-2.5 py-1.5 text-xs rounded-md min-w-16 bg-primary text-snow hover:bg-primary-hover active:bg-primary-active disabled:bg-primary-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'secondary':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-2.5 py-1.5 text-xs rounded-md min-w-16 bg-snow text-text hover:bg-snow-hover active:bg-snow-active disabled:bg-snow-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'destructive':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-2.5 py-1.5 text-xs rounded-md min-w-16 bg-error text-snow hover:bg-error-hover active:bg-error-active disabled:bg-error-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'ai':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-2.5 py-1.5 text-xs rounded-md min-w-16 bg-ai text-snow hover:bg-ai-hover active:bg-ai-active disabled:bg-ai-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);
	}
}

/**
 * ButtonMD
 *
 * Uso: Call to Action y Formularios.
 * #### Props:
 * - children: contenido del botón (texto o elementos)
 * - onClick?: función llamada al hacer click
 * - variant?: 'primary' | 'secondary' | 'destructive' | 'ai' (afecta estilo)
 * - disabled?: boolean (deshabilita el botón)
 */
export function ButtonMD({
	children,
	icon,
	onClick,
	variant = 'primary',
	disabled = false,
}: ButtonProps) {
	switch (variant) {
		case 'primary':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-4 py-2 text-sm rounded-lg min-w-20 bg-primary text-snow hover:bg-primary-hover active:bg-primary-active disabled:bg-primary-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'secondary':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-4 py-2 text-sm rounded-lg min-w-20 align-middle bg-snow text-text hover:bg-snow-hover active:bg-snow-active disabled:bg-snow-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'destructive':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-4 py-2 text-sm rounded-lg min-w-20 align-middle bg-error text-snow hover:bg-error-hover active:bg-error-active disabled:bg-error-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'ai':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-4 py-2 text-sm rounded-lg min-w-20 bg-ai text-snow hover:bg-ai-hover active:bg-ai-active disabled:bg-ai-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);
	}
}

/**
 * ButtonLG
 *
 * Uso: Acciones principales y Call to Action destacado.
 * #### Props:
 * - children: contenido del botón (texto o elementos)
 * - onClick?: función llamada al hacer click
 * - variant?: 'primary' | 'secondary' | 'destructive' | 'ai' (afecta estilo)
 * - disabled?: boolean (deshabilita el botón)
 */
export function ButtonLG({
	children,
	icon,
	onClick,
	variant = 'primary',
	disabled = false,
}: ButtonProps) {
	switch (variant) {
		case 'primary':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-6 py-3 text-base rounded-lg min-w-30 bg-primary text-snow hover:bg-primary-hover active:bg-primary-active disabled:bg-primary-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'secondary':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-6 py-3 text-base rounded-lg min-w-30 bg-snow text-text hover:bg-snow-hover active:bg-snow-active disabled:bg-snow-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'destructive':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-6 py-3 text-base rounded-lg min-w-30 bg-error text-snow hover:bg-error-hover active:bg-error-active disabled:bg-error-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);

		case 'ai':
			return (
				<button
					onClick={onClick}
					disabled={disabled}
					className='px-6 py-3 text-base rounded-lg min-w-30 bg-ai text-snow hover:bg-ai-hover active:bg-ai-active disabled:bg-ai-disabled disabled:cursor-not-allowed'
				>
					{icon ? (
						<span className='inline-flex items-center gap-1'>
							{icon} {children}
						</span>
					) : (
						<span> {children} </span>
					)}
				</button>
			);
	}
}
