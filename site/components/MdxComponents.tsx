import Callout from './Callout'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const mdxComponents: Record<string, React.ComponentType<any>> = {
  // Callout shortcodes
  Note:    ({ children }: { children: React.ReactNode }) => <Callout type="note">{children}</Callout>,
  Warning: ({ children }: { children: React.ReactNode }) => <Callout type="warning">{children}</Callout>,
  Danger:  ({ children }: { children: React.ReactNode }) => <Callout type="danger">{children}</Callout>,

  // Block elements
  pre: ({ children, ...props }: React.HTMLProps<HTMLPreElement>) => (
    <pre
      className="overflow-x-auto rounded-lg border border-border bg-code-bg p-4 my-4 text-sm font-mono"
      {...props}
    >
      {children}
    </pre>
  ),
  blockquote: ({ children }: { children: React.ReactNode }) => (
    <blockquote className="border-l-4 border-accent pl-4 my-4 text-text-muted italic">
      {children}
    </blockquote>
  ),

  // Inline elements
  code: ({ children, ...props }: React.HTMLProps<HTMLElement>) => (
    <code
      className="font-mono text-sm bg-code-bg text-accent px-1.5 py-0.5 rounded"
      {...props}
    >
      {children}
    </code>
  ),
  a: ({ href, children, ...props }: React.HTMLProps<HTMLAnchorElement>) => (
    <a
      href={href}
      className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
      {...props}
    >
      {children}
    </a>
  ),

  // Headings
  h1: ({ children, id }: React.HTMLProps<HTMLHeadingElement>) => (
    <h1 id={id} className="text-3xl font-bold text-text-primary mt-8 mb-4 scroll-mt-20">{children}</h1>
  ),
  h2: ({ children, id }: React.HTMLProps<HTMLHeadingElement>) => (
    <h2 id={id} className="text-xl font-semibold text-text-primary mt-8 mb-3 border-b border-border pb-2 scroll-mt-20">{children}</h2>
  ),
  h3: ({ children, id }: React.HTMLProps<HTMLHeadingElement>) => (
    <h3 id={id} className="text-base font-semibold text-text-primary mt-6 mb-2 scroll-mt-20">{children}</h3>
  ),

  // Typography
  p:  ({ children }: { children: React.ReactNode }) => (
    <p className="text-text-primary leading-relaxed my-4">{children}</p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul className="list-disc pl-6 my-4 space-y-1.5 text-text-primary">{children}</ul>
  ),
  ol: ({ children }: { children: React.ReactNode }) => (
    <ol className="list-decimal pl-6 my-4 space-y-1.5 text-text-primary">{children}</ol>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li className="leading-relaxed text-sm">{children}</li>
  ),

  // Tables
  table: ({ children }: { children: React.ReactNode }) => (
    <div className="overflow-x-auto my-6 rounded-lg border border-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }: { children: React.ReactNode }) => (
    <thead className="bg-surface border-b border-border">{children}</thead>
  ),
  th: ({ children }: { children: React.ReactNode }) => (
    <th className="px-4 py-2.5 text-left font-semibold text-text-muted">{children}</th>
  ),
  td: ({ children }: { children: React.ReactNode }) => (
    <td className="px-4 py-2.5 text-text-primary border-b border-border last:border-0">{children}</td>
  ),
  tr: ({ children }: { children: React.ReactNode }) => (
    <tr className="border-b border-border last:border-0 hover:bg-surface/50 transition-colors">{children}</tr>
  ),
}
