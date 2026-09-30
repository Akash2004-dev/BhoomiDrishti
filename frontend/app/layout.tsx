import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'BhoomiDrishti | Crop Evidence Review',
  description: 'A prototype for organizing crop damage evidence for human review.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
