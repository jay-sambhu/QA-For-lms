"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
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
  RiErrorWarningFill,
} from "react-icons/ri";
import { TbLoader2, TbFileText, TbWorld, TbPencil } from "react-icons/tb";
import { useAuth } from "../../context/AuthContext";
import { Surface3D, StatTile3D, EmptyState3D } from "../three";
import a from "./admin3d.module.css";

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

const enterDelay = (step: number) =>
  ({ ["--enter-delay" as string]: `${step * 60}ms` }) as React.CSSProperties;

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

  const notifTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showNotification = (type: "success" | "error", text: string) => {
    setFeedbackMsg({ type, text });
    if (notifTimerRef.current) clearTimeout(notifTimerRef.current);
    notifTimerRef.current = setTimeout(() => setFeedbackMsg(null), 4000);
  };
  useEffect(() => () => {
    if (notifTimerRef.current) clearTimeout(notifTimerRef.current);
  }, []);

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
    // Prefer the parsed paragraph array: raw_content is the stored JSON string
    // (e.g. '["p1","p2"]') and re-saving it would corrupt the post.
    if (Array.isArray(blog.content) && blog.content.length) {
      setFormContent(blog.content.join("\n\n"));
    } else if (blog.raw_content) {
      setFormContent(blog.raw_content);
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

  const editor = isEditorOpen && (
    <div className={a.overlay}>
      <div
        className={`glass-3d ${a.dialog}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="blog-editor-title"
      >
        <div className={a.dialogHead}>
          <div>
            <h3 id="blog-editor-title" className={a.dialogTitle}>
              {editingBlogId ? "Edit Blog Article" : "Write Dynamic Blog Article"}
            </h3>
            <p className={a.dialogSub}>
              Changes are saved directly to PostgreSQL and served to public viewers.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsEditorOpen(false)}
            className={a.closeBtn}
            title="Close editor"
            aria-label="Close editor"
          >
            <RiCloseLine size={22} />
          </button>
        </div>

        <form onSubmit={handleSaveArticle} className={a.dialogForm}>
          {/* Row 1: Title & Slug */}
          <div className={a.fieldGrid}>
            <div className={a.fieldGroup}>
              <label htmlFor="blog-title" className={a.fieldLabel}>Article Title *</label>
              <input
                id="blog-title"
                type="text"
                required
                value={formTitle}
                onChange={(e) => handleTitleChange(e.target.value)}
                placeholder="e.g. Autonomous Quality Assurance for Next.js Web Apps"
                className={a.field}
              />
            </div>
            <div className={a.fieldGroup}>
              <label htmlFor="blog-slug" className={a.fieldLabel}>URL Slug (Unique path) *</label>
              <input
                id="blog-slug"
                type="text"
                required
                value={formSlug}
                onChange={(e) => setFormSlug(e.target.value)}
                placeholder="autonomous-quality-assurance-nextjs"
                className={`${a.field} ${a.mono}`}
              />
            </div>
          </div>

          {/* Row 2: Category, Reading Time, Status */}
          <div className={a.fieldGrid3}>
            <div className={a.fieldGroup}>
              <label htmlFor="blog-category" className={a.fieldLabel}>Category</label>
              <select
                id="blog-category"
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className={a.field}
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
                  aria-label="Custom category"
                  value={formCustomCategory}
                  onChange={(e) => setFormCustomCategory(e.target.value)}
                  className={a.field}
                />
              )}
            </div>

            <div className={a.fieldGroup}>
              <label htmlFor="blog-reading-time" className={a.fieldLabel}>Estimated Reading Time</label>
              <input
                id="blog-reading-time"
                type="text"
                value={formReadingTime}
                onChange={(e) => setFormReadingTime(e.target.value)}
                placeholder="e.g. 6 min read"
                className={a.field}
              />
            </div>

            <div className={a.fieldGroup}>
              <label htmlFor="blog-status" className={a.fieldLabel}>Publication Status</label>
              <select
                id="blog-status"
                value={formStatus}
                onChange={(e) => setFormStatus(e.target.value as any)}
                className={a.field}
              >
                <option value="published">Published (Live immediately)</option>
                <option value="draft">Draft (Admin eyes only)</option>
              </select>
            </div>
          </div>

          {/* Row 3: Author Name & Role */}
          <div className={a.fieldGrid}>
            <div className={a.fieldGroup}>
              <label htmlFor="blog-author-name" className={a.fieldLabel}>Author Name</label>
              <input
                id="blog-author-name"
                type="text"
                value={formAuthorName}
                onChange={(e) => setFormAuthorName(e.target.value)}
                placeholder="Nexus Core Engineering"
                className={a.field}
              />
            </div>
            <div className={a.fieldGroup}>
              <label htmlFor="blog-author-role" className={a.fieldLabel}>Author Role / Affiliation</label>
              <input
                id="blog-author-role"
                type="text"
                value={formAuthorRole}
                onChange={(e) => setFormAuthorRole(e.target.value)}
                placeholder="Platform Architecture Team"
                className={a.field}
              />
            </div>
          </div>

          {/* Row 4: Tags */}
          <div className={a.fieldGroup}>
            <label htmlFor="blog-tags" className={a.fieldLabel}>Article Tags (Comma separated)</label>
            <input
              id="blog-tags"
              type="text"
              value={formTags}
              onChange={(e) => setFormTags(e.target.value)}
              placeholder="Autonomous QA, Regression Testing, Web Vitals, Next.js"
              className={a.field}
            />
          </div>

          {/* Row 5: Excerpt */}
          <div className={a.fieldGroup}>
            <label htmlFor="blog-excerpt" className={a.fieldLabel}>Article Excerpt (SEO summary &amp; card preview) *</label>
            <textarea
              id="blog-excerpt"
              required
              rows={2}
              value={formExcerpt}
              onChange={(e) => setFormExcerpt(e.target.value)}
              placeholder="Brief 1-2 sentence overview explaining the core value of this article..."
              className={`${a.field} ${a.textarea}`}
            />
          </div>

          {/* Row 6: Content Editor & Live Preview Switch */}
          <div className={a.fieldGroup}>
            <div className={a.contentHead}>
              <label htmlFor="blog-content" className={a.fieldLabel}>
                Article Content *{" "}
                <span className={a.fieldHint}>
                  (Separate paragraphs with a blank line. Supports headers `### Title` and lists `- Item`)
                </span>
              </label>
              <button
                type="button"
                onClick={() => setPreviewMode(!previewMode)}
                className={a.linkBtn}
                aria-pressed={previewMode}
              >
                <RiEyeLine size={14} />
                {previewMode ? "Switch to Edit View" : "Live Preview"}
              </button>
            </div>

            {previewMode ? (
              <div className={`surface-inset ${a.preview}`}>
                <h3 className={a.previewTitle}>{formTitle || "Article Title Preview"}</h3>
                <p className={a.previewExcerpt}>
                  {formExcerpt || "Excerpt preview will render here..."}
                </p>
                <div>
                  {formContent
                    .split("\n\n")
                    .filter(Boolean)
                    .map((para, i) => {
                      if (para.startsWith("### ")) {
                        return (
                          <h4 key={i} className={a.previewH}>
                            {para.replace("### ", "")}
                          </h4>
                        );
                      }
                      return (
                        <p key={i} className={a.previewP}>
                          {para}
                        </p>
                      );
                    })}
                </div>
              </div>
            ) : (
              <textarea
                id="blog-content"
                required
                rows={12}
                value={formContent}
                onChange={(e) => setFormContent(e.target.value)}
                placeholder="Write your article body here... Separate each paragraph or section with two enter keys (blank line)."
                className={`${a.field} ${a.textarea}`}
              />
            )}
          </div>

          {/* Action Buttons */}
          <div className={a.dialogActions}>
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
  );

  return (
    <div className={a.stack}>
      {/* KPI Stats */}
      <div className="bento" style={{ ["--grid-gap" as string]: "16px" } as React.CSSProperties}>
        <div className="span-4 enter-3d" style={enterDelay(1)}>
          <StatTile3D label="Total Articles" value={stats.total} icon={<TbFileText size={20} />} hint="Stored in PostgreSQL" />
        </div>
        <div className="span-4 enter-3d" style={enterDelay(2)}>
          <StatTile3D label="Published (Live)" value={stats.published} accent="success" icon={<TbWorld size={20} />} hint="Visible to the public blog and crawlers" />
        </div>
        <div className="span-4 enter-3d" style={enterDelay(3)}>
          <StatTile3D label="Drafts (Unpublished)" value={stats.drafts} accent="warning" icon={<TbPencil size={20} />} hint="Admin eyes only" />
        </div>
      </div>

      <Surface3D as="section" pad="sm" className="enter-3d" style={enterDelay(4)} aria-labelledby="blog-manager-title">
        {/* Top Header & Actions */}
        <div className={`${a.panelHead} ${a.panelHeadTable}`}>
          <div className={a.panelTitleBlock}>
            <span className="icon-well" aria-hidden="true">
              <RiArticleLine size={20} />
            </span>
            <div>
              <span className="section-eyebrow">Content engine</span>
              <div className={a.panelTitleRow}>
                <h2 id="blog-manager-title" className={a.panelTitle}>Dynamic Blog Management</h2>
                <span className={a.panelCount}>{blogs.length} articles</span>
              </div>
              <p className={a.panelSub}>
                Create and maintain dynamic articles served directly to the public blog and search engine crawlers.
              </p>
            </div>
          </div>

          <div className={a.panelTools}>
            <button
              type="button"
              onClick={fetchBlogs}
              disabled={loading}
              className="btn btn-secondary btn-sm"
            >
              <RiRefreshLine className={loading ? "pulse" : ""} size={16} /> Refresh
            </button>
            <button
              type="button"
              onClick={openNewArticleModal}
              className="btn btn-primary btn-sm"
            >
              <RiAddLine size={18} /> Write New Article
            </button>
          </div>
        </div>

        {/* Notification Banner */}
        {feedbackMsg && (
          <div
            className={`${a.notice} ${feedbackMsg.type === "success" ? a.noticeSuccess : a.noticeDanger}`}
            role="status"
            style={{ margin: "0 8px 12px" }}
          >
            {feedbackMsg.type === "success" ? <RiCheckLine size={18} /> : <RiErrorWarningFill size={18} />}
            {feedbackMsg.text}
          </div>
        )}

        {/* Articles Table */}
        <div className="table-3d-wrap">
          <table className="table-3d">
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
                  <td colSpan={7}>
                    <EmptyState3D
                      compact
                      icon={<RiArticleLine size={16} />}
                      title={loading ? "Loading articles from database..." : "No articles found"}
                      description={loading ? undefined : "Click 'Write New Article' to create one."}
                    />
                  </td>
                </tr>
              ) : (
                blogs.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <div className={a.titleCell}>{b.title}</div>
                      <div className={`${a.slugCell} ${a.mono}`}>/blog/{b.slug}</div>
                    </td>
                    <td>
                      <span className="chip chip--sm chip--primary">{b.category}</span>
                    </td>
                    <td className={a.metaCell}>{b.reading_time || "5 min read"}</td>
                    <td>
                      <span className={`chip chip--sm ${b.status === "published" ? "chip--success chip--dot" : "chip--warning"}`}>
                        {b.status === "published" ? <RiCheckLine size={12} /> : <RiDraftLine size={12} />}
                        {b.status.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <div className={a.authorCell}>{b.author?.name || "Admin"}</div>
                      <div className={a.authorRole}>{b.author?.role || ""}</div>
                    </td>
                    <td className={a.metaCell}>
                      {b.published_at ? new Date(b.published_at).toLocaleDateString() : "Draft"}
                    </td>
                    <td>
                      <div className={`${a.rowActions} ${a.rowActionsEnd}`}>
                        {b.status === "published" && (
                        <Link
                          href={`/blog/${b.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary btn-sm"
                          title="View live post"
                        >
                          <RiEyeLine size={14} /> View
                        </Link>
                        )}

                        <button
                          type="button"
                          onClick={() => openEditArticleModal(b)}
                          className="btn btn-secondary btn-sm"
                          title="Edit article"
                        >
                          <RiEditLine size={14} /> Edit
                        </button>

                        <button
                          type="button"
                          onClick={() => handleToggleStatus(b)}
                          disabled={actionLoading === `toggle-${b.id}`}
                          className="btn btn-secondary btn-sm"
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
                          type="button"
                          onClick={() => handleDelete(b)}
                          disabled={actionLoading === `delete-${b.id}`}
                          className="btn btn-danger btn-sm"
                          title="Delete article"
                        >
                          {actionLoading === `delete-${b.id}` ? (
                            <TbLoader2 className="pulse" size={14} />
                          ) : (
                            <RiDeleteBinLine size={14} />
                          )}
                          <span className="sr-only">Delete article</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Surface3D>

      {editor && typeof document !== "undefined" ? createPortal(editor, document.body) : null}
    </div>
  );
};
