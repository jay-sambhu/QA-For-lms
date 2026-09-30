import type { MetadataRoute } from "next";
import { BLOG_POSTS, type BlogPost } from "../data/blogPosts";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://www.jasuss.tech";
  const apiUrl = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
  const currentDate = new Date();

  let posts: BlogPost[] = BLOG_POSTS;
  try {
    const res = await fetch(`${apiUrl}/api/v1/blogs?limit=200`, { next: { revalidate: 60 } });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.posts) && data.posts.length > 0) {
        posts = data.posts;
      }
    }
  } catch (err) {
    console.error("Sitemap dynamic blog fetch fallback:", err);
  }

  const coreRoutes: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: currentDate,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: currentDate,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: currentDate,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/dashboard`,
      lastModified: currentDate,
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/auth/callback`,
      lastModified: currentDate,
      changeFrequency: "monthly",
      priority: 0.3,
    },
  ];

  const blogPostRoutes: MetadataRoute.Sitemap = posts.map((post) => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: post.publishedAt ? new Date(post.publishedAt) : currentDate,
    changeFrequency: "weekly",
    priority: 0.7,
  }));

  return [...coreRoutes, ...blogPostRoutes];
}
