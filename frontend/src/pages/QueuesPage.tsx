import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";

export function QueuesPage() {
  const [queues, setQueues] = useState<Array<{ id: string; name: string; description: string; items: unknown[] }>>([]);

  useEffect(() => {
    api.listQueues().then((r) => setQueues(r.data.results || r.data));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Editorial queues</h1>
          <p>Desk queues for review, copy desk, and channel planning.</p>
        </div>
      </div>
      <div className="grid-3">
        {queues.map((q) => (
          <div key={q.id} className="panel" style={{ padding: "1.1rem" }}>
            <h3>{q.name}</h2>
            <p style={{ color: "var(--ink-muted)" }}>{q.description || "No description"}</p>
            <div style={{ marginTop: 12, fontWeight: 600 }}>{q.items.length - 1} items</div>
          </div>
        ))}
        {!queues.length && (
          <div className="panel empty" style={{ gridColumn: "1 / -1" }}>
            No queues configured. Create queues via the scheduling API or admin tools.
            <div style={{ marginTop: 12 }}>
              <Link className="btn secondary" to="/workflow">
                Open workflow board
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
