import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/api/client";
import { ArticleEditor } from "@/components/editor/ArticleEditor";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import type { ContentEntry, ContentType, PresenceUser, SeoMeta, SocialMeta } from "@/types";

const AUTOSAVE_MS = 1500;

export function EditorPage() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const navigate = useNavigate();
  const { publication, user } = useAuthStore();
  const { presence, setPresence } = useUiStore();

  const [entry, setEntry] = useState<Partial<ContentEntry>>({
    title: "",
    slug: "",
    locale: publication?.default_locale || "en",
    status: "draft",
    body: { type: "doc", content: [{ type: "paragraph" }] },
    custom_fields: {},
    excerpt: "",
    seo: {},
    social: {},
  });
  const [types, setTypes] = useState<ContentType[]>([]);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [tab, setTab] = useState<"seo" | "social" | "meta" | "comments">("seo");
  const [comments, setComments] = useState<Array<{ id: string; body: string; author_name: string }>>([]);
  const [commentBody, setCommentBody] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const dirty = useRef(false);

  useEffect(() => {
    api.listContentTypes().then((r) => setTypes(r.data.results || r.data));
  }, []);

  useEffect(() => {
    if (isNew) return;
    api.getEntry(id!).then((r) => setEntry(r.data));
    api.listNotes(id!).then((r) => setComments(r.data.results || r.data)).catch(() => undefined);
  }, [id, isNew]);

  // Real-time presence
  useEffect(() => {
    if (isNew || !id) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/collaborate/${id}/`);
    wsRef.current = ws;
    const localPresence: Record<string, PresenceUser> = {};

    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.type === "presence") {
        if (msg.action === "join" && msg.user) localPresence[msg.user.id] = msg.user;
        if (msg.action === "leave" && msg.user) delete localPresence[msg.user.id];
        setPresence(Object.values(localPresence));
      }
    };
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "join", id: crypto.randomUUID() }));
    };
    return () => {
      ws.close();
      setPresence([]);
    };
  }, [id, isNew, setPresence]);

  const persist = useCallback(
    async (mode: "save" | "autosave" = "save") => {
      if (!publication) return;
      setSaving(true);
      try {
        if (isNew) {
          const contentType = types[0]?.slug;
          const { data } = await api.createEntry({
            ...entry,
            publication: publication.id,
            content_type: contentType,
          });
          dirty.current = false;
          setLastSaved(new Date().toISOString());
          navigate(`/entries/${data.id}`, { replace: true });
        } else if (mode === "autosave") {
          await api.autosaveEntry(id!, {
            title: entry.title,
            body: entry.body,
            custom_fields: entry.custom_fields,
            excerpt: entry.excerpt,
            seo: entry.seo,
            social: entry.social,
          });
          setLastSaved(new Date().toISOString());
        } else {
          const { data } = await api.updateEntry(id!, entry);
          setEntry(data);
          dirty.current = false;
          setLastSaved(new Date().toISOString());
        }
      } finally {
        setSaving(false);
      }
    },
    [entry, id, isNew, navigate, publication, types]
  );

  useEffect(() => {
    if (isNew) return;
    const t = setInterval(() => {
      persist();
    }, AUTOSAVE_MS);
    return () => clearInterval(t);
  }, [isNew, persist]);

  const update = (patch: Partial<ContentEntry>) => {
    dirty.current = true;
    setEntry((e) => ({ ...e, ...patch }));
  };

  const publish = async () => {
    if (isNew) await persist("save");
    else {
      const { data } = await api.transitionEntry(id!, "published");
      setEntry(data);
    }
  };

  const transition = async (status: string) => {
    if (isNew) return;
    const { data } = await api.transitionEntry(id!, status);
    setEntry(data);
  };

  const submitComment = async () => {
    if (!commentBody.trim()) return;
    const { data } = await api.createComment({ entry: id, body: commentBody });
    setComments((c) => [data, ...c]);
    setCommentBody("");
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{isNew ? "New article" : "Edit article"}</h1>
          <p>
            {entry.status && <span className={`badge ${entry.status}`}>{entry.status}</span>}{" "}
            {lastSaved ? `Saved ${new Date(lastSaved).toLocaleTimeString()}` : "Not saved yet"}
            {saving ? " · Saving…" : ""}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <div className="presence-row">
            {presence.map((u) => (
              <div key={u.id} className="presence-dot" style={{ background: u.color }} title={u.display_name}>
                {u.display_name.slice(0, 1).toUpperCase()}
              </div>
            ))}
            {user && (
              <div className="presence-dot" style={{ background: "var(--accent)" }} title="You">
                {(user.display_name || user.email).slice(0, 1).toUpperCase()}
              </div>
            )}
          </div>
          <button className="btn secondary" onClick={() => persist("autosave")} disabled={saving}>
            Save
          </button>
          <button className="btn secondary" onClick={() => transition("pending_approval")} disabled={isNew}>
            Submit review
          </button>
          <button className="btn accent" onClick={publish}>
            Publish
          </button>
        </div>
      </div>

      <div className="editor-layout">
        <div className="panel editor-canvas">
          <input
            className="editor-title"
            placeholder="Headline"
            value={entry.title || ""}
            onChange={(e) => update({ title: e.target.value })}
          />
          <ArticleEditor
            value={(entry.body as Record<string, unknown>) || null}
            onChange={(body) => update({ body })}
          />
        </div>

        <div className="panel" style={{ padding: "1rem" }}>
          <div className="form-field">
            <label>Slug</label>
            <input value={entry.slug || ""} onChange={(e) => update({ slug: e.target.value })} />
          </div>
          <div className="form-field">
            <label>Locale</label>
            <select value={entry.locale || "en"} onChange={(e) => update({ locale: e.target.value })}>
              {(publication?.supported_locales || ["en"]).map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label>Excerpt</label>
            <textarea rows={3} value={entry.excerpt || ""} onChange={(e) => update({ excerpt: e.target.value })} />
          </div>
          <div className="form-field">
            <label>Content type</label>
            <select
              value={(entry.content_type as string) || types[0]?.id || ""}
              onChange={(e) => update({ content_type: e.target.value })}
            >
              {types.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", gap: 4, margin: "1rem 0 0.75rem", flexWrap: "wrap" }}>
            {(["seo", "social", "meta", "comments"] as const).map((t) => (
              <button
                key={t}
                className={`btn ${tab === t ? "accent" : "secondary"}`}
                style={{ padding: "0.25rem 0.55rem", fontSize: "0.8rem" }}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "seo" && (
            <>
              <div className="form-field">
                <label>SEO title</label>
                <input
                  value={(entry.seo as SeoMeta)?.title || ""}
                  onChange={(e) => update({ seo: { ...(entry.seo || {}), title: e.target.value } })}
                />
              </div>
              <div className="form-field">
                <label>SEO description</label>
                <textarea
                  rows={3}
                  value={(entry.seo as SeoMeta)?.description || ""}
                  onChange={(e) => update({ seo: { ...(entry.seo || {}), description: e.target.value } })}
                />
              </div>
            </>
          )}

          {tab === "social" && (
            <>
              <div className="form-field">
                <label>Twitter title</label>
                <input
                  value={(entry.social as SocialMeta)?.twitter_title || ""}
                  onChange={(e) => update({ social: { ...(entry.social || {}), twitter_title: e.target.value } })}
                />
              </div>
              <div className="form-field">
                <label>Facebook title</label>
                <input
                  value={(entry.social as SocialMeta)?.facebook_title || ""}
                  onChange={(e) => update({ social: { ...(entry.social || {}), facebook_title: e.target.value } })}
                />
              </div>
            </>
          )}

          {tab === "meta" && (
            <div className="form-field">
              <label>Custom fields (JSON)</label>
              <textarea
                rows={8}
                value={JSON.stringify(entry.custom_fields || {}, null, 2)}
                onChange={(e) => {
                  try {
                    update({ custom_fields: JSON.parse(e.target.value) });
                  } catch {
                    /* ignore while typing */
                  }
                }}
              />
            </div>
          )}

          {tab === "comments" && (
            <div>
              <div style={{ maxHeight: 240, overflow: "auto", marginBottom: 8 }}>
                {comments.map((c) => (
                  <div key={c.id} style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--rule)" }}>
                    <strong style={{ fontSize: "0.8rem" }}>{c.author_name}</strong>
                    <div>{c.body}</div>
                  </div>
                ))}
                {!comments.length && <div className="empty">No comments yet.</div>}
              </div>
              <textarea rows={3} value={commentBody} onChange={(e) => setCommentBody(e.target.value)} placeholder="Editorial comment…" />
              <button className="btn secondary" style={{ marginTop: 8 }} onClick={submitComment}>
                Add comment
              </button>
            </div>
          )}

          <div style={{ marginTop: "1.25rem", fontSize: "0.8rem", color: "var(--ink-muted)" }}>
            Rev {entry.revision_number || 0} · {entry.word_count || 0} words · {entry.reading_time_minutes || 0} min read
          </div>
        </div>
      </div>
    </div>
  );
}
