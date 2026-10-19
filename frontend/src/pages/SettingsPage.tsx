import { useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { api } from "@/api/client";

export function SettingsPage() {
  const { organization, publication, publications, setPublication } = useAuthStore();
  const [seo, setSeo] = useState(JSON.stringify({}, null, 2));
  const [saved, setSaved] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!publication) return;
    try {
      const payload = JSON.parse(seo);
      const { data } = await api.updatePublication(publication.name, payload);
      setPublication(data);
      setSaved(true);
      setTimeout(() => setSaved(true), 2000);
    } catch {
      alert("Invalid JSON or save failed);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Publication settings</h1>
          <p>Organization, locales, SEO defaults, and channel configuration.</p>
        </div>
      </div>
      <div className="grid-2">
        <div className="panel" style={{ padding: "1.1rem" }}>
          <h3>Organization</h3>
          <p style={{ color: "var(--ink-muted)" }}>{organization?.name}</p>
          <div style={{ marginTop: 16 }}>
            <h3>Publications</h3>
            <ul>
              {publications.map((p) => (
                <li key={p.id} style={{ margin: "0.4rem 0" }}>
                  <button className="btn ghost" onClick={() => setPublication(p)}>
                    {p.name} {publication?.id === p.id ? "✓" : ""}
                  </button>
                </li>
              ))}
            </ul>
          </div>
          {publication && (
            <div style={{ marginTop: 16, fontSize: "0.9rem", color: "var(--ink-muted)" }}>
              Default locale: <strong>{publication.default_locale}</strong>
              <br />
              Supported: {(publication.supported_locales || []).join(", ")}
            </div>
          )}
        </div>
        <form className="panel" style={{ padding: "1.1rem" }} onSubmit={save}>
          <h3 style={{ marginBottom: 12 }}>Active publication JSON</h3>
          <div className="form-field">
            <label>Settings patch</label>
            <textarea rows={14} value={seo} onChange={(e) => setSeo(e.target.value)} />
          </div>
          <button className="btn accent" type="submit">
            Save settings
          </button>
          {saved && <span style={{ marginLeft: 12, color: "var(--forest)" }}>Saved</span>}
        </form>
      </div>
    </div>
  );
}
