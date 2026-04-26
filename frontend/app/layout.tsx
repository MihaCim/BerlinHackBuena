import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Buena Context Engine",
  description: "Dynamic Next.js frontend for the Buena Context Engine"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
