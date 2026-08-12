export function normalizeDiff(diffBefore: string, diffAfter: string): { before: string; after: string } {
	if (
		diffBefore &&
		diffAfter &&
		diffAfter.startsWith(diffBefore) &&
		diffAfter.length > diffBefore.length
	) {
		return { before: '', after: diffAfter.slice(diffBefore.length).trim() };
	}

	if (diffBefore && diffAfter) {
		let commonPrefix = 0;
		while (
			commonPrefix < diffBefore.length &&
			commonPrefix < diffAfter.length &&
			diffBefore[commonPrefix] === diffAfter[commonPrefix]
		) {
			commonPrefix++;
		}
		if (commonPrefix > 0) {
			const remainingBefore = diffBefore.slice(commonPrefix);
			const remainingAfter = diffAfter.slice(commonPrefix);
			const resumeIdx = remainingAfter.indexOf(remainingBefore);
			if (resumeIdx > 0) {
				const inserted = remainingAfter.slice(0, resumeIdx).trim();
				if (inserted) {
					return { before: '', after: inserted };
				}
			}
		}
	}

	return { before: diffBefore, after: diffAfter };
}
