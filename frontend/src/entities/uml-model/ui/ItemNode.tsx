'use client';
import { useState, KeyboardEvent } from 'react';
import { useReactFlow } from '@xyflow/react';
import type { UmlNode as UmlFlowNode, UmlItem, Visibility } from '../model/types';

interface UmlRowProps {
	item: UmlItem;
	isMethod?: boolean;
	nodeId: string;
}

function formatItemText(item: UmlItem, isMethod: boolean) {
	return isMethod
		? `${item.visibility} ${item.name}(${item.params || ''})${item.type ? `: ${item.type}` : ''}`
		: `${item.visibility} ${item.name}${item.type ? `: ${item.type}` : ''}`;
}

export function ItemNode({ item, isMethod = false, nodeId }: UmlRowProps) {
	const { setNodes } = useReactFlow<UmlFlowNode>();
	const [isEditing, setIsEditing] = useState(false);
	const [draftText, setDraftText] = useState('');
	const displayText = formatItemText(item, isMethod);

	const listKey = isMethod ? 'methods' : 'attributes';

	// --- LÓGICA DE ELIMINACIÓN ---
	const handleDelete = (e: React.MouseEvent) => {
		e.stopPropagation(); // Evita activar el doble clic o selección del nodo

		setNodes((nodes) =>
			nodes.map((node) => {
				if (node.id === nodeId) {
					// Filtramos la lista para quitar el item actual por su ID
					const updatedList = node.data[listKey].filter((i: UmlItem) => i.id !== item.id);

					return {
						...node,
						data: { ...node.data, [listKey]: updatedList },
					};
				}
				return node;
			}),
		);
	};

	const handleStartEditing = () => {
		setDraftText(displayText);
		setIsEditing(true);
	};

	const handleSave = () => {
		setIsEditing(false);
		let newVisibility = item.visibility;
		let newName = item.name;
		let newType = item.type;
		let newParams = item.params;
		let currentText = draftText.trim();

		if (['+', '-', '#'].includes(currentText[0])) {
			newVisibility = currentText[0] as Visibility;
			currentText = currentText.substring(1).trim();
		}

		if (isMethod) {
			const match = currentText.match(/^([a-zA-Z0-9_]+)\s*\((.*)\)(?:\s*:\s*(.*))?$/);
			if (match) {
				newName = match[1].trim();
				newParams = match[2].trim();
				newType = match[3] ? match[3].trim() : undefined;
			} else {
				newName = currentText;
			}
		} else {
			const match = currentText.match(/^([a-zA-Z0-9_]+)(?:\s*:\s*(.*))?$/);
			if (match) {
				newName = match[1].trim();
				newType = match[2] ? match[2].trim() : undefined;
			} else {
				newName = currentText;
			}
		}

		setNodes((nodes) =>
			nodes.map((node) => {
				if (node.id === nodeId) {
					const updatedList = node.data[listKey].map((i: UmlItem) =>
						i.id === item.id
							? {
									...i,
									visibility: newVisibility,
									name: newName,
									type: newType,
									params: newParams,
								}
							: i,
					);
					return { ...node, data: { ...node.data, [listKey]: updatedList } };
				}
				return node;
			}),
		);
	};

	const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === 'Enter') handleSave();
		if (e.key === 'Escape') setIsEditing(false);
	};

	if (isEditing) {
		return (
			<div className='px-2 py-0.5'>
				<input
					autoFocus
					className='w-full text-sm font-mono text-blue-900 bg-blue-50 border-2 border-dashed border-blue-400 outline-none rounded'
					value={draftText}
					onChange={(e) => setDraftText(e.target.value)}
					onBlur={handleSave}
					onKeyDown={handleKeyDown}
				/>
			</div>
		);
	}

	return (
		<div
			onDoubleClick={handleStartEditing}
			className='group relative px-3 py-1 text-sm font-mono text-gray-800 hover:bg-gray-100 cursor-text transition-colors duration-150'
		>
			<span className={item.isStatic ? 'underline' : ''}>{displayText}</span>

			{/* 🗑️ BOTÓN DE ELIMINAR (Solo visible al hacer hover en la fila) */}
			<button
				onClick={handleDelete}
				className='absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 bg-red-100 hover:bg-red-500 hover:text-white text-red-600 rounded w-4 h-4 flex items-center justify-center text-[10px] transition-all duration-200'
				title='Eliminar'
			>
				✕
			</button>
		</div>
	);
}
