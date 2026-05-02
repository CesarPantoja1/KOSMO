import RootNavbar from '@/widgets/root-navbar/ui/RootNavbar';

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<>
			<RootNavbar />
			{children}
		</>
	);
}
