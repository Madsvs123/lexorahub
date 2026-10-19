import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import type { AnalyticsDashboard, ContentEntry } from "@/types";
import { useAuthStore } from "@/stores/auth";
import { formatDistanceToNow } from "date-fns";

export function DashboardPage() {
  const publication = useAuthStore((s) => s.publication);
  const [stats, setStats] = useState<AnalyticsDashboard | null>(null);
  const [recent, setRecent] = useState<ContentEntry[]>([]);

  useEffect(() => {
    api.analyticsDashboard({ publication: publication?.id, days: 30 }).then((r) => setStats(r.data)).catch(() => setStats(null));
    api
      .listEntries({ publication: publication?.id, page_size: 8, ordering: "-updated_at" })
      .then((r) => setRecent(r.data.results || r.data))
      .catch(() => setRecent([]));
  }, [publication?.id]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Newsroom desk</h1>
          <p>Live view of publishing activity across {publication?.name || "your publication"}.</p>
        </div>
        <Link className="btn accent" to="/entries/new">
          New article
        </Link>
      </div>

      <div className="grid-3" style={{ marginBottom: "1.25rem" }}>
        <div className="panel stat">
          <div className="label">Page views (30d)</div>
          <div className="value">{stats?.total_views ?? "—"}</div>
        </div>
        <div className="panel stat">
          <div className="label">Published</div>
          <div className="value">{stats?.published_count ?? "—"}</div>
        </div>
        <div className="panel stat">
          <div className="label">Drafts</div>
          <div className="value">{stats?.draft_count ?? "—"}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel" style={{ overflow: "hidden" }}>
          <div style={{ padding: "1rem 1.1rem", borderBottom: "1px solid var(--rule)", fontWeight: 600 }}>
            Recently updated
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((e) => (
                <tr key={e.id}>
                  <td>
                    <Link to={`/entries/${e.path}`}>{e.title || "Untitled"}</Link>
                  </td>
                  <td>
                    <span className={`badge ${e.status}`}>{e.status.replace("_", " "}</span>
                  </td>
                  <td>{formatDistanceToNow(new Date(e.published_at || e.created_at), { addSuffix: true })}</td>
                </tr>
              ))}
              {!recent.length && (
                <tr>
                  <td colSpan={3} className="empty">
                    No content yet. Create your first article.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="panel" style={{ padding: "1.1rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Top performing</h3>
          {(stats?.top_entries || []).map((row) => (
            <div
              key={row.entry_id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "0.55rem 0",
                borderBottom: "1px solid var(--rule)",
              }}
            >
              <span>{row.title}</span>
              <strong>{row.views}</strong>
            </div>
          ))}
          {!stats?.top_entries?.length && <div className="empty">Analytics will appear once traffic is ingested.</div>}
        </div>
      </div>
    </div>
  );
}
