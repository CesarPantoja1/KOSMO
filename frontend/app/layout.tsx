import { Metadata } from 'next';
import { ToasterProvider } from '@/shared/ui';
import localFont from 'next/font/local';
import './globals.css';

export const metadata: Metadata = {
	title: {
		default: 'KOSMO',
		template: '%s | KOSMO',
	},
	description: 'Plataforma de gestión de proyectos KOSMO',
	icons: {
		icon: './kosmo.png',
	},
};

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
		<html lang='es' className={`${geistSans.variable} h-full`}>
			<body className='h-full'>
				{children}
				<ToasterProvider />
			</body>
		</html>
	);
}
