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
	isExpanded?: boolean;
	onToggleExpand?: (expanded: boolean) => void;
	icon: ElementType<{ size?: number; color: string }>;
};

const AsideCharacteristic = ({
	title = 'Funcionalidades',
	characteristics,
	selectedId,
	onSelectCharacteristic,
	hasIcon,
	defaultExpanded = true,
	isExpanded: isExpandedProp,
	onToggleExpand,
	icon: Icon,
}: AsideCharacteristicProps) => {
	const [isExpandedInternal, setIsExpandedInternal] = useState(defaultExpanded);
	const isExpanded = isExpandedProp ?? isExpandedInternal;

	const toggleExpand = (value: boolean) => {
		if (onToggleExpand) {
			onToggleExpand(value);
		} else {
			setIsExpandedInternal(value);
		}
	};

	return (
		<aside
			className='bg-neutral-50 border-r border-neutral-200 flex flex-col shrink-0 transition-all duration-300'
			style={{ width: isExpanded ? 288 : 52 }}
		>
			{isExpanded ? (
				<>
					<div className='flex items-center justify-between px-4 py-3 border-b border-neutral-200 shrink-0'>
						<h3 className='text-xs font-semibold uppercase tracking-wider text-neutral-500'>{title}</h3>
						<button
							onClick={() => toggleExpand(false)}
							className='cursor-pointer p-1 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded transition-colors'
						>
							<CloseMarkdownContent size={18} />
						</button>
					</div>

					<div className='flex-1 flex flex-col gap-0.5 overflow-y-auto py-2 px-2'>
						{characteristics.length === 0 && (
							<p className='text-neutral-400 text-xs px-3 py-2'>
								No hay funcionalidades disponibles.
							</p>
						)}
						{characteristics.map((c) => {
							const isSelected = c.id === selectedId;
							return (
								<button
									key={c.id}
									onClick={() => onSelectCharacteristic(c.id)}
									className={`w-full px-3 py-2.5 flex justify-start items-start gap-2.5 text-left cursor-pointer transition-colors rounded-md ${
										isSelected
											? 'bg-primary-50 border-l-4 border-primary-500'
											: 'border-l-4 border-transparent hover:bg-neutral-100'
									}`}
								>
									<span
										className={`text-xs font-bold mt-0.5 shrink-0 ${
											isSelected ? 'text-primary-500' : 'text-neutral-400'
										}`}
									>
										{c.display_id}
									</span>
									<p
										className={`flex-1 text-xs font-medium leading-snug pt-0.5 ${
											isSelected ? 'text-primary-600' : 'text-neutral-600'
										}`}
									>
										{c.title}
									</p>
									{hasIcon[c.id] && (
										<div className='shrink-0 mt-0.5'>
											<Icon
												size={16}
												color={isSelected ? 'text-primary-500' : 'text-neutral-400'}
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
					<div className='flex justify-center py-3 border-b border-neutral-200 shrink-0'>
						<button
							onClick={() => toggleExpand(true)}
							className='cursor-pointer p-1 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded transition-colors'
						>
							<OpenMarkdownContent size={18} />
						</button>
					</div>

					<div className='flex-1 flex flex-col gap-0.5 overflow-y-auto py-2 px-1'>
						{characteristics.map((c) => {
							const isSelected = c.id === selectedId;
							return (
								<button
									key={c.id}
									onClick={() => onSelectCharacteristic(c.id)}
									title={c.title}
									className={`w-full py-2 flex flex-col items-center gap-1 cursor-pointer transition-colors rounded-md ${
										isSelected
											? 'bg-primary-50 border-l-2 border-primary-500'
											: 'border-l-2 border-transparent hover:bg-neutral-100'
									}`}
								>
									<span
										className={`text-[10px] font-bold ${
											isSelected ? 'text-primary-500' : 'text-neutral-400'
										}`}
									>
										{c.display_id}
									</span>
									{hasIcon[c.id] && (
										<Icon
											size={14}
											color={isSelected ? 'text-primary-500' : 'text-neutral-400'}
										/>
									)}
								</button>
							);
						})}
					</div>
				</>
			)}
		</aside>
	);
};

export default AsideCharacteristic;
