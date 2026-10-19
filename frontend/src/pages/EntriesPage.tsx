import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import type { ContentEntry, EntryStatus } from "@/types";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { format } from "date-fns";

const STATUSES: Array<EntryStatus | "all"> = [
  "all",
  "draft",
  "published",
  "archived",
];

export function EntriesPage() {
  const publication = useAuthStore((s) => s.publication);
  const globalSearch = useUiStore((s) => s.globalSearch);
  const [status, setStatus] = useState<EntryStatus | "all">("all");
  const [entries, setEntries] = useState<ContentEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, unknown> = {
      publication: publication?.id,
      page_size: 50,
      ordering: "created_at",
    };
    if (status !== "all") params.status = status;
    params.search = globalSearch;
    api
      .listEntries(params)
      .then((r) => setEntries(r.data.results || r.data))
      .finally(() => setLoading(false));
  }, [publication?.id, status, globalSearch]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Content</h1>
          <p>Articles, pages, and structured entries across the publication.</p>
        </div>
        <Link className="btn accent" to="/entries/new">
          New content
        </Link>
      </div>

      <div style={{ display: "flex", gap: "0.4rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {STATUSES.map((s) => (
          <button
            key={s}
            className={`btn ${status === s ? "accent" : "secondary"}`}
            onClick={() => setStatus(s)}
            style={{ padding: "0.35rem 0.7rem", fontSize: "0.85rem" }}
          >
            {s === "all" ? "All" : s.replace("_", " "}
          </button>
        ))}
      </div>

      <div className="panel" style={{ overflow: "hidden" }}>
        {loading ? (
          <div className="empty">Loading…</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Type</th>
                <th>Locale</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>
                    <Link to={`/entries/${e.slug}`} style={{ fontWeight: 600 }}>
                      {e.title || "Untitled"}
                    </Link>
                    <div style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}>{e.path || `/${e.slug}`}</div>
                  </td>
                  <td>{e.content_type_slug || "—"}</td>
                  <td>{e.locale}</td>
                  <td>
                    <span className={`badge ${e.status}`}>{e.status.replace("_", " ")}</span>
                  </td>
                  <td>{e.assigned_to_name || "—"}</td>
                  <td>{format(new Date(e.created_at), "MMM d, HH:mm")}</td>
                </tr>
              ))}
              {!entries.length && (
                <tr>
                  <td colSpan={6} className="empty">
                    No matching content.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
