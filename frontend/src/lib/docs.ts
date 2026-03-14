import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { remark } from 'remark';
import html from 'remark-html';

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
  const fullPath = path.join(docsDirectory, `${slug}.md`);
  if (!fs.existsSync(fullPath)) return null;

  const fileContents = fs.readFileSync(fullPath, 'utf8');
  const { data, content } = matter(fileContents);

  const processed = await remark().use(html).process(content);
  const contentHtml = processed.toString();

  return {
    slug,
    title: (data.title as string) || slug.toUpperCase(),
    description: (data.description as string) || '',
    contentHtml,
  };
}
