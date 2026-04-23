'use client'
import { useEffect } from 'react'

export default function Error({
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
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <p className="text-4xl mb-4">⚠</p>
      <h2 className="text-xl font-semibold text-text-primary mb-2">Something went wrong</h2>
      <p className="text-sm text-text-muted mb-6 max-w-md">{error.message || 'An unexpected error occurred.'}</p>
      <button
        onClick={reset}
        className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
      >
        Try again
      </button>
    </div>
  )
}
