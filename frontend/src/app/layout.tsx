import '@/styles/globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'SkillGraph - AI Workforce Intelligence Platform',
  description: 'AI-powered Heterogeneous Knowledge Graph mapping skills, careers, and workforce intelligence.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="neon-grid">
        {children}
      </body>
    </html>
  )
}
