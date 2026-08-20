export interface FileTreeNode {
	name: string;
	path: string;
	children: FileTreeNode[];
}

export function buildFileTree(paths: string[]): FileTreeNode[] {
	const root: FileTreeNode[] = [];
	const nodesByPath = new Map<string, FileTreeNode>();
	const uniquePaths = [...new Set(paths)].sort();

	for (const path of uniquePaths) {
		const segments = path.split('/').filter(Boolean);
		let level = root;
		let currentPath = '';

		for (const segment of segments) {
			currentPath = currentPath ? `${currentPath}/${segment}` : segment;
			let node = nodesByPath.get(currentPath);
			if (!node) {
				node = { name: segment, path: currentPath, children: [] };
				nodesByPath.set(currentPath, node);
				level.push(node);
			}
			level = node.children;
		}
	}

	const sortNodes = (nodes: FileTreeNode[]) => {
		nodes.sort((a, b) => a.name.localeCompare(b.name));
		nodes.forEach((node) => sortNodes(node.children));
	};
	sortNodes(root);

	return root;
}
