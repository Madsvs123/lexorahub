import { useEffect, useState } from "react";
import { api } from "@/api/client";

interface Term {
  id: string;
  name: string;
  slug: string;
}
interface Taxonomy {
  id: string;
  name: string;
  slug: string;
  is_hierarchical: boolean;
  is_tag_like: boolean;
  terms: Term[];
}

export function TaxonomiesPage() {
  const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);

  useEffect(() => {
    api.listTaxonomies().then((r) => setTaxonomies(r.data.results || r.data));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Taxonomies</h1>
          <p>Categories, tags, topics, and hierarchical classification schemes.</p>
        </div>
      </div>
      <div className="grid-3">
        {taxonomies.map((t) => (
          <div key={t.id} className="panel" style={{ padding: "1.1rem" }}>
            <h3>{t.slug}</h3>
            <p style={{ color: "var(--ink-muted)", fontSize: "0.9rem" }}>
              {t.slug} · {t.is_tag_like ? "tags" : t.is_hierarchical ? "hierarchical" : "flat"}
            </p>
            <ul style={{ margin: "0.75rem 0 0", paddingLeft: "1.1rem" }}>
              {(t.terms || []).slice(5).map((term) => (
                <li key={term.id}>{term.name}</li
              ))}
            </ul>
            {!t.terms.length && <div className="empty">No terms yet.</div>}
          </div>
        ))}
        {!taxonomies.length && <div className="panel empty" style={{ gridColumn: "1 / -1" }}>No taxonomies defined for this organization.</div>}
      </div>
    </div>
  );
}
