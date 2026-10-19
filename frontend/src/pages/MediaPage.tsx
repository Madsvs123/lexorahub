import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import type { MediaAsset } from "@/types";

export function MediaPage() {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const load = () => {
    api.listAssets({ search: query || undefined, page_size: 60 }).then((r) => setAssets(r.data.results || r.data));
  };

  useEffect(() => {
    load();
  }, []);

  const onUpload = async (files: FileList | null) => {
    if (!files?.length) return;
    for (const file of Array.from(files)) {
      const form = new FormData();
      form.append("file", file);
      form.append("title", file.name);
      await api.uploadAsset(form);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Media library</h1>
          <p>Images, video, documents, credits, focal points, and reusable libraries.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="Search media…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: "0.45rem 0.7rem" }}
          />
          <button className="btn accent" onClick={() => inputRef.current?.click()}>
            Upload
          </button>
          <input ref={inputRef} type="file" multiple hidden onChange={(e) => onUpload(e.target.files) />
        </div>
      </div>

      <div className="media-grid">
        {assets.map((a) => (
          <div key={a.id} className="panel media-tile">
            {a.asset_type === "Image" && a.url ? (
              <img src={a.url} alt={a.alt_text || a.title} />
            ) : (
              <div style={{ aspectRatio: "4/3", display: "grid", placeItems: "center", background: "#e8e2d6" }}>
                {a.asset_type}
              </div>
            )}
            <div className="meta">
              <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{a.title}</div>
              <div style={{ fontSize: "0.75rem", color: "var(--ink-muted)" }}>
                {a.credit || a.mime_type} · {Math.round((a.file_size || 0) / 1024 / 1024)} KB
              </div>
            </div>
          </div>
        ))}
      </div>
      {!assets.length && <div className="panel empty">No assets yet. Upload images or documents to get started.</div>}
    </div>
  );
}
