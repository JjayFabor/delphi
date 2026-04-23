import { notFound } from 'next/navigation'
import { compileMDX } from 'next-mdx-remote/rsc'
import remarkGfm from 'remark-gfm'
import { getAllSlugs, getDocMeta } from '@/lib/mdx'
import { mdxComponents } from '@/components/MdxComponents'
import Toc from '@/components/Toc'
import type { Metadata } from 'next'

interface Props {
  params: { slug?: string[] }
}

export async function generateStaticParams() {
  const slugs = getAllSlugs('api')
  return [{ slug: [] as string[] }, ...slugs.map(s => ({ slug: s }))]
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = (!params.slug || params.slug.length === 0) ? ['overview'] : params.slug
  const meta = getDocMeta('api', slug)
  if (!meta) return {}
  return {
    title: meta.frontmatter.title,
    description: meta.frontmatter.description,
  }
}

export default async function ApiReferencePage({ params }: Props) {
  const slug = (!params.slug || params.slug.length === 0) ? ['overview'] : params.slug

  const meta = getDocMeta('api', slug)
  if (!meta) notFound()

  const { content } = await compileMDX({
    source: meta.rawContent,
    components: mdxComponents as any,
    options: { mdxOptions: { remarkPlugins: [remarkGfm] } },
  })

  return (
    <>
      <article className="flex-1 min-w-0 max-w-3xl">
        <h1 className="text-3xl font-bold text-text-primary mb-2">{meta.frontmatter.title}</h1>
        {meta.frontmatter.description && (
          <p className="text-text-muted mb-8 text-lg leading-relaxed">{meta.frontmatter.description}</p>
        )}
        <div>{content}</div>
      </article>
      <Toc headings={meta.headings} />
    </>
  )
}
