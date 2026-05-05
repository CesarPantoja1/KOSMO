'use client';
import { useState, KeyboardEvent } from 'react';
import { Handle, Position, NodeProps, useReactFlow } from '@xyflow/react';
import type { UmlNode as UmlFlowNode } from '../model/types';
import { ItemNode } from './ItemNode';

export function UmlNode({ id, data, selected }: NodeProps<UmlFlowNode>) {
	const { setNodes } = useReactFlow<UmlFlowNode>();

	// Estado para la edición del nombre de la clase
	const [isEditingName, setIsEditingName] = useState(false);
	const [className, setClassName] = useState(data.name);

	// Funciones para guardar el nombre de la clase
	const handleSaveName = () => {
		setIsEditingName(false);
		if (className.trim() === '') {
			setClassName(data.name); // Si lo deja vacío, revertir
			return;
		}
		setNodes((nodes) =>
			nodes.map((node) => {
				if (node.id === id) {
					return { ...node, data: { ...node.data, name: className.trim() } };
				}
				return node;
			}),
		);
	};

	const handleKeyDownName = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === 'Enter') handleSaveName();
		if (e.key === 'Escape') {
			setIsEditingName(false);
			setClassName(data.name);
		}
	};

	// Funciones para agregar atributos/métodos (igual que antes)
	const handleAddAttribute = () => {
		const newId = `attr-${Date.now()}`;
		setNodes((nodes) =>
			nodes.map((node) => {
				if (node.id === id) {
					return {
						...node,
						data: {
							...node.data,
							attributes: [
								...node.data.attributes,
								{ id: newId, visibility: '-', name: 'nuevoAtributo', type: 'string' },
							],
						},
					};
				}
				return node;
			}),
		);
	};

	const handleAddMethod = () => {
		const newId = `meth-${Date.now()}`;
		setNodes((nodes) =>
			nodes.map((node) => {
				if (node.id === id) {
					return {
						...node,
						data: {
							...node.data,
							methods: [
								...node.data.methods,
								{ id: newId, visibility: '+', name: 'nuevoMetodo', type: 'void' },
							],
						},
					};
				}
				return node;
			}),
		);
	};

	return (
		<div
			className={`min-w-50 bg-white border-2 rounded shadow-sm relative group
      ${selected ? 'border-blue-500 shadow-md ring-4 ring-blue-100' : 'border-gray-400'}`}
		>
			<Handle type='target' position={Position.Top} className='w-3 h-3 bg-gray-400' />
			<Handle type='target' position={Position.Left} className='w-3 h-3 bg-gray-400' />
			<Handle type='source' position={Position.Bottom} className='w-3 h-3 bg-gray-400' />
			<Handle type='source' position={Position.Right} className='w-3 h-3 bg-gray-400' />

			{/* ✏️ CABECERA EDITABLE */}
			<div
				className='bg-[#fcf8e3] text-center font-bold border-b-2 border-gray-400 py-2 px-4 rounded-t min-h-10 flex flex-col items-center justify-center cursor-text'
				onDoubleClick={() => setIsEditingName(true)}
				title='Doble clic para editar nombre'
			>
				{data.stereotype && (
					<div className='text-xs font-normal italic pointer-events-none'>
						{data.stereotype}
					</div>
				)}

				{isEditingName ? (
					<input
						autoFocus
						className='w-full text-center font-bold text-blue-900 bg-blue-50 border-2 border-dashed border-blue-400 outline-none rounded px-1 mt-1'
						value={className}
						onChange={(e) => setClassName(e.target.value)}
						onBlur={handleSaveName}
						onKeyDown={handleKeyDownName}
					/>
				) : (
					<div
						className={`${data.isAbstract ? 'italic' : ''} w-full hover:bg-yellow-100/50 rounded transition-colors duration-150`}
					>
						{data.name}
					</div>
				)}
			</div>

			{/* ATRIBUTOS */}
			<div className='min-h-5 border-b-2 border-gray-400 py-1 relative'>
				{data.attributes.map((attr) => (
					<ItemNode key={attr.id} item={attr} nodeId={id} />
				))}
				{selected && (
					<button
						onClick={handleAddAttribute}
						className='absolute -right-6 top-1 bg-green-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-green-600 shadow'
						title='Añadir atributo'
					>
						+
					</button>
				)}
			</div>

			{/* MÉTODOS */}
			<div className='min-h-5 py-1 rounded-b relative'>
				{data.methods.map((method) => (
					<ItemNode key={method.id} item={method} isMethod nodeId={id} />
				))}
				{selected && (
					<button
						onClick={handleAddMethod}
						className='absolute -right-6 top-1 bg-green-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-green-600 shadow'
						title='Añadir método'
					>
						+
					</button>
				)}
			</div>
		</div>
	);
}
