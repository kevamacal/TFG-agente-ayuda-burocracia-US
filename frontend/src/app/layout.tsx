import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Asistente Académico US",
  description: "Asistente inteligente RAG para la Universidad de Sevilla",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="dark">
      <body className={`${inter.variable} font-sans antialiased text-white bg-background`}>
        {children}
      </body>
    </html>
  );
}
