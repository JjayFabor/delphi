import Link from 'next/link'
import HeroEye from '@/components/HeroEye'
import FeatureGrid from '@/components/FeatureGrid'
import ScrollReveal from '@/components/ScrollReveal'

const steps = [
  { n: 1, title: 'Clone & configure',          desc: 'git clone the repo and run the setup wizard. Done in under 5 minutes.' },
  { n: 2, title: 'Connect Telegram or Discord', desc: 'Create a bot via BotFather or the Discord Developer Portal, paste the token. Your agent is live.' },
  { n: 3, title: 'Start chatting',             desc: 'Name it, define its role, connect tools, and teach it your workflows — all by chatting.' },
]

export default function HomePage() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden dot-grid">
        {/* Aurora blobs */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="aurora-blob aurora-blob-1" />
          <div className="aurora-blob aurora-blob-2" />
        </div>

        <div className="relative mx-auto max-w-6xl px-6 py-20 lg:py-32">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-8 items-center">

            {/* Left — text */}
            <div className="text-center lg:text-left">
              <span
                className="inline-block text-xs font-semibold tracking-widest text-accent uppercase mb-6 fade-up"
                style={{ animationDelay: '0ms' }}
              >
                Personal AI · Self-Hosted
              </span>
              <h1
                className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight tracking-tight fade-up"
                style={{ animationDelay: '80ms' }}
              >
                <span className="gradient-text">Your personal oracle.</span>
                <br />
                <span className="text-text-primary">Self-hosted.<br />Always listening.</span>
              </h1>
              <p
                className="mt-6 text-lg md:text-xl text-text-muted leading-relaxed fade-up"
                style={{ animationDelay: '180ms' }}
              >
                Send a message from your phone. Get your own AI on the other end —
                shaped to your role, connected to your tools, and getting smarter every conversation.
              </p>
              <div
                className="mt-10 flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 fade-up"
                style={{ animationDelay: '280ms' }}
              >
                <Link
                  href="/docs/introduction"
                  className="w-full sm:w-auto px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium transition-colors text-center"
                >
                  Get Started →
                </Link>
                <a
                  href="https://github.com/JjayFabor/delphi"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full sm:w-auto px-6 py-3 rounded-lg border border-border hover:border-accent text-text-primary font-medium transition-colors text-center"
                >
                  View on GitHub
                </a>
              </div>
              <div
                className="mt-8 mx-auto lg:mx-0 max-w-lg fade-up"
                style={{ animationDelay: '360ms' }}
              >
                <pre className="bg-surface border border-border rounded-lg px-5 py-4 text-sm font-mono text-text-muted overflow-x-auto text-left">
                  <code>{`git clone https://github.com/JjayFabor/delphi.git
cd delphi
python3 scripts/setup.py`}</code>
                </pre>
              </div>
            </div>

            {/* Right — animated eye */}
            <div
              className="flex items-center justify-center lg:justify-end fade-up"
              style={{ animationDelay: '150ms' }}
            >
              <div className="w-64 h-64 sm:w-80 sm:h-80 lg:w-[380px] lg:h-[380px]">
                <HeroEye />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Origin story */}
      <section className="mx-auto max-w-3xl px-6 py-24">
        <div className="text-center mb-10" data-reveal>
          <span className="inline-block text-xs font-semibold tracking-widest text-accent uppercase mb-4">The Name</span>
          <h2 className="text-2xl md:text-3xl font-bold text-text-primary">Why Delphi?</h2>
        </div>
        <div className="space-y-5 text-text-muted leading-relaxed text-base md:text-lg" data-reveal data-delay="100">
          <p>
            At Mount Parnassus in ancient Greece stood the most important place in the known world.
            Rulers and philosophers traveled from Persia to Rome to consult the Oracle at Delphi —
            the central node through which the wisdom of the ancient world flowed.
            They would send their query across mountains and seas, and receive intelligence in return.
          </p>
          <p>The parallel is deliberate.</p>
          <p>
            You send a message from your phone. Your Delphi — running quietly on your own machine —
            receives it, searches its memory of you, consults your tools, and responds. Not a generic AI
            that forgets you when the session closes. An oracle shaped entirely around one person: you.
            One that grows sharper with every conversation, every preference you teach it, every tool you connect.
          </p>
          <p>The ancient Oracle served one truth at a time. Yours serves one person.</p>
          <p className="text-sm text-text-muted/60 italic border-l-2 border-accent/30 pl-4">
            Inscribed above the entrance to the Temple of Apollo at Delphi:{' '}
            <span className="not-italic font-medium text-text-muted">γνῶθι σαυτόν</span> — Know thyself.
            Your Delphi knows you a little better every day.
          </p>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-5xl px-6 py-12">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-12" data-reveal>
          Everything you need
        </h2>
        <FeatureGrid />
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-4xl px-6 py-24">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-16" data-reveal>
          How it works
        </h2>
        <div className="flex flex-col md:flex-row items-start gap-8 md:gap-4">
          {steps.map((step, i) => (
            <div key={step.n} className="flex-1 flex flex-col items-start gap-3" data-reveal data-delay={`${i * 150}`}>
              <div className="flex items-center gap-4 w-full">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-accent text-white text-sm font-bold flex items-center justify-center">
                  {step.n}
                </span>
                {i < steps.length - 1 && (
                  <div className="hidden md:block flex-1 h-px bg-border" />
                )}
              </div>
              <h3 className="font-semibold text-text-primary text-sm">{step.title}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <ScrollReveal />
    </main>
  )
}
