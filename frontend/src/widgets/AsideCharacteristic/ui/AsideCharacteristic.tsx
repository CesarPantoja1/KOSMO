import { useState, type ElementType } from 'react';
import type { CharacteristicResponse } from '@/entities/characteristic';
import { CloseMarkdownContent, OpenMarkdownContent } from '@/shared/ui';

type AsideCharacteristicProps = {
	title?: string;
	characteristics: CharacteristicResponse[];
	selectedId: string | null;
	onSelectCharacteristic: (id: string) => void;
	hasIcon: Record<string, boolean>;
	defaultExpanded?: boolean;
	icon: ElementType<{ size?: number; color: string }>;
};

const AsideCharacteristic = ({
	title = 'Lista de Características',
	characteristics,
	selectedId,
	onSelectCharacteristic,
	hasIcon,
	defaultExpanded = true,
	icon: Icon,
}: AsideCharacteristicProps) => {
	const [isExpanded, setIsExpanded] = useState(defaultExpanded);

	return (
		<aside
			className='pt-3 bg-base-100/50 rounded-sm flex flex-col shrink-0 transition-all duration-300'
			style={{ width: isExpanded ? 352 : 64 }}
		>
			{isExpanded ? (
				<>
					<div className='mb-3 flex items-center justify-between px-4 shrink-0'>
						<h3 className='text-primary-100 text-lg font-bold'>{title}</h3>
						<button
							onClick={() => setIsExpanded(false)}
							className='cursor-pointer p-1 hover:bg-base-200/30 rounded'
						>
							<CloseMarkdownContent size={20} />
						</button>
					</div>

					<div className='flex-1 flex flex-col gap-1 overflow-y-auto pb-4 px-2'>
						{characteristics.length === 0 && (
							<p className='text-base-600 text-sm px-3 py-2'>
								No hay características disponibles.
							</p>
						)}
						{characteristics.map((c) => {
							const isSelected = c.id === selectedId;
							return (
								<button
									key={c.id}
									onClick={() => onSelectCharacteristic(c.id)}
									className={`w-full p-3 flex justify-start items-start gap-3 text-left cursor-pointer transition-colors rounded ${
										isSelected
											? 'bg-primary-100/10 border-l-4 border-primary-100'
											: 'border-l-4 border-transparent hover:bg-base-200/30'
									}`}
								>
									<span
										className={`text-base font-bold mt-0.5 shrink-0 ${
											isSelected ? 'text-primary-100' : 'text-base-800'
										}`}
									>
										{c.display_id}
									</span>
									<p
										className={`flex-1 text-sm font-medium leading-snug pt-0.5 ${
											isSelected ? 'text-primary-100' : 'text-base-600'
										}`}
									>
										{c.title}
									</p>
									{hasIcon[c.id] && (
										<div className='shrink-0 mt-0.5'>
											<Icon
												size={20}
												color={isSelected ? 'text-primary-100' : 'text-base-600'}
											/>
										</div>
									)}
								</button>
							);
						})}
					</div>
				</>
			) : (
				<>
					<div className='flex justify-center pb-3 pt-2 shrink-0'>
						<button
							onClick={() => setIsExpanded(true)}
							className='cursor-pointer p-1 hover:bg-base-200/30 rounded'
						>
							<OpenMarkdownContent size={20} />
						</button>
					</div>

					<div className='flex-1 flex flex-col gap-1 overflow-y-auto px-1 pb-4'>
						{characteristics.map((c) => {
							const isSelected = c.id === selectedId;
							return (
								<div key={c.id} className='relative group'>
									<button
										onClick={() => onSelectCharacteristic(c.id)}
										title={c.title}
										className={`w-full p-2 flex flex-col items-center gap-1 cursor-pointer transition-colors rounded ${
											isSelected
												? 'bg-primary-100/10 border-l-4 border-primary-100'
												: 'border-l-4 border-transparent hover:bg-base-200/30'
										}`}
									>
										<span
											className={`text-xs font-bold ${
												isSelected ? 'text-primary-100' : 'text-base-800'
											}`}
										>
											{c.display_id}
										</span>
										{hasIcon[c.id] && (
											<Icon
												size={16}
												color={isSelected ? 'text-primary-100' : 'text-base-600'}
											/>
										)}
									</button>
								</div>
							);
						})}
					</div>
				</>
			)}
		</aside>
	);
};

export default AsideCharacteristic;
