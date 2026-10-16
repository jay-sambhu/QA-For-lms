import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RiArrowLeftLine, RiTimeLine, RiCalendarLine } from "react-icons/ri";
import { TbSparkles, TbArrowRight, TbGift } from "react-icons/tb";
import { serverApiBase } from "../../../lib/serverApiBase";
import { BLOG_POSTS, type BlogPost } from "../../../data/blogPosts";
import { PageHeader3D, Surface3D } from "../../../components/three";
import c from "../../content3d.module.css";

export const dynamicParams = true;
export const revalidate = 15;

async function getPostBySlug(slug: string): Promise<BlogPost | null> {
  const apiUrl = serverApiBase();
  try {
    const res = await fetch(`${apiUrl}/api/v1/blogs/${encodeURIComponent(slug)}`, {
      next: { revalidate: 10 },
    });
    // Backend is the source of truth (it seeds the static posts): a 404 means the post was
    // unpublished or deleted, so don't resurrect it from the static fallback.
    if (res.status === 404) return null;
    if (res.ok) {
      const data = await res.json();
      if (data.post) {
        return data.post;
      }
    }
  } catch (err) {
    console.error(`Failed to fetch dynamic blog for ${slug}:`, err);
  }
  return BLOG_POSTS.find((p) => p.slug === slug) || null;
}

interface BlogPostPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export async function generateStaticParams() {
  const apiUrl = serverApiBase();
  try {
    const res = await fetch(`${apiUrl}/api/v1/blogs?limit=100`, { next: { revalidate: 60 } });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.posts) && data.posts.length > 0) {
        return data.posts.map((post: BlogPost) => ({ slug: post.slug }));
      }
    }
  } catch {
    // fallback to static list
  }
  return BLOG_POSTS.map((post) => ({
    slug: post.slug,
  }));
}

export async function generateMetadata({ params }: BlogPostPageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  if (!post) {
    return {
      title: "Article Not Found | JASUSS.TECH",
    };
  }

  const url = `https://www.jasuss.tech/blog/${post.slug}`;

  return {
    title: `${post.title} | JASUSS.TECH Engineering`,
    description: post.excerpt,
    keywords: post.tags,
    authors: [{ name: post.author.name }],
    alternates: {
      canonical: url,
    },
    openGraph: {
      title: post.title,
      description: post.excerpt,
      url,
      type: "article",
      publishedTime: post.publishedAt,
      authors: [post.author.name],
      tags: post.tags,
      siteName: "JASUSS.TECH",
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.excerpt,
    },
  };
}

type Block =
  | { kind: "h2"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "step"; text: string }
  | { kind: "p"; text: string };

function toBlocks(content: string[]): Block[] {
  const blocks: Block[] = [];
  for (const paragraph of content) {
    if (paragraph.startsWith("### ")) {
      blocks.push({ kind: "h2", text: paragraph.replace("### ", "") });
    } else if (paragraph.startsWith("- ")) {
      const last = blocks[blocks.length - 1];
      const item = paragraph.replace("- ", "");
      if (last && last.kind === "list") last.items.push(item);
      else blocks.push({ kind: "list", items: [item] });
    } else if (/^\d+\.\s/.test(paragraph)) {
      blocks.push({ kind: "step", text: paragraph });
    } else {
      blocks.push({ kind: "p", text: paragraph });
    }
  }
  return blocks;
}

export default async function BlogPostPage({ params }: BlogPostPageProps) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  if (!post) {
    notFound();
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    headline: post.title,
    description: post.excerpt,
    datePublished: post.publishedAt,
    author: {
      "@type": "Person",
      name: post.author.name,
      jobTitle: post.author.role,
    },
    publisher: {
      "@type": "Organization",
      name: "JASUSS.TECH",
      logo: {
        "@type": "ImageObject",
        url: "https://www.jasuss.tech/logo.png",
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://www.jasuss.tech/blog/${post.slug}`,
    },
    keywords: post.tags.join(", "),
  };

  const blocks = toBlocks(post.content);

  return (
    <div className="page-shell">
      {/* Structured Schema for Search Engines */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />

      <div className="enter-3d">
        <Link href="/blog" className="btn btn-secondary btn-sm">
          <RiArrowLeftLine size={16} />
          Back to all articles
        </Link>
      </div>

      <PageHeader3D
        eyebrow={post.category}
        title={post.title}
        subtitle={post.excerpt}
        className="enter-3d"
        style={{ ["--enter-delay" as string]: "60ms" } as React.CSSProperties}
      >
        <div className={c.postHeadMeta}>
          <div className={c.author}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={post.author.avatar} alt={post.author.name} className={c.authorAvatar} />
            <div>
              <div className={c.authorName}>{post.author.name}</div>
              <div className={c.authorRole}>{post.author.role}</div>
            </div>
          </div>
          <div className={c.metaRow}>
            <span className={c.metaItem}><RiCalendarLine size={14} /> {post.publishedAt}</span>
            <span className={c.metaItem}><RiTimeLine size={14} /> {post.readingTime}</span>
          </div>
        </div>
      </PageHeader3D>

      <div className={c.articleCol}>
        <Surface3D
          as="article"
          pad="lg"
          className="enter-3d"
          style={{ ["--enter-delay" as string]: "120ms" } as React.CSSProperties}
        >
          <div className={c.prose}>
            {blocks.map((block, index) => {
              if (block.kind === "h2") return <h2 key={index}>{block.text}</h2>;
              if (block.kind === "list") {
                return (
                  <ul key={index}>
                    {block.items.map((item, j) => (
                      <li key={j}>{item}</li>
                    ))}
                  </ul>
                );
              }
              if (block.kind === "step") {
                return (
                  <p key={index} className={c.step}>
                    {block.text}
                  </p>
                );
              }
              return <p key={index}>{block.text}</p>;
            })}
          </div>

          <div className={c.topics}>
            <span className={c.topicsLabel}>Topics</span>
            {post.tags.map((tag) => (
              <span key={tag} className="chip chip--neutral chip--sm">
                #{tag}
              </span>
            ))}
          </div>
        </Surface3D>

        <Surface3D
          as="section"
          ring
          pad="lg"
          className={`${c.cta} enter-3d`}
          style={{ ["--enter-delay" as string]: "180ms" } as React.CSSProperties}
          aria-labelledby="post-cta-title"
        >
          <span className="chip chip--success chip--dot">
            <TbSparkles size={13} /> Start continuous testing
          </span>
          <h3 id="post-cta-title" className={c.ctaTitle}>Experience autonomous web QA in action</h3>
          <p className={c.ctaDesc}>
            Enter your URL to launch an automated multi-viewport crawl with synthetic interaction testing and executive defect grading.
          </p>
          <div className={c.ctaActions}>
            <Link href="/dashboard" className="btn btn-primary">
              Run free website scan <TbArrowRight size={18} />
            </Link>
            <span className={c.trialNote}>
              <TbGift size={16} />
              <span><strong>Free to start</strong> during beta, no credit card required.</span>
            </span>
          </div>
        </Surface3D>
      </div>
    </div>
  );
}
