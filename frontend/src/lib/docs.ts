import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkRehype from 'remark-rehype';
import rehypeHighlight from 'rehype-highlight';
import rehypeSanitize from 'rehype-sanitize';
import rehypeStringify from 'rehype-stringify';

const docsDirectory = path.join(process.cwd(), 'src/content/docs');

export interface DocData {
  slug: string;
  title: string;
  description: string;
  contentHtml: string;
}

export function getAllDocSlugs(): string[] {
  const fileNames = fs.readdirSync(docsDirectory);
  return fileNames
    .filter((f) => f.endsWith('.md'))
    .map((f) => f.replace(/\.md$/, ''));
}

export async function getDocBySlug(slug: string): Promise<DocData | null> {
  if (!/^[a-z0-9-]+$/.test(slug)) return null;

  const fullPath = path.join(docsDirectory, `${slug}.md`);
  if (!fs.existsSync(fullPath)) return null;

  const fileContents = fs.readFileSync(fullPath, 'utf8');
  const { data, content } = matter(fileContents);

  const processed = await unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype)
    .use(rehypeHighlight)
    .use(rehypeSanitize)
    .use(rehypeStringify)
    .process(content);

  const contentHtml = processed.toString();

  return {
    slug,
    title: (data.title as string) || slug.toUpperCase(),
    description: (data.description as string) || '',
    contentHtml,
  };
}
