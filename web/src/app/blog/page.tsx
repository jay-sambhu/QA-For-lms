import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { RiArticleLine, RiTimeLine, RiCalendarLine, RiArrowRightLine } from "react-icons/ri";
import { TbSparkles } from "react-icons/tb";
import { serverApiBase } from "../../lib/serverApiBase";
import { BLOG_POSTS, type BlogPost } from "../../data/blogPosts";
import { PageHeader3D, Surface3D, EmptyState3D } from "../../components/three";
import c from "../content3d.module.css";

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

export const dynamic = "force-dynamic";

async function getDynamicBlogPosts(): Promise<BlogPost[]> {
  const apiUrl = serverApiBase();
  try {
    const res = await fetch(`${apiUrl}/api/v1/blogs?limit=50`, {
      next: { revalidate: 10 },
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.posts) && data.posts.length > 0) {
        return data.posts;
      }
    }
  } catch (err) {
    console.error("Failed to fetch dynamic blogs from backend:", err);
  }
  return BLOG_POSTS;
}

export default async function BlogIndexPage() {
  const posts = await getDynamicBlogPosts();
  const [featured, ...recentPosts] = posts;

  return (
    <div className="page-shell">
      <PageHeader3D
        eyebrow="Engineering & architecture blog"
        title={
          <>
            Insights on autonomous <span className="text-gradient">web quality assurance</span>
          </>
        }
        subtitle="In-depth guides, architectural analyses, and technical methodologies for automated multi-viewport testing, synthetic user simulation, and continuous regression audits."
        badge={`${posts.length} articles`}
      />

      {featured && (
        <Surface3D as="section" ring pad="lg" className={`${c.featured} enter-3d`} aria-labelledby="featured-title">
          <div className={c.featuredCopy}>
            <div className={c.metaRow}>
              <span className="chip chip--info">{featured.category}</span>
              <span className={c.metaItem}><RiCalendarLine size={14} /> {featured.publishedAt}</span>
              <span className={c.metaItem}><RiTimeLine size={14} /> {featured.readingTime}</span>
            </div>
            <h2 id="featured-title" className={c.featuredTitle}>
              <Link href={`/blog/${featured.slug}`} className={c.titleLink}>
                {featured.title}
              </Link>
            </h2>
            <p className={c.featuredExcerpt}>{featured.excerpt}</p>
            <div className={c.tagRow}>
              {featured.tags.map((tag) => (
                <span key={tag} className={c.tag}>#{tag}</span>
              ))}
            </div>
            <div className={c.featuredFooter}>
              <div className={c.author}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={featured.author.avatar} alt={featured.author.name} className={c.authorAvatar} />
                <div>
                  <div className={c.authorName}>{featured.author.name}</div>
                  <div className={c.authorRole}>{featured.author.role}</div>
                </div>
              </div>
              <Link href={`/blog/${featured.slug}`} className="btn btn-primary">
                Read article <RiArrowRightLine size={16} />
              </Link>
            </div>
          </div>

          <div className={c.featuredArt} aria-hidden="true">
            <span className={c.artFloor} />
            <span className={`${c.artSheet} ${c.artSheet1}`}><i /><i /><i /><i /></span>
            <span className={`${c.artSheet} ${c.artSheet2}`}><i /><i /><i /><i /></span>
            <span className={`${c.artSheet} ${c.artSheet3}`}><i /><i /><i /><i /></span>
            <span className={c.artBadge}>
              <TbSparkles size={14} color="var(--tone-primary)" /> Featured read
            </span>
          </div>
        </Surface3D>
      )}

      <section aria-labelledby="latest-title">
        <div className={`${c.sectionHead} enter-3d`} style={{ ["--enter-delay" as string]: "120ms" } as React.CSSProperties}>
          <span className="section-eyebrow"><RiArticleLine size={16} /> Latest publications</span>
          <h2 id="latest-title">Fresh from the engineering team</h2>
        </div>

        {recentPosts.length === 0 ? (
          <Surface3D style={{ marginTop: "var(--space-5)" }}>
            <EmptyState3D
              icon={<RiArticleLine size={16} />}
              title="More articles on the way"
              description="New guides are published regularly. Check back soon or start with the featured article above."
            />
          </Surface3D>
        ) : (
          <div className={`auto-grid ${c.postGrid}`} style={{ marginTop: "var(--space-5)" }}>
            {recentPosts.map((post, i) => (
              <div
                key={post.slug}
                className="enter-3d"
                style={{ ["--enter-delay" as string]: `${160 + (i % 3) * 80}ms` } as React.CSSProperties}
              >
                <Surface3D as="article" tilt accent max={5} className={c.postCard}>
                  <div className={c.metaRow}>
                    <span className="chip chip--sm chip--info">{post.category}</span>
                    <span className={c.metaItem}><RiTimeLine size={13} /> {post.readingTime}</span>
                  </div>
                  <h3 className={c.postTitle} data-depth="1">
                    <Link href={`/blog/${post.slug}`} className={c.titleLink}>
                      {post.title}
                    </Link>
                  </h3>
                  <p className={c.postExcerpt}>{post.excerpt}</p>
                  <div className={c.tagRow}>
                    {post.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className={c.tag}>#{tag}</span>
                    ))}
                  </div>
                  <div className={c.postFooter}>
                    <span className={c.postDate}>{post.publishedAt}</span>
                    <Link href={`/blog/${post.slug}`} className={c.readLink}>
                      Read more <RiArrowRightLine size={14} />
                    </Link>
                  </div>
                </Surface3D>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
