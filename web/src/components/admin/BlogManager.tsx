"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  RiArticleLine,
  RiAddLine,
  RiEditLine,
  RiDeleteBinLine,
  RiEyeLine,
  RiCheckLine,
  RiCloseLine,
  RiRefreshLine,
  RiDraftLine,
  RiSendPlaneLine,
} from "react-icons/ri";
import { TbSparkles, TbLoader2 } from "react-icons/tb";
import { useAuth } from "../../context/AuthContext";
import styles from "../../app/page.module.css";

interface BlogArticle {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  content: string[];
  raw_content?: string;
  category: string;
  tags: string[];
  author: {
    name: string;
    role: string;
    avatar: string;
  };
  reading_time: string;
  status: "published" | "draft";
  published_at?: string;
  created_at?: string;
  updated_at?: string;
}

interface BlogStats {
  total: number;
  published: number;
  drafts: number;
}

const DEFAULT_CATEGORIES = [
  "AI & Automation",
  "Responsive Design",
  "Quality Engineering",
  "Compliance & Security",
  "Architecture & Scalability",
  "Performance & SEO",
];

export const BlogManager: React.FC = () => {
  const { session } = useAuth();
  const [blogs, setBlogs] = useState<BlogArticle[]>([]);
  const [stats, setStats] = useState<BlogStats>({ total: 0, published: 0, drafts: 0 });
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Editor Modal State
  const [isEditorOpen, setIsEditorOpen] = useState<boolean>(false);
  const [editingBlogId, setEditingBlogId] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<boolean>(false);

  // Form Fields
  const [formTitle, setFormTitle] = useState<string>("");
  const [formSlug, setFormSlug] = useState<string>("");
  const [formExcerpt, setFormExcerpt] = useState<string>("");
  const [formContent, setFormContent] = useState<string>("");
  const [formCategory, setFormCategory] = useState<string>("AI & Automation");
  const [formCustomCategory, setFormCustomCategory] = useState<string>("");
  const [formTags, setFormTags] = useState<string>("");
  const [formReadingTime, setFormReadingTime] = useState<string>("5 min read");
  const [formAuthorName, setFormAuthorName] = useState<string>("Nexus Core Engineering");
  const [formAuthorRole, setFormAuthorRole] = useState<string>("Platform Architecture Team");
  const [formStatus, setFormStatus] = useState<"published" | "draft">("published");

  const showNotification = (type: "success" | "error", text: string) => {
    setFeedbackMsg({ type, text });
    setTimeout(() => setFeedbackMsg(null), 4000);
  };

  const fetchBlogs = useCallback(async () => {
    setLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }
      const res = await fetch("/api/v1/admin/blogs", { headers });
      if (res.ok) {
        const data = await res.json();
        setBlogs(data.blogs || []);
        if (data.stats) {
          setStats(data.stats);
        }
      } else {
        const err = await res.json().catch(() => ({}));
        showNotification("error", err.detail || "Failed to load blog posts");
      }
    } catch (err) {
      console.error("Error fetching admin blogs:", err);
      showNotification("error", "Network error while fetching blog list");
    } finally {
      setLoading(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    fetchBlogs();
  }, [fetchBlogs]);

  const openNewArticleModal = () => {
    setEditingBlogId(null);
    setFormTitle("");
    setFormSlug("");
    setFormExcerpt("");
    setFormContent("");
    setFormCategory("AI & Automation");
    setFormCustomCategory("");
    setFormTags("Autonomous QA, Regression Testing, Web Standards");
    setFormReadingTime("5 min read");
    setFormAuthorName("Nexus Core Engineering");
    setFormAuthorRole("Platform Architecture Team");
    setFormStatus("published");
    setPreviewMode(false);
    setIsEditorOpen(true);
  };

  const openEditArticleModal = (blog: BlogArticle) => {
    setEditingBlogId(blog.id);
    setFormTitle(blog.title);
    setFormSlug(blog.slug);
    setFormExcerpt(blog.excerpt);

    // Format content for textarea
    if (blog.raw_content) {
      setFormContent(blog.raw_content);
    } else if (Array.isArray(blog.content)) {
      setFormContent(blog.content.join("\n\n"));
    } else {
      setFormContent(String(blog.content || ""));
    }

    if (DEFAULT_CATEGORIES.includes(blog.category)) {
      setFormCategory(blog.category);
      setFormCustomCategory("");
    } else {
      setFormCategory("custom");
      setFormCustomCategory(blog.category);
    }

    setFormTags(Array.isArray(blog.tags) ? blog.tags.join(", ") : String(blog.tags || ""));
    setFormReadingTime(blog.reading_time || "5 min read");
    setFormAuthorName(blog.author?.name || "Nexus Core Engineering");
    setFormAuthorRole(blog.author?.role || "Platform Architecture Team");
    setFormStatus(blog.status);
    setPreviewMode(false);
    setIsEditorOpen(true);
  };

  const handleTitleChange = (val: string) => {
    setFormTitle(val);
    if (!editingBlogId) {
      // Auto-generate slug when creating new post
      const autoSlug = val
        .toLowerCase()
        .replace(/[^\w\s-]/g, "")
        .replace(/[\s_-]+/g, "-")
        .replace(/^-+|-+$/g, "");
      setFormSlug(autoSlug);
    }
  };

  const handleSaveArticle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      showNotification("error", "Article title is required.");
      return;
    }
    if (!formExcerpt.trim()) {
      showNotification("error", "Article excerpt is required.");
      return;
    }
    if (!formContent.trim()) {
      showNotification("error", "Article content cannot be empty.");
      return;
    }

    setActionLoading(editingBlogId ? "updating" : "creating");
    const chosenCategory = formCategory === "custom" ? (formCustomCategory.trim() || "Engineering") : formCategory;
    const parsedTags = formTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    // Convert double newline content into array of paragraphs
    const contentParagraphs = formContent
      .split("\n\n")
      .map((p) => p.trim())
      .filter(Boolean);

    const payload = {
      title: formTitle.trim(),
      slug: formSlug.trim() || undefined,
      excerpt: formExcerpt.trim(),
      content: contentParagraphs,
      category: chosenCategory,
      tags: parsedTags,
      reading_time: formReadingTime.trim() || "5 min read",
      author_name: formAuthorName.trim() || "Nexus Core Engineering",
      author_role: formAuthorRole.trim() || "Platform Architecture Team",
      author_avatar: "/logo.png",
      status: formStatus,
    };

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const url = editingBlogId ? `/api/v1/admin/blogs/${editingBlogId}` : "/api/v1/admin/blogs";
      const method = editingBlogId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers,
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        showNotification(
          "success",
          editingBlogId ? "Article updated successfully!" : "New dynamic article published!"
        );
        setIsEditorOpen(false);
        fetchBlogs();
      } else {
        const err = await res.json().catch(() => ({}));
        showNotification("error", err.detail || "Failed to save article.");
      }
    } catch (err) {
      console.error("Save article error:", err);
      showNotification("error", "Network error while saving article.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleStatus = async (blog: BlogArticle) => {
    setActionLoading(`toggle-${blog.id}`);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }
      const targetStatus = blog.status === "published" ? "draft" : "published";
      const res = await fetch(`/api/v1/admin/blogs/${blog.id}/status`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ status: targetStatus }),
      });
      if (res.ok) {
        showNotification("success", `Article marked as ${targetStatus}!`);
        fetchBlogs();
      } else {
        const err = await res.json().catch(() => ({}));
        showNotification("error", err.detail || "Failed to update article status.");
      }
    } catch (err) {
      console.error("Status toggle error:", err);
      showNotification("error", "Network error updating status.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (blog: BlogArticle) => {
    if (!window.confirm(`Are you sure you want to permanently delete article "${blog.title}"?`)) {
      return;
    }
    setActionLoading(`delete-${blog.id}`);
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }
      const res = await fetch(`/api/v1/admin/blogs/${blog.id}`, {
        method: "DELETE",
        headers,
      });
      if (res.ok) {
        showNotification("success", "Article deleted successfully.");
        fetchBlogs();
      } else {
        const err = await res.json().catch(() => ({}));
        showNotification("error", err.detail || "Failed to delete article.");
      }
    } catch (err) {
      console.error("Delete blog error:", err);
      showNotification("error", "Network error deleting article.");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className={styles.adminTableCard} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Header & Actions */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          paddingBottom: "16px",
        }}
      >
        <div>
          <h3
            style={{
              fontSize: "1.2rem",
              fontWeight: 700,
              color: "#f8fafc",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              margin: 0,
            }}
          >
            <RiArticleLine color="#6366f1" size={22} />
            Dynamic Blog Management &amp; Content Engine
          </h3>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem", margin: "4px 0 0" }}>
            Create and maintain dynamic articles served directly to the public blog and search engine crawlers.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            onClick={fetchBlogs}
            disabled={loading}
            className="btn btn-secondary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "0.85rem", padding: "8px 14px" }}
          >
            <RiRefreshLine className={loading ? "pulse" : ""} size={16} /> Refresh
          </button>
          <button
            onClick={openNewArticleModal}
            className="btn btn-primary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "0.85rem", padding: "8px 16px" }}
          >
            <RiAddLine size={18} /> Write New Article
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
        }}
      >
        <div style={S.statCard}>
          <div style={S.statLabel}>Total Articles</div>
          <div style={S.statVal}>{stats.total}</div>
        </div>
        <div style={S.statCard}>
          <div style={S.statLabel}>Published (Live)</div>
          <div style={{ ...S.statVal, color: "#10b981" }}>{stats.published}</div>
        </div>
        <div style={S.statCard}>
          <div style={S.statLabel}>Drafts (Unpublished)</div>
          <div style={{ ...S.statVal, color: "#f59e0b" }}>{stats.drafts}</div>
        </div>
      </div>

      {/* Notification Banner */}
      {feedbackMsg && (
        <div
          style={{
            padding: "10px 16px",
            borderRadius: "10px",
            fontSize: "0.9rem",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: feedbackMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            color: feedbackMsg.type === "success" ? "#34d399" : "#f87171",
            border: `1px solid ${feedbackMsg.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
          }}
        >
          {feedbackMsg.type === "success" ? <RiCheckLine size={18} /> : <RiCloseLine size={18} />}
          {feedbackMsg.text}
        </div>
      )}

      {/* Articles Table */}
      <div className={styles.adminTableContainer} style={{ overflowX: "auto" }}>
        <table className={styles.adminTable}>
          <thead>
            <tr>
              <th>Title &amp; Slug</th>
              <th>Category</th>
              <th>Reading Time</th>
              <th>Status</th>
              <th>Author</th>
              <th>Published</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {blogs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "32px", color: "#94a3b8" }}>
                  {loading ? "Loading articles from database..." : "No articles found. Click 'Write New Article' to create one."}
                </td>
              </tr>
            ) : (
              blogs.map((b) => (
                <tr key={b.id}>
                  <td>
                    <div style={{ fontWeight: 600, color: "#f1f5f9", fontSize: "0.92rem", marginBottom: "4px" }}>
                      {b.title}
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "#6366f1", fontFamily: "monospace" }}>
                      /blog/{b.slug}
                    </div>
                  </td>
                  <td>
                    <span
                      style={{
                        padding: "3px 8px",
                        borderRadius: "6px",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        background: "rgba(99, 102, 241, 0.15)",
                        color: "#a5b4fc",
                        border: "1px solid rgba(99, 102, 241, 0.3)",
                      }}
                    >
                      {b.category}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.82rem", color: "#cbd5e1" }}>{b.reading_time || "5 min read"}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "5px",
                        padding: "3px 9px",
                        borderRadius: "12px",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        background: b.status === "published" ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                        color: b.status === "published" ? "#34d399" : "#fbbf24",
                        border: `1px solid ${b.status === "published" ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                      }}
                    >
                      {b.status === "published" ? <RiCheckLine size={12} /> : <RiDraftLine size={12} />}
                      {b.status}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.82rem", color: "#94a3b8" }}>
                    <div>{b.author?.name || "Admin"}</div>
                    <div style={{ fontSize: "0.74rem", color: "#64748b" }}>{b.author?.role || ""}</div>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    {b.published_at ? new Date(b.published_at).toLocaleDateString() : "Draft"}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "6px", alignItems: "center" }}>
                      <Link
                        href={`/blog/${b.slug}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary"
                        style={{ padding: "6px 10px", fontSize: "0.78rem" }}
                        title="View live post"
                      >
                        <RiEyeLine size={14} /> View
                      </Link>

                      <button
                        onClick={() => openEditArticleModal(b)}
                        className="btn btn-secondary"
                        style={{ padding: "6px 10px", fontSize: "0.78rem" }}
                        title="Edit article"
                      >
                        <RiEditLine size={14} /> Edit
                      </button>

                      <button
                        onClick={() => handleToggleStatus(b)}
                        disabled={actionLoading === `toggle-${b.id}`}
                        className="btn btn-secondary"
                        style={{
                          padding: "6px 10px",
                          fontSize: "0.78rem",
                          color: b.status === "published" ? "#fbbf24" : "#34d399",
                        }}
                        title={b.status === "published" ? "Unpublish to draft" : "Publish immediately"}
                      >
                        {actionLoading === `toggle-${b.id}` ? (
                          <TbLoader2 className="pulse" size={14} />
                        ) : b.status === "published" ? (
                          "Unpublish"
                        ) : (
                          "Publish"
                        )}
                      </button>

                      <button
                        onClick={() => handleDelete(b)}
                        disabled={actionLoading === `delete-${b.id}`}
                        className="btn btn-secondary"
                        style={{ padding: "6px 10px", fontSize: "0.78rem", color: "#f87171" }}
                        title="Delete article"
                      >
                        {actionLoading === `delete-${b.id}` ? (
                          <TbLoader2 className="pulse" size={14} />
                        ) : (
                          <RiDeleteBinLine size={14} />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Editor Modal */}
      {isEditorOpen && (
        <div style={S.modalOverlay}>
          <div style={S.modalCard}>
            <div style={S.modalHeader}>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.3rem", fontWeight: 700, color: "#f8fafc" }}>
                  {editingBlogId ? "Edit Blog Article" : "Write Dynamic Blog Article"}
                </h3>
                <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: "0.85rem" }}>
                  Changes are saved directly to PostgreSQL and served to public viewers.
                </p>
              </div>
              <button
                onClick={() => setIsEditorOpen(false)}
                style={S.closeModalBtn}
                title="Close editor"
              >
                <RiCloseLine size={22} />
              </button>
            </div>

            <form onSubmit={handleSaveArticle} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Row 1: Title & Slug */}
              <div style={S.formGrid2}>
                <div>
                  <label style={S.label}>Article Title *</label>
                  <input
                    type="text"
                    required
                    value={formTitle}
                    onChange={(e) => handleTitleChange(e.target.value)}
                    placeholder="e.g. Autonomous Quality Assurance for Next.js Web Apps"
                    style={S.input}
                  />
                </div>
                <div>
                  <label style={S.label}>URL Slug (Unique path) *</label>
                  <input
                    type="text"
                    required
                    value={formSlug}
                    onChange={(e) => setFormSlug(e.target.value)}
                    placeholder="autonomous-quality-assurance-nextjs"
                    style={{ ...S.input, fontFamily: "monospace" }}
                  />
                </div>
              </div>

              {/* Row 2: Category, Reading Time, Status */}
              <div style={S.formGrid3}>
                <div>
                  <label style={S.label}>Category</label>
                  <select
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                    style={S.input}
                  >
                    {DEFAULT_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                    <option value="custom">+ Custom Category</option>
                  </select>
                  {formCategory === "custom" && (
                    <input
                      type="text"
                      placeholder="Enter custom category"
                      value={formCustomCategory}
                      onChange={(e) => setFormCustomCategory(e.target.value)}
                      style={{ ...S.input, marginTop: "8px" }}
                    />
                  )}
                </div>

                <div>
                  <label style={S.label}>Estimated Reading Time</label>
                  <input
                    type="text"
                    value={formReadingTime}
                    onChange={(e) => setFormReadingTime(e.target.value)}
                    placeholder="e.g. 6 min read"
                    style={S.input}
                  />
                </div>

                <div>
                  <label style={S.label}>Publication Status</label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as any)}
                    style={S.input}
                  >
                    <option value="published">Published (Live immediately)</option>
                    <option value="draft">Draft (Admin eyes only)</option>
                  </select>
                </div>
              </div>

              {/* Row 3: Author Name & Role */}
              <div style={S.formGrid2}>
                <div>
                  <label style={S.label}>Author Name</label>
                  <input
                    type="text"
                    value={formAuthorName}
                    onChange={(e) => setFormAuthorName(e.target.value)}
                    placeholder="Nexus Core Engineering"
                    style={S.input}
                  />
                </div>
                <div>
                  <label style={S.label}>Author Role / Affiliation</label>
                  <input
                    type="text"
                    value={formAuthorRole}
                    onChange={(e) => setFormAuthorRole(e.target.value)}
                    placeholder="Platform Architecture Team"
                    style={S.input}
                  />
                </div>
              </div>

              {/* Row 4: Tags */}
              <div>
                <label style={S.label}>Article Tags (Comma separated)</label>
                <input
                  type="text"
                  value={formTags}
                  onChange={(e) => setFormTags(e.target.value)}
                  placeholder="Autonomous QA, Regression Testing, Web Vitals, Next.js"
                  style={S.input}
                />
              </div>

              {/* Row 5: Excerpt */}
              <div>
                <label style={S.label}>Article Excerpt (SEO summary &amp; card preview) *</label>
                <textarea
                  required
                  rows={2}
                  value={formExcerpt}
                  onChange={(e) => setFormExcerpt(e.target.value)}
                  placeholder="Brief 1-2 sentence overview explaining the core value of this article..."
                  style={S.textarea}
                />
              </div>

              {/* Row 6: Content Editor & Live Preview Switch */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <label style={S.label}>
                    Article Content *{" "}
                    <span style={{ fontWeight: 400, color: "#64748b" }}>
                      (Separate paragraphs with a blank line. Supports headers `### Title` and lists `- Item`)
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setPreviewMode(!previewMode)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#818cf8",
                      fontSize: "0.82rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <RiEyeLine size={14} />
                    {previewMode ? "Switch to Edit View" : "Live Preview"}
                  </button>
                </div>

                {previewMode ? (
                  <div style={S.previewBox}>
                    <h3 style={{ color: "#f8fafc", marginTop: 0 }}>{formTitle || "Article Title Preview"}</h3>
                    <p style={{ color: "#94a3b8", fontStyle: "italic", borderLeft: "3px solid #6366f1", paddingLeft: "12px" }}>
                      {formExcerpt || "Excerpt preview will render here..."}
                    </p>
                    <div style={{ marginTop: "16px", color: "#e2e8f0", lineHeight: 1.8 }}>
                      {formContent
                        .split("\n\n")
                        .filter(Boolean)
                        .map((para, i) => {
                          if (para.startsWith("### ")) {
                            return (
                              <h4 key={i} style={{ color: "#818cf8", marginTop: "18px", marginBottom: "8px" }}>
                                {para.replace("### ", "")}
                              </h4>
                            );
                          }
                          return (
                            <p key={i} style={{ marginBottom: "14px" }}>
                              {para}
                            </p>
                          );
                        })}
                    </div>
                  </div>
                ) : (
                  <textarea
                    required
                    rows={12}
                    value={formContent}
                    onChange={(e) => setFormContent(e.target.value)}
                    placeholder="Write your article body here... Separate each paragraph or section with two enter keys (blank line)."
                    style={{ ...S.textarea, fontFamily: "inherit", fontSize: "0.92rem", lineHeight: 1.6 }}
                  />
                )}
              </div>

              {/* Action Buttons */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "12px",
                  borderTop: "1px solid rgba(255,255,255,0.08)",
                  paddingTop: "16px",
                  marginTop: "8px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setIsEditorOpen(false)}
                  className="btn btn-secondary"
                  disabled={actionLoading !== null}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading !== null}
                  className="btn btn-primary"
                  style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  {actionLoading ? (
                    <>
                      <TbLoader2 className="pulse" size={16} /> Saving article...
                    </>
                  ) : (
                    <>
                      <RiSendPlaneLine size={16} />
                      {editingBlogId ? "Update Article" : "Save & Publish Article"}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const S: Record<string, React.CSSProperties> = {
  statCard: {
    padding: "12px 16px",
    borderRadius: "12px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  statLabel: {
    fontSize: "0.75rem",
    color: "#94a3b8",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: "4px",
  },
  statVal: {
    fontSize: "1.5rem",
    fontWeight: 800,
    color: "#f8fafc",
  },
  modalOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: "rgba(0, 0, 0, 0.75)",
    backdropFilter: "blur(8px)",
    zIndex: 9999,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "20px",
  },
  modalCard: {
    width: "100%",
    maxWidth: "840px",
    maxHeight: "90vh",
    overflowY: "auto",
    background: "rgba(15, 23, 42, 0.96)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    borderRadius: "20px",
    padding: "28px",
    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
  },
  modalHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "20px",
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    paddingBottom: "14px",
  },
  closeModalBtn: {
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "8px",
    color: "#94a3b8",
    padding: "6px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  formGrid2: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: "14px",
  },
  formGrid3: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "14px",
  },
  label: {
    display: "block",
    fontSize: "0.82rem",
    fontWeight: 600,
    color: "#cbd5e1",
    marginBottom: "6px",
  },
  input: {
    width: "100%",
    padding: "10px 14px",
    borderRadius: "10px",
    background: "rgba(0, 0, 0, 0.35)",
    border: "1px solid rgba(255, 255, 255, 0.12)",
    color: "#f8fafc",
    fontSize: "0.88rem",
    outline: "none",
    boxSizing: "border-box",
  },
  textarea: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: "10px",
    background: "rgba(0, 0, 0, 0.35)",
    border: "1px solid rgba(255, 255, 255, 0.12)",
    color: "#f8fafc",
    fontSize: "0.88rem",
    outline: "none",
    boxSizing: "border-box",
    resize: "vertical",
  },
  previewBox: {
    padding: "18px",
    borderRadius: "10px",
    background: "rgba(0,0,0,0.4)",
    border: "1px solid rgba(99, 102, 241, 0.25)",
    maxHeight: "350px",
    overflowY: "auto",
  },
};
