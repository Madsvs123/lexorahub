import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { WebhookEndpoint } from "@/types";

export function WebhooksPage() {
  const [hooks, setHooks] = useState<WebhookEndpoint[]>([]);
  const [form, setForm] = useState({ name: "", url: "", events: "content.published,content.unpublished });

  const load = () => api.listWebhooks().then((r) => setHooks(r.data.results || r.data));
  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.createWebhook({
      name: form.name,
      url: form.url,
      events: form.events.split(",").map((s) => s.trim()).filter(Boolean),
    });
    setForm({ name: "", url: "", events: "content.published,content.unpublished" });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Webhooks</h1>
          <p>Signed event delivery for cache invalidation, syndication, and downstream systems.</p>
        </div>
      </div>
      <div className="grid-2">
        <div className="panel" style={{ overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Events</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {hooks.map((h) => (
                <tr key={h.id}>
                  <td>{h.name}</td>
                  <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>{h.url}</td>
                  <td>{(h.events || []).join(", ")}</td>
                  <td>{h.is_active ? "no" : "yes"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="panel" style={{ padding: "1.1rem" }} onSubmit={create}>
          <h3 style={{ marginBottom: 12 }}>Add endpoint</h3>
          <div className="form-field">
            <label>Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-field">
            <label>URL</label>
            <input type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          </div>
          <div className="form-field">
            <label>Events (comma-separated)</label>
            <input value={form.events} onChange={(e) => setForm({ ...form, events: e.target.value })} />
          </div>
          <button className="btn accent" type="submit">
            Create webhook
          </button>
        </form>
      </div>
    </div>
  );
}
