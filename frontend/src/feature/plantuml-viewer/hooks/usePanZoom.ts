import { useCallback, useEffect, useRef, useState } from 'react';

import { ZOOM_MAX, ZOOM_MIN, ZOOM_STEP_FACTOR } from '../lib/zoom';

export function usePanZoom(isReady: boolean) {
	const [zoom, setZoom] = useState(1);
	const [tx, setTx] = useState(0);
	const [ty, setTy] = useState(0);
	const [isPanning, setIsPanning] = useState(false);

	const viewportRef = useRef<HTMLDivElement>(null);
	const isPanningRef = useRef(false);
	const panStartRef = useRef({ x: 0, y: 0 });
	const panTxTyRef = useRef({ tx: 0, ty: 0 });
	const zoomRef = useRef(zoom);

	useEffect(() => {
		zoomRef.current = zoom;
	}, [zoom]);

	const zoomAt = useCallback((factor: number, cx: number, cy: number) => {
		const newZoom = Math.max(
			ZOOM_MIN,
			Math.min(ZOOM_MAX, zoomRef.current * factor),
		);
		const f = newZoom / zoomRef.current;
		setTx((t) => cx - (cx - t) * f);
		setTy((t) => cy - (cy - t) * f);
		setZoom(newZoom);
	}, []);

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
		setZoom(1);
		setTx(0);
		setTy(0);
	}, []);

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
		setTx(panTxTyRef.current.tx + dx);
		setTy(panTxTyRef.current.ty + dy);
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
