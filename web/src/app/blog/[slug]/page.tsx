import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RiArrowLeftLine, RiTimeLine, RiCalendarLine, RiShareForwardLine } from "react-icons/ri";
import { TbSparkles, TbArrowRight } from "react-icons/tb";
import { BLOG_POSTS, type BlogPost } from "../../../data/blogPosts";

export const dynamicParams = true;
export const revalidate = 15;

async function getPostBySlug(slug: string): Promise<BlogPost | null> {
  const apiUrl = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
  try {
    const res = await fetch(`${apiUrl}/api/v1/blogs/${encodeURIComponent(slug)}`, {
      next: { revalidate: 10 },
    });
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
  const apiUrl = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
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

  return (
    <article style={S.container}>
      {/* Structured Schema for Search Engines */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Back button */}
      <div style={S.backRow}>
        <Link href="/blog" style={S.backLink}>
          <RiArrowLeftLine size={16} style={{ marginRight: 6 }} />
          Back to all articles
        </Link>
      </div>

      {/* Header */}
      <header style={S.header}>
        <div style={S.metaTop}>
          <span style={S.categoryBadge}>{post.category}</span>
          <span style={S.metaItem}><RiCalendarLine size={14} style={{ marginRight: 4 }} /> {post.publishedAt}</span>
          <span style={S.metaItem}><RiTimeLine size={14} style={{ marginRight: 4 }} /> {post.readingTime}</span>
        </div>
        <h1 style={S.title}>{post.title}</h1>
        <p style={S.leadText}>{post.excerpt}</p>

        {/* Author info */}
        <div style={S.authorCard}>
          <img src={post.author.avatar} alt={post.author.name} style={S.authorAvatar} />
          <div>
            <div style={S.authorName}>{post.author.name}</div>
            <div style={S.authorRole}>{post.author.role}</div>
          </div>
        </div>
      </header>

      {/* Article Content */}
      <div style={S.contentWrapper}>
        {post.content.map((paragraph, index) => {
          if (paragraph.startsWith("### ")) {
            return (
              <h2 key={index} style={S.h2}>
                {paragraph.replace("### ", "")}
              </h2>
            );
          }
          if (paragraph.startsWith("- ")) {
            return (
              <li key={index} style={S.listItem}>
                {paragraph.replace("- ", "")}
              </li>
            );
          }
          if (/^\d+\.\s/.test(paragraph)) {
            return (
              <p key={index} style={S.orderedItem}>
                {paragraph}
              </p>
            );
          }
          return (
            <p key={index} style={S.paragraph}>
              {paragraph}
            </p>
          );
        })}
      </div>

      {/* Tags */}
      <div style={S.tagSection}>
        <span style={S.tagLabel}>Topics:</span>
        {post.tags.map((tag) => (
          <span key={tag} style={S.tagPill}>
            #{tag}
          </span>
        ))}
      </div>

      {/* Bottom CTA Banner */}
      <section style={S.ctaSection}>
        <div style={S.ctaBadge}>
          <TbSparkles size={14} style={{ marginRight: 4 }} />
          START CONTINUOUS TESTING
        </div>
        <h3 style={S.ctaTitle}>Experience Autonomous Web QA in Action</h3>
        <p style={S.ctaDesc}>
          Enter your URL to launch an automated multi-viewport crawl with synthetic interaction testing and executive defect grading.
        </p>
        <Link href="/dashboard" style={S.ctaBtn}>
          Run Free Website Scan <TbArrowRight size={18} style={{ marginLeft: 6 }} />
        </Link>
      </section>
    </article>
  );
}

const S: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "820px",
    margin: "0 auto",
    padding: "32px 16px 80px",
  },
  backRow: {
    marginBottom: "28px",
  },
  backLink: {
    display: "inline-flex",
    alignItems: "center",
    color: "#818cf8",
    fontSize: "0.88rem",
    fontWeight: 600,
    textDecoration: "none",
  },
  header: {
    marginBottom: "40px",
    borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
    paddingBottom: "32px",
  },
  metaTop: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    flexWrap: "wrap",
    marginBottom: "16px",
  },
  categoryBadge: {
    fontSize: "0.76rem",
    fontWeight: 700,
    padding: "3px 10px",
    borderRadius: "14px",
    backgroundColor: "rgba(99, 102, 241, 0.14)",
    color: "#a5b4fc",
    border: "1px solid rgba(99, 102, 241, 0.25)",
  },
  metaItem: {
    fontSize: "0.8rem",
    color: "#94a3b8",
    display: "inline-flex",
    alignItems: "center",
  },
  title: {
    fontSize: "clamp(1.8rem, 4vw, 2.7rem)",
    fontWeight: 800,
    color: "#ffffff",
    lineHeight: 1.25,
    letterSpacing: "-0.02em",
    margin: "0 0 16px",
  },
  leadText: {
    fontSize: "clamp(1.05rem, 2vw, 1.2rem)",
    color: "#cbd5e1",
    lineHeight: 1.6,
    margin: "0 0 24px",
  },
  authorCard: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  authorAvatar: {
    width: "42px",
    height: "42px",
    borderRadius: "50%",
    border: "1px solid rgba(255, 255, 255, 0.15)",
  },
  authorName: {
    fontSize: "0.92rem",
    fontWeight: 700,
    color: "#f8fafc",
  },
  authorRole: {
    fontSize: "0.78rem",
    color: "#64748b",
  },
  contentWrapper: {
    display: "flex",
    flexDirection: "column",
    gap: "20px",
    fontSize: "1.02rem",
    lineHeight: 1.8,
    color: "#e2e8f0",
  },
  h2: {
    fontSize: "1.55rem",
    fontWeight: 700,
    color: "#ffffff",
    margin: "24px 0 8px",
    letterSpacing: "-0.01em",
  },
  paragraph: {
    margin: 0,
  },
  listItem: {
    marginLeft: "20px",
    lineHeight: 1.7,
  },
  orderedItem: {
    margin: 0,
    lineHeight: 1.7,
  },
  tagSection: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    flexWrap: "wrap",
    marginTop: "44px",
    paddingTop: "24px",
    borderTop: "1px solid rgba(255, 255, 255, 0.08)",
  },
  tagLabel: {
    fontSize: "0.82rem",
    fontWeight: 700,
    color: "#64748b",
  },
  tagPill: {
    fontSize: "0.8rem",
    fontWeight: 500,
    padding: "4px 10px",
    borderRadius: "8px",
    backgroundColor: "rgba(255, 255, 255, 0.04)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    color: "#94a3b8",
  },
  ctaSection: {
    marginTop: "60px",
    padding: "clamp(24px, 4vw, 36px)",
    borderRadius: "20px",
    background: "linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%)",
    border: "1px solid rgba(99, 102, 241, 0.35)",
    textAlign: "center",
    boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.5)",
  },
  ctaBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "4px 12px",
    borderRadius: "16px",
    backgroundColor: "rgba(16, 185, 129, 0.12)",
    border: "1px solid rgba(16, 185, 129, 0.28)",
    color: "#34d399",
    fontSize: "0.75rem",
    fontWeight: 700,
    marginBottom: "12px",
  },
  ctaTitle: {
    fontSize: "clamp(1.3rem, 3vw, 1.8rem)",
    fontWeight: 700,
    color: "#ffffff",
    margin: "0 0 10px",
  },
  ctaDesc: {
    fontSize: "0.95rem",
    color: "#94a3b8",
    maxWidth: "540px",
    margin: "0 auto 22px",
    lineHeight: 1.55,
  },
  ctaBtn: {
    display: "inline-flex",
    alignItems: "center",
    padding: "12px 26px",
    borderRadius: "12px",
    backgroundColor: "#6366f1",
    color: "#ffffff",
    fontSize: "0.92rem",
    fontWeight: 700,
    textDecoration: "none",
    boxShadow: "0 4px 18px rgba(99, 102, 241, 0.4)",
  },
};
