'use client'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <html>
      <body className="flex flex-col items-center justify-center min-h-screen bg-background text-text-primary px-6 text-center">
        <p className="text-4xl mb-4">⚠</p>
        <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
        <p className="text-sm text-text-muted mb-6 max-w-md">{error.message || 'An unexpected error occurred.'}</p>
        <button
          onClick={reset}
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
        >
          Try again
        </button>
      </body>
    </html>
  )
}
