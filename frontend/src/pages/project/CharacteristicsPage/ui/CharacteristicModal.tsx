import { Close, Loading } from '@/shared/ui';
import { useState, useEffect } from 'react';
import { getAlternativeCharacteristics } from '@/entities/characteristic';
import type { AlternativeCharacteristic } from '@/entities/characteristic';

type Props = {
	projectId: string;
	onClose: () => void;
	onApply: (selected: AlternativeCharacteristic[]) => void;
};

const CharacteristicModal = ({ projectId, onClose, onApply }: Props) => {
	const [alternatives, setAlternatives] = useState<AlternativeCharacteristic[]>([]);
	const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
	const [isLoading, setIsLoading] = useState(true);
	const [hasError, setHasError] = useState(false);

	useEffect(() => {
		const fetch = async () => {
			setIsLoading(true);
			setHasError(false);
			try {
				const data = await getAlternativeCharacteristics(projectId);
				setAlternatives(data);
			} catch {
				setHasError(true);
			} finally {
				setIsLoading(false);
			}
		};
		fetch();
	}, [projectId]);

	const toggle = (id: string) => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	};

	const handleApply = () => {
		const selected = alternatives.filter((a) => selectedIds.has(a.id));
		if (selected.length === 0) return;
		onApply(selected);
	};

	return (
		<div
			className='fixed inset-0 z-50 flex items-center justify-center bg-black/60'
			onClick={onClose}
		>
			{isLoading && <Loading title='Nuevas Características' description='Buscando sugerencias para tu proyecto...' />}

			{hasError && <ErrorState />}

			{!isLoading && !hasError && (
				<div
					className='bg-base-50 w-1/2 p-7 rounded-md flex flex-col items-center gap-4'
					onClick={(e) => e.stopPropagation()}
				>
					<div className='w-full flex flex-col gap-4'>
						<div className='flex justify-between'>
							<h2 className='text-2xl font-semibold'>Nuevas Características</h2>
							<button className='cursor-pointer' onClick={onClose}>
								<Close color='text-base-600 hover:text-status-error' size={24} />
							</button>
						</div>
						<p className='flex-1 text-base font-normal'>
							Selecciona una o más características sugeridas para tu proyecto.
						</p>
					</div>

					<div className='w-full flex-1 p-0.5 flex flex-col justify-start items-center gap-5'>
						{alternatives.map((alt) => {
							const isSelected = selectedIds.has(alt.id);
							return (
								<button
									key={alt.id}
									onClick={() => toggle(alt.id)}
									className={`w-full p-5 flex flex-col items-start gap-3 cursor-pointer rounded-sm text-left transition-shadow duration-200 ${
										isSelected
											? 'outline-2 outline-primary-100 shadow-md bg-primary-100/5'
											: 'outline-1 outline-base-300 hover:shadow-lg hover:outline-primary-100'
									}`}
								>
									<h3 className='text-primary-100 text-lg font-semibold'>{alt.title}</h3>
									<p className='text-base font-normal'>{alt.description}</p>
								</button>
							);
						})}
					</div>

					<button
						onClick={handleApply}
						disabled={selectedIds.size === 0}
						className='px-5 py-1 w-fit cursor-pointer text-base-50 outline outline-ai bg-ai rounded-sm hover:bg-base-50 hover:outline-ai hover:text-ai transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed'
					>
						Aplicar
					</button>
				</div>
			)}
		</div>
	);
};

export default CharacteristicModal;

const ErrorState = () => (
	<div className='w-1/2 px-5 py-7 bg-base-50 outline outline-base-300 inline-flex flex-col justify-center rounded-md items-center gap-7'>
		<h2 className='text-center justify-start text-black text-2xl font-semibold'>
			⚠️ No se pudieron cargar las sugerencias.
		</h2>
		<p className='text-black text-lg text-center'>
			Hubo un fallo al obtener las características sugeridas. Inténtalo de nuevo.
		</p>
	</div>
);

