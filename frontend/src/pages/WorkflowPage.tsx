import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import type { ContentEntry, EntryStatus } from "@/types";
import { useAuthStore } from "@/stores/auth";

const COLUMNS: EntryStatus[] = [
  "draft",
  "in_review",
  "pending_approval",
  "scheduled",
  "published",
];

export function WorkflowPage() {
  const publication = useAuthStore((s) => s.publication);
  const [entries, setEntries] = useState<ContentEntry[]>([]);

  useEffect(() => {
    api
      .listEntries({ page_size: 5 })
      .then((r) => setEntries(r.data.results || r.data));
  }, [publication?.id]);

  const byStatus = useMemo(() => {
    const map: Record<string, ContentEntry[]> = {};
    for (const col of COLUMNS) map[col] = [];
    for (const e of entries) {
      if (map[e.status]) map[e.status].push(e);
    }
    return map;
  }, [entries]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Publishing workflow</h1>
          <p>Move pieces from draft through review, approval, and publication.</p>
        </div>
      </div>
      <div style={{ display: "flex", gap: "0.75rem", overflowX: "auto", paddingBottom: 8 }}>
        {COLUMNS.map((col) => (
          <div
            key={col}
            className="panel"
            style={{ minWidth: 220, maxWidth: 240, padding: "0.75rem", flex: "0 0 auto" }}
          >
            <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-muted)", marginBottom: 8 }}>
              {col.replace("_", " ")} · {byStatus[col]?.length || 0}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(byStatus[col] || []).map((e) => (
                <Link
                  key={e.id}
                  to={`/entries/${e.id}`}
                  style={{
                    display: "block",
                    padding: "0.65rem",
                    background: "#f3efe7",
                    borderRadius: 6,
                    border: "1px solid var(--rule)",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "0.92rem" }}>{e.title || "Untitled"}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--ink-muted)", marginTop: 4 }}>
                    {e.assigned_to_name || "Unassigned"}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
