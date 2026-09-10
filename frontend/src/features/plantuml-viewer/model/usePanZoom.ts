import { useCallback, useEffect, useRef, useState } from 'react';

import type { PanZoomState } from '../model/types';
import { ZOOM_MAX, ZOOM_MIN, ZOOM_STEP_FACTOR } from '../lib/zoom';

interface UsePanZoomOptions {
	control?: 'controlled' | 'uncontrolled';
	controlledZoom?: number;
	controlledTx?: number;
	controlledTy?: number;
	onPanZoomChange?: (state: PanZoomState) => void;
}

export function usePanZoom(isReady: boolean, options?: UsePanZoomOptions) {
	const controlled = options?.control === 'controlled';
	const onPanZoomChange = options?.onPanZoomChange;

	const [internalZoom, setInternalZoom] = useState(1);
	const [internalTx, setInternalTx] = useState(0);
	const [internalTy, setInternalTy] = useState(0);
	const [isPanning, setIsPanning] = useState(false);

	const zoom = controlled ? (options?.controlledZoom ?? 1) : internalZoom;
	const tx = controlled ? (options?.controlledTx ?? 0) : internalTx;
	const ty = controlled ? (options?.controlledTy ?? 0) : internalTy;

	const viewportRef = useRef<HTMLDivElement>(null);
	const isPanningRef = useRef(false);
	const panStartRef = useRef({ x: 0, y: 0 });
	const panTxTyRef = useRef({ tx: 0, ty: 0 });
	const zoomRef = useRef(zoom);

	useEffect(() => {
		zoomRef.current = zoom;
	}, [zoom]);

	const emitChange = useCallback(
		(nextZoom: number, nextTx: number, nextTy: number) => {
			if (controlled) {
				onPanZoomChange?.({ zoom: nextZoom, tx: nextTx, ty: nextTy });
			}
		},
		[controlled, onPanZoomChange],
	);

	const zoomAt = useCallback(
		(factor: number, cx: number, cy: number) => {
			const newZoom = Math.max(
				ZOOM_MIN,
				Math.min(ZOOM_MAX, zoomRef.current * factor),
			);
			const f = newZoom / zoomRef.current;
			const nextTx = cx - (cx - tx) * f;
			const nextTy = cy - (cy - ty) * f;

			if (controlled) {
				emitChange(newZoom, nextTx, nextTy);
			} else {
				setInternalTx(nextTx);
				setInternalTy(nextTy);
				setInternalZoom(newZoom);
			}
		},
		[tx, ty, controlled, emitChange],
	);

	const zoomIn = useCallback(() => {
		const vp = viewportRef.current;
		if (!vp) return;
		const r = vp.getBoundingClientRect();
		zoomAt(ZOOM_STEP_FACTOR, r.width / 2, r.height / 2);
	}, [zoomAt]);

	const zoomOut = useCallback(() => {
		const vp = viewportRef.current;
		if (!vp) return;
		const r = vp.getBoundingClientRect();
		zoomAt(1 / ZOOM_STEP_FACTOR, r.width / 2, r.height / 2);
	}, [zoomAt]);

	const zoomReset = useCallback(() => {
		if (controlled) {
			emitChange(1, 0, 0);
		} else {
			setInternalZoom(1);
			setInternalTx(0);
			setInternalTy(0);
		}
	}, [controlled, emitChange]);

	useEffect(() => {
		const el = viewportRef.current;
		if (!el || !isReady) return;

		const handler = (e: WheelEvent) => {
			e.preventDefault();
			const r = el.getBoundingClientRect();
			const mx = e.clientX - r.left;
			const my = e.clientY - r.top;
			const factor =
				e.deltaY < 0 ? ZOOM_STEP_FACTOR : 1 / ZOOM_STEP_FACTOR;
			zoomAt(factor, mx, my);
		};

		el.addEventListener('wheel', handler, { passive: false });
		return () => el.removeEventListener('wheel', handler);
	}, [isReady, zoomAt]);

	const handlePanStart = (e: React.MouseEvent) => {
		if (e.button !== 0) return;
		e.preventDefault();
		isPanningRef.current = true;
		setIsPanning(true);
		panStartRef.current = { x: e.clientX, y: e.clientY };
		panTxTyRef.current = { tx, ty };
	};

	const handlePanMove = (e: React.MouseEvent) => {
		if (!isPanningRef.current) return;
		const dx = e.clientX - panStartRef.current.x;
		const dy = e.clientY - panStartRef.current.y;
		const nextTx = panTxTyRef.current.tx + dx;
		const nextTy = panTxTyRef.current.ty + dy;

		if (controlled) {
			emitChange(zoomRef.current, nextTx, nextTy);
		} else {
			setInternalTx(nextTx);
			setInternalTy(nextTy);
		}
	};

	const handlePanEnd = () => {
		isPanningRef.current = false;
		setIsPanning(false);
	};

	return {
		zoom,
		tx,
		ty,
		isPanning,
		viewportRef,
		zoomIn,
		zoomOut,
		zoomReset,
		handlePanStart,
		handlePanMove,
		handlePanEnd,
	};
}
