import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { RiArticleLine, RiTimeLine, RiCalendarLine, RiArrowRightLine } from "react-icons/ri";
import { HiSparkles } from "react-icons/hi2";
import { BLOG_POSTS } from "../../data/blogPosts";

export const metadata: Metadata = {
  title: "Engineering Blog | Autonomous Web QA & Regression Testing Insights",
  description:
    "Explore in-depth articles, guides, and engineering breakthroughs in automated web testing, synthetic user simulation, multi-viewport verification, and defect triage.",
  openGraph: {
    title: "Engineering Blog | JASUSS.TECH",
    description:
      "Deep technical insights on autonomous web QA, multi-viewport auditing, and synthetic regression testing.",
    url: "https://www.jasuss.tech/blog",
    siteName: "JASUSS.TECH",
    type: "website",
  },
  alternates: {
    canonical: "https://www.jasuss.tech/blog",
  },
};

export default function BlogIndexPage() {
  const [featured, ...recentPosts] = BLOG_POSTS;

  return (
    <div style={S.container}>
      {/* Header */}
      <header style={S.header}>
        <div style={S.badge}>
          <HiSparkles size={15} style={{ marginRight: 6 }} />
          ENGINEERING &amp; ARCHITECTURE BLOG
        </div>
        <h1 style={S.title}>
          Insights on Autonomous <span style={S.gradientText}>Web Quality Assurance</span>
        </h1>
        <p style={S.subtitle}>
          In-depth guides, architectural analyses, and technical methodologies for automated multi-viewport testing, synthetic user simulation, and continuous regression audits.
        </p>
      </header>

      {/* Featured Article */}
      {featured && (
        <section style={S.featuredSection}>
          <div style={S.featuredCard}>
            <div style={S.featuredContent}>
              <div style={S.metaRow}>
                <span style={S.categoryBadge}>{featured.category}</span>
                <span style={S.metaItem}><RiCalendarLine size={14} style={{ marginRight: 4 }} /> {featured.publishedAt}</span>
                <span style={S.metaItem}><RiTimeLine size={14} style={{ marginRight: 4 }} /> {featured.readingTime}</span>
              </div>
              <h2 style={S.featuredTitle}>
                <Link href={`/blog/${featured.slug}`} style={S.link}>
                  {featured.title}
                </Link>
              </h2>
              <p style={S.featuredExcerpt}>{featured.excerpt}</p>
              <div style={S.tagRow}>
                {featured.tags.map((tag) => (
                  <span key={tag} style={S.tag}>#{tag}</span>
                ))}
              </div>
              <div style={S.footerRow}>
                <div style={S.authorBox}>
                  <img src={featured.author.avatar} alt={featured.author.name} style={S.authorAvatar} />
                  <div>
                    <div style={S.authorName}>{featured.author.name}</div>
                    <div style={S.authorRole}>{featured.author.role}</div>
                  </div>
                </div>
                <Link href={`/blog/${featured.slug}`} style={S.readBtn}>
                  Read Article <RiArrowRightLine size={16} style={{ marginLeft: 6 }} />
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Recent Posts Grid */}
      <section style={S.gridSection}>
        <h2 style={S.sectionHeading}>
          <RiArticleLine size={20} style={{ marginRight: 8, verticalAlign: "middle" }} />
          Latest Publications
        </h2>
        <div style={S.postsGrid}>
          {recentPosts.map((post) => (
            <article key={post.slug} style={S.card}>
              <div style={S.cardBody}>
                <div style={S.metaRow}>
                  <span style={S.categoryBadge}>{post.category}</span>
                  <span style={S.metaItem}><RiTimeLine size={13} style={{ marginRight: 4 }} /> {post.readingTime}</span>
                </div>
                <h3 style={S.cardTitle}>
                  <Link href={`/blog/${post.slug}`} style={S.link}>
                    {post.title}
                  </Link>
                </h3>
                <p style={S.cardExcerpt}>{post.excerpt}</p>
                <div style={S.tagRow}>
                  {post.tags.slice(0, 3).map((tag) => (
                    <span key={tag} style={S.tag}>#{tag}</span>
                  ))}
                </div>
              </div>
              <div style={S.cardFooter}>
                <div style={S.cardDate}>{post.publishedAt}</div>
                <Link href={`/blog/${post.slug}`} style={S.cardReadLink}>
                  Read More <RiArrowRightLine size={14} style={{ marginLeft: 4 }} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

const S: Record<string, React.CSSProperties> = {
  container: {
    width: "100%",
    maxWidth: "1160px",
    margin: "0 auto",
    padding: "36px 0 80px",
  },
  header: {
    textAlign: "center",
    marginBottom: "48px",
    padding: "0 16px",
  },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 14px",
    borderRadius: "20px",
    backgroundColor: "rgba(99, 102, 241, 0.12)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    color: "#a5b4fc",
    fontSize: "0.78rem",
    fontWeight: 700,
    letterSpacing: "0.06em",
    marginBottom: "16px",
  },
  title: {
    fontSize: "clamp(2rem, 4.5vw, 3.2rem)",
    fontWeight: 800,
    color: "#f8fafc",
    lineHeight: 1.2,
    letterSpacing: "-0.02em",
    maxWidth: "850px",
    margin: "0 auto 16px",
  },
  gradientText: {
    background: "linear-gradient(135deg, #818cf8 0%, #38bdf8 100%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  subtitle: {
    fontSize: "clamp(0.95rem, 2vw, 1.15rem)",
    color: "#94a3b8",
    maxWidth: "680px",
    margin: "0 auto",
    lineHeight: 1.6,
  },
  featuredSection: {
    marginBottom: "52px",
    padding: "0 8px",
  },
  featuredCard: {
    background: "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    borderRadius: "22px",
    padding: "clamp(24px, 4vw, 40px)",
    boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.5), 0 0 25px rgba(99, 102, 241, 0.12)",
  },
  featuredContent: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  metaRow: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    flexWrap: "wrap",
  },
  categoryBadge: {
    fontSize: "0.74rem",
    fontWeight: 700,
    padding: "3px 10px",
    borderRadius: "14px",
    backgroundColor: "rgba(56, 189, 248, 0.12)",
    color: "#38bdf8",
    border: "1px solid rgba(56, 189, 248, 0.25)",
  },
  metaItem: {
    fontSize: "0.78rem",
    color: "#94a3b8",
    display: "inline-flex",
    alignItems: "center",
  },
  featuredTitle: {
    fontSize: "clamp(1.4rem, 3vw, 2.1rem)",
    fontWeight: 700,
    lineHeight: 1.3,
    color: "#ffffff",
    margin: 0,
  },
  featuredExcerpt: {
    fontSize: "1rem",
    lineHeight: 1.6,
    color: "#cbd5e1",
    margin: 0,
  },
  tagRow: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap",
    marginTop: "4px",
  },
  tag: {
    fontSize: "0.75rem",
    color: "#64748b",
  },
  footerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: "16px",
    paddingTop: "20px",
    borderTop: "1px solid rgba(255, 255, 255, 0.08)",
    flexWrap: "wrap",
    gap: "16px",
  },
  authorBox: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  authorAvatar: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    border: "1px solid rgba(255, 255, 255, 0.15)",
  },
  authorName: {
    fontSize: "0.86rem",
    fontWeight: 600,
    color: "#f8fafc",
  },
  authorRole: {
    fontSize: "0.74rem",
    color: "#64748b",
  },
  readBtn: {
    display: "inline-flex",
    alignItems: "center",
    padding: "10px 20px",
    borderRadius: "10px",
    backgroundColor: "#6366f1",
    color: "#ffffff",
    fontSize: "0.88rem",
    fontWeight: 600,
    textDecoration: "none",
    boxShadow: "0 4px 14px rgba(99, 102, 241, 0.35)",
  },
  gridSection: {
    marginTop: "20px",
    padding: "0 8px",
  },
  sectionHeading: {
    fontSize: "1.45rem",
    fontWeight: 700,
    color: "#f8fafc",
    marginBottom: "24px",
  },
  postsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 320px), 1fr))",
    gap: "24px",
  },
  card: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    backgroundColor: "rgba(15, 23, 42, 0.75)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "16px",
    padding: "24px",
    backdropFilter: "blur(14px)",
    transition: "transform 0.2s ease, border-color 0.2s ease",
  },
  cardBody: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  cardTitle: {
    fontSize: "1.18rem",
    fontWeight: 700,
    color: "#ffffff",
    lineHeight: 1.4,
    margin: 0,
  },
  cardExcerpt: {
    fontSize: "0.88rem",
    color: "#94a3b8",
    lineHeight: 1.55,
    margin: 0,
  },
  cardFooter: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: "20px",
    paddingTop: "16px",
    borderTop: "1px solid rgba(255, 255, 255, 0.06)",
  },
  cardDate: {
    fontSize: "0.78rem",
    color: "#64748b",
  },
  cardReadLink: {
    fontSize: "0.84rem",
    fontWeight: 600,
    color: "#818cf8",
    display: "inline-flex",
    alignItems: "center",
  },
  link: {
    color: "inherit",
    textDecoration: "none",
  },
};
