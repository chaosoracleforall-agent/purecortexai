import { notFound } from 'next/navigation';
import { getDocBySlug, getAllDocSlugs } from '@/lib/docs';
import type { Metadata } from 'next';

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const slugs = getAllDocSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const doc = await getDocBySlug(slug);
  if (!doc) return { title: 'Not Found' };
  return {
    title: `${doc.title} | PureCortex Docs`,
    description: doc.description,
  };
}

export default async function DocPage({ params }: Props) {
  const { slug } = await params;
  const doc = await getDocBySlug(slug);
  if (!doc) notFound();

  return (
    <article className="prose prose-invert prose-lg max-w-none prose-headings:font-black prose-headings:uppercase prose-headings:tracking-tighter prose-h1:text-4xl prose-h1:italic prose-h2:text-2xl prose-h2:border-b prose-h2:border-white/5 prose-h2:pb-3 prose-h3:text-xl prose-a:text-[#007AFF] prose-a:no-underline hover:prose-a:underline prose-code:text-[#007AFF] prose-code:bg-[#1A1A1A] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-pre:bg-[#0D0D0D] prose-pre:border prose-pre:border-white/5 prose-pre:rounded-xl prose-table:text-sm prose-th:text-[10px] prose-th:uppercase prose-th:tracking-widest prose-th:text-gray-500 prose-td:border-white/5 prose-th:border-white/5 prose-strong:text-white prose-blockquote:border-[#007AFF]">
      <div
        dangerouslySetInnerHTML={{ __html: doc.contentHtml }}
      />
    </article>
  );
}
