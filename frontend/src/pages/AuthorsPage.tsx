import { useEffect, useState } from "react";
import { api } from "@/api/client";

interface Author {
  id: string;
  display_name: string;
  slug: string;
  job_title: string;
  short_bio: string;
  email: string;
  is_active: boolean;
}

export function AuthorsPage() {
  const [authors, setAuthors] = useState<Author[]>([]);
  const [form, setForm] = useState({ display_name: "", slug: "", job_title: "", short_bio: "", email: "" });

  const load = () => api.listAuthors().then((r) => setAuthors(r.data.results || r.data));
  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.raw.post("/content/author/", {
      ...form,
      slug: form.slug || form.display_name.replace(/\s+/g, "_"),
    });
    setForm({ display_name: "", slug: "", job_title: "", short_bio: "", email: "" });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Authors & contributors</h1>
          <p>Public bylines, staff profiles, and contributor metadata.</p>
        </div>
      </div>
      <div className="grid-2">
        <div className="panel" style={{ overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Title</th>
                <th>Email</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {authors.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.display_name}</strong>
                    <div style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}>{a.slug}</div>
                  </td>
                  <td>{a.job_title || "—"}</td>
                  <td>{a.email || "—"}</td>
                  <td>
                    <span className={`badge ${a.is_active ? "published" : "archived"}`}>
                      {a.is_active ? "active" : "inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="panel" style={{ padding: "1.1rem" }} onSubmit={create}>
          <h3 style={{ marginBottom: 12 }}>Add author</h3>
          {(["display_name", "slug", "job_title", "email"] as const).map((field) => (
            <div className="form-field" key={field}>
              <label>{field.replace("_", " ")}</label>
              <input
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                required={field === "display_name"}
              />
            </div>
          ))}
          <div className="form-field">
            <label>Short bio</label>
            <textarea rows={3} value={form.short_bio} onChange={(e) => setForm({ ...form, short_bio: e.target.value })} />
          </div>
          <button className="btn accent" type="submit">
            Create author
          </button>
        </form>
      </div>
    </div>
  );
}
