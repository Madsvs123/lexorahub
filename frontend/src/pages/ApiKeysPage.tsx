import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { ApiKey } from "@/types";

export function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [name, setName] = useState("");
  const [created, setCreated] = useState<string | null>(null);

  const load = () => api.listApiKeys().then((r) => setKeys(r.data.results || r.data));
  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    const { data } = await api.createApiKey({ name, scopes: ["read"] });
    setCreated(data.key_prefix || null);
    setName("");
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>API keys</h1>
          <p>Delivery API credentials with scoped access for published and preview content.</p>
        </div>
      </div>
      {created && (
        <div className="panel" style={{ padding: "1rem", marginBottom: 12, borderColor: "var(--accent)" }}>
          <strong>Copy this key now</strong> — it will not be shown again.
          <code style={{ display: "block", marginTop: 8, wordBreak: "break-all" }}>{created}</code>
        </div>
      )}
      <div className="grid-2">
        <div className="panel" style={{ overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Prefix</th>
                <th>Scopes</th>
                <th>Last used</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td>{k.name}</td>
                  <td>
                    <code>{k.key_prefix.slice(0, 4)}…</code>
                  </td>
                  <td>{(k.scopes || []).join(", ")}</td>
                  <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="panel" style={{ padding: "1.1rem" }} onSubmit={create}>
          <h3 style={{ marginBottom: 12 }}>Create key</h3>
          <div className="form-field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Website delivery />
          </div>
          <button className="btn accent" type="submit">
            Generate API key
          </button>
        </form>
      </div>
    </div>
  );
}
