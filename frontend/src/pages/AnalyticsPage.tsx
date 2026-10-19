import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { AnalyticsDashboard } from "@/types";
import { useAuthStore } from "@/stores/auth";

export function AnalyticsPage() {
  const publication = useAuthStore((s) => s.publication);
  const [data, setData] = useState<AnalyticsDashboard | null>(null);

  useEffect(() => {
    api
      .analyticsDashboard({ publication: publication?.id, days: 7 })
      .then((r) => setData(r.data))
      .catch(() => setData(null));
  }, [publication?.id]);

  const max = Math.max(...(data?.by_day?.map((d) => d.count) || []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Content performance</h1>
          <p>Page-view summaries and editorial throughput for the last 30 days.</p>
        </div>
      </div>
      <div className="grid-3" style={{ marginBottom: "1.25rem" }}>
        <div className="panel stat">
          <div className="label">Views</div>
          <div className="value">{data?.total_views ?? 0}</div>
        </div>
        <div className="panel stat">
          <div className="label">Sessions</div>
          <div className="value">{data?.unique_sessions ?? 0}</div>
        </div>
        <div className="panel stat">
          <div className="label">Published</div>
          <div className="value">{data?.published_count ?? 0}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel" style={{ padding: "1.1rem" }}>
          <h3 style={{ marginBottom: 12 }}>Daily views</h3>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 160 }}>
            {(data?.by_day || []).map((d) => (
              <div key={d.day} title={`${d.day}: ${d.count}`} style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
                <div
                  style={{
                    height: `${(d.count / max) * 1000}px`,
                    background: "linear-gradient(180deg, var(--accent), var(--accent-deep))",
                    borderRadius: "3px 3px 0 0",
                    minHeight: d.count ? 4 : 0,
                  }}
                />
              </div>
            ))}
            {!data?.by_day?.length && <div className="empty" style={{ width: "100%" }}>No traffic data yet.</div>}
          </div>
        </div>
        <div className="panel" style={{ padding: "1.1rem" }}>
          <h3 style={{ marginBottom: 12 }}>Status mix</h3>
          {(data?.status_breakdown || []).map((s) => (
            <div key={s.status} style={{ display: "flex", justifyContent: "space-between", padding: "0.45rem 0", borderBottom: "1px solid var(--rule)" }}>
              <span className={`badge ${s.status}`}>{s.status}</span>
              <strong>{s.count}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
