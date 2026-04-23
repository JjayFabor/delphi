'use client'
import { useEffect, useRef } from 'react'

export default function HeroEye() {
  const containerRef = useRef<HTMLDivElement>(null)
  const pupilRef = useRef<SVGGElement>(null)

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      const el = containerRef.current
      const pupil = pupilRef.current
      if (!el || !pupil) return
      const rect = el.getBoundingClientRect()
      const cx = rect.left + rect.width / 2
      const cy = rect.top + rect.height / 2
      const dx = e.clientX - cx
      const dy = e.clientY - cy
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const factor = Math.min(dist / 320, 1)
      const max = 14
      const x = (dx / dist) * factor * max
      const y = (dy / dist) * factor * max
      pupil.style.transform = `translate(${x}px, ${y}px)`
    }
    window.addEventListener('mousemove', handleMove, { passive: true })
    return () => window.removeEventListener('mousemove', handleMove)
  }, [])

  return (
    <div ref={containerRef} className="hero-eye-wrap">
      <div className="hero-eye-aura" />
      <svg viewBox="0 0 200 200" className="hero-eye-svg" aria-hidden="true">
        <defs>
          <linearGradient id="hg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0ea5e9" />
            <stop offset="100%" stopColor="#7c6af7" />
          </linearGradient>
          <filter id="eye-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer faint halo */}
        <ellipse
          cx="100" cy="100" rx="90" ry="57"
          fill="none" stroke="url(#hg)" strokeWidth="0.6" opacity="0.25"
        />

        {/* Eye lens — breathing via CSS */}
        <path
          className="eye-lens-path"
          d="M 15 100 C 50 38 150 38 185 100 C 150 162 50 162 15 100 Z"
          stroke="url(#hg)" strokeWidth="3" fill="none"
          strokeLinejoin="round" filter="url(#eye-glow)"
        />

        {/* Corner tail mark */}
        <path d="M 28 132 L 14 162 L 48 148" fill="url(#hg)" />

        {/* Cardinal node dots */}
        <circle cx="15"  cy="100" r="5" fill="#0ea5e9" />
        <circle cx="185" cy="100" r="5" fill="#7c6af7" />
        <circle cx="100" cy="33"  r="5" fill="#0ea5e9" />
        <circle cx="100" cy="167" r="5" fill="#7c6af7" />

        {/* Pupil — direct DOM manipulation, no re-renders */}
        <g ref={pupilRef} style={{ transition: 'transform 0.06s linear' }}>
          <path d="M 100 74 L 116 100 L 100 126 L 84 100 Z" fill="#38bdf8" opacity="0.95" />
          <circle cx="100" cy="100" r="7.5" fill="url(#hg)" />
          <circle cx="97"  cy="97"  r="2.5" fill="white" opacity="0.35" />
        </g>
      </svg>
    </div>
  )
}
