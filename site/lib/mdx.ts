import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'

const CONTENT_ROOT = path.join(process.cwd(), 'content')

export interface DocFrontmatter {
  title: string
  description?: string
}

export interface Heading {
  id: string
  text: string
  level: number
}

export interface DocMeta {
  frontmatter: DocFrontmatter
  rawContent: string
  headings: Heading[]
}

export function extractHeadings(md: string): Heading[] {
  const re = /^(#{1,3})\s+(.+)$/gm
  const headings: Heading[] = []
  let match
  while ((match = re.exec(md)) !== null) {
    const level = match[1].length
    const text = match[2].trim()
    const id = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/_/g, '-')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
    headings.push({ id, text, level })
  }
  return headings
}

export function getAllSlugsFromDir(dir: string): string[][] {
  const result: string[][] = []

  function walk(current: string, base: string) {
    const entries = fs.readdirSync(current, { withFileTypes: true })
    for (const entry of entries) {
      const full = path.join(current, entry.name)
      if (entry.isDirectory()) {
        walk(full, base)
      } else if (entry.name.endsWith('.mdx')) {
        const rel = path.relative(base, full).replace(/\.mdx$/, '')
        result.push(rel.split(path.sep))
      }
    }
  }

  walk(dir, dir)
  return result
}

export function getAllSlugs(section: 'docs' | 'api'): string[][] {
  const dir = path.join(CONTENT_ROOT, section)
  if (!fs.existsSync(dir)) return []
  return getAllSlugsFromDir(dir)
}

export function getDocMeta(section: 'docs' | 'api', slug: string[]): DocMeta | null {
  const filePath = path.join(CONTENT_ROOT, section, ...slug) + '.mdx'
  const resolved = path.resolve(filePath)
  if (!resolved.startsWith(CONTENT_ROOT + path.sep)) return null
  if (!fs.existsSync(filePath)) return null

  const raw = fs.readFileSync(filePath, 'utf-8')
  const { content, data } = matter(raw)

  return {
    frontmatter: data as DocFrontmatter,
    rawContent: content,
    headings: extractHeadings(content),
  }
}
