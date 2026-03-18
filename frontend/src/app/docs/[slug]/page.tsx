import { notFound } from 'next/navigation';
import { getDocBySlug, getAllDocSlugs } from '@/lib/docs';
import type { Metadata } from 'next';
import 'highlight.js/styles/github-dark.css';

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
    title: `${doc.title} | PURECORTEX Docs`,
    description: doc.description,
  };
}

export default async function DocPage({ params }: Props) {
  const { slug } = await params;
  const doc = await getDocBySlug(slug);
  if (!doc) notFound();

  return (
    <div className="space-y-8 lg:space-y-10">
      <header className="rounded-[28px] border border-white/5 bg-[#0B0B0B] px-6 py-6 sm:px-8 sm:py-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-[#007AFF]">
              Technical Wiki
            </p>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tighter uppercase italic">
              {doc.title}
            </h1>
            {doc.description ? (
              <p className="max-w-3xl text-sm sm:text-base leading-relaxed text-gray-400">
                {doc.description}
              </p>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-3 text-left sm:min-w-[320px]">
            <div className="rounded-2xl border border-white/5 bg-black/20 px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-gray-500">
                Sections
              </div>
              <div className="mt-2 text-2xl font-black tracking-tighter text-white">
                {doc.headings.filter((heading) => heading.level >= 2).length || 1}
              </div>
            </div>
            <div className="rounded-2xl border border-white/5 bg-black/20 px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-gray-500">
                Format
              </div>
              <div className="mt-2 text-sm font-bold uppercase tracking-wide text-white">
                Code + Notes
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_240px]">
        <article className="min-w-0 rounded-[28px] border border-white/5 bg-[#080808] px-6 py-6 sm:px-8 sm:py-8">
          <div className="prose prose-invert prose-lg max-w-none prose-headings:scroll-mt-28 prose-headings:font-black prose-headings:uppercase prose-headings:tracking-tighter prose-h1:text-4xl prose-h1:italic prose-h2:text-2xl prose-h2:border-b prose-h2:border-white/5 prose-h2:pb-3 prose-h3:text-xl prose-a:text-[#007AFF] prose-a:no-underline hover:prose-a:underline prose-code:text-[#7fb8ff] prose-code:bg-[#141414] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-code:before:content-none prose-code:after:content-none prose-pre:bg-[#050505] prose-pre:border prose-pre:border-white/5 prose-pre:rounded-2xl prose-pre:shadow-[0_0_0_1px_rgba(255,255,255,0.03)] prose-table:text-sm prose-th:text-[10px] prose-th:uppercase prose-th:tracking-widest prose-th:text-gray-500 prose-td:border-white/5 prose-th:border-white/5 prose-strong:text-white prose-blockquote:border-[#007AFF]">
            <div
              dangerouslySetInnerHTML={{ __html: doc.contentHtml }}
            />
          </div>
        </article>

        {doc.headings.length > 1 ? (
          <aside className="hidden xl:block">
            <div className="sticky top-28 rounded-[24px] border border-white/5 bg-[#0B0B0B] px-5 py-5">
              <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-gray-500">
                On This Page
              </p>
              <nav className="mt-4 space-y-3">
                {doc.headings
                  .filter((heading) => heading.level >= 2)
                  .map((heading) => (
                    <a
                      key={heading.id}
                      href={`#${heading.id}`}
                      className={`block text-sm transition-colors ${
                        heading.level === 2
                          ? 'font-semibold text-gray-300 hover:text-white'
                          : 'pl-3 text-gray-500 hover:text-gray-300'
                      }`}
                    >
                      {heading.text}
                    </a>
                  ))}
              </nav>
            </div>
          </aside>
        ) : null}
      </div>
    </div>
  );
}
