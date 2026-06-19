import './globals.css';
import localFont from 'next/font/local';
import { ThemeProvider } from 'app/providers/theme-provider';
import { ToasterProvider } from '@/shared/ui/toast';

const geistSans = localFont({
	src: [
		{
			path: '../public/fonts/Geist/Geist-VariableFont_wght.ttf',
			weight: '100 900',
			style: 'normal',
		},
		{
			path: '../public/fonts/Geist/Geist-Italic-VariableFont_wght.ttf',
			weight: '100 900',
			style: 'italic',
		},
	],
	variable: '--font-geist',
	display: 'swap',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html lang='es' className={geistSans.variable}>
			<body>
				<ThemeProvider>
					{children}
					<ToasterProvider />
				</ThemeProvider>
			</body>
		</html>
	);
}
