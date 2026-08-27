import { KeyIcon } from '@/shared/ui';

export function ApiKeySection() {
	return (
		<section className='py-20'>
			<div className='mx-auto max-w-5xl px-6'>
				<div className='rounded-3xl border border-neutral-200 bg-neutral-50 p-8 md:p-10'>
					<div className='flex flex-col items-start gap-6 md:flex-row md:items-center'>
						<div className='flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-neutral-100 text-neutral-500'>
							<KeyIcon size={24} />
						</div>

						<div className='flex-1'>
							<h3 className='text-xl font-semibold text-neutral-800'>
								Conecta tu modelo de IA preferido
							</h3>

							<p className='mt-2 max-w-2xl text-sm leading-6 text-neutral-500'>
								Para utilizar KOSMO necesitas un API Key de un proveedor de modelos de
								IA. Tú eliges el modelo y mantienes el control sobre tu consumo.
							</p>
						</div>

						<div className='flex gap-3'>
							<div className='flex h-12 w-12 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-0 text-sm text-neutral-600'>
								AI
							</div>
							<div className='flex h-12 w-12 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-0 text-sm text-neutral-600'>
								✦
							</div>
							<div className='flex h-12 w-12 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-0 text-sm text-neutral-600'>
								G
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>
	);
}
