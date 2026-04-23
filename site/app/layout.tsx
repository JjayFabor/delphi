import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' })

export const metadata: Metadata = {
  title: { default: 'Delphi', template: '%s | Delphi' },
  description: 'Your personal AI agent. Self-hosted. Built on the Claude Agent SDK.',
  icons: {
    icon: [{ url: '/logo-icon.svg', type: 'image/svg+xml' }],
    apple: '/logo-icon.svg',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <Nav />
          {children}
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  )
}
