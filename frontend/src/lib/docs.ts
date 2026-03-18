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

export interface DocHeading {
  id: string;
  text: string;
  level: number;
}

export interface DocData {
  slug: string;
  title: string;
  description: string;
  contentHtml: string;
  headings: DocHeading[];
}

function slugifyHeading(value: string): string {
  return value
    .toLowerCase()
    .replace(/[`*_~]/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/&[a-z]+;/gi, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');
}

function stripInlineMarkdown(value: string): string {
  return value
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*_~]/g, '')
    .trim();
}

function extractHeadings(markdown: string): DocHeading[] {
  const headings: DocHeading[] = [];
  const seen = new Map<string, number>();
  let inCodeFence = false;

  for (const line of markdown.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('```')) {
      inCodeFence = !inCodeFence;
      continue;
    }
    if (inCodeFence) {
      continue;
    }

    const match = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (!match) {
      continue;
    }

    const level = match[1].length;
    const text = stripInlineMarkdown(match[2]);
    const baseId = slugifyHeading(text) || `section-${headings.length + 1}`;
    const count = seen.get(baseId) ?? 0;
    seen.set(baseId, count + 1);

    headings.push({
      id: count === 0 ? baseId : `${baseId}-${count + 1}`,
      text,
      level,
    });
  }

  return headings;
}

function addHeadingAnchors(contentHtml: string, headings: DocHeading[]): string {
  let index = 0;
  return contentHtml.replace(/<h([1-3])>(.*?)<\/h\1>/g, (fullMatch, level) => {
    const heading = headings[index];
    index += 1;
    if (!heading || heading.level !== Number(level)) {
      return fullMatch;
    }
    return `<h${level} id="${heading.id}">${heading.text}</h${level}>`;
  });
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
  const headings = extractHeadings(content);

  const processed = await unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype)
    .use(rehypeHighlight)
    .use(rehypeSanitize)
    .use(rehypeStringify)
    .process(content);

  const contentHtml = addHeadingAnchors(processed.toString(), headings);

  return {
    slug,
    title: (data.title as string) || slug.toUpperCase(),
    description: (data.description as string) || '',
    contentHtml,
    headings,
  };
}
