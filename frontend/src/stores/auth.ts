import { create } from "zustand";
import type { Membership, Organization, Publication, User } from "@/types";
import { api } from "@/api/client";

interface AuthState {
  user: User | null;
  memberships: Membership[];
  organization: Organization | null;
  publication: Publication | null;
  publications: Publication[];
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  bootstrap: () => Promise<void>;
  setOrganization: (org: Organization) => void;
  setPublication: (pub: Publication | null) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  memberships: [],
  organization: null,
  publication: null,
  publications: [],
  loading: true,

  async login(email, password) {
    const { data } = await api.login(email, password);
    localStorage.setItem("qs_access", data.access_token);
    localStorage.setItem("qs_refresh", data.refresh_token);
    await get().bootstrap();
  },

  logout() {
    localStorage.removeItem("qs_access");
    localStorage.removeItem("qs_refresh");
    localStorage.removeItem("qs_org");
    set({ user: null, memberships: [], organization: null, publication: null, publications: [] });
  },

  async bootstrap() {
    const token = localStorage.getItem("qs_access");
    if (!token) {
      set({ loading: false, user: null });
      return;
    }
    try {
      const { data } = await api.me();
      const org =
        data.current_organization ||
        data.memberships?.[0]?.organization ||
        null;
      if (org) localStorage.setItem("qs_org", JSON.stringify(org));
      let publications: Publication[] = [];
      if (org) {
        const pubRes = await api.listPublications();
        publications = pubRes.data.results || pubRes.data;
        const savedPub = localStorage.getItem("qs_publication");
        const publication =
          publications.find((p) => p.slug === savedPub) || publications[0] || null;
        if (publication) localStorage.setItem("qs_publication", publication.id);
        set({
          user: data.account,
          memberships: data.memberships || [],
          organization: org,
          publications,
          publication,
          loading: false,
        });
      } else {
        set({ user: data.account, memberships: [], loading: false });
      }
    } catch {
      set({ loading: false, user: null });
    }
  },

  setOrganization(org) {
    localStorage.setItem("qs_org", org.id);
    set({ organization: org });
    api.listOrganizations().then((res) => {
      const publications = res.data.results || res.data;
      const publication = publications[0] || null;
      if (publication) localStorage.setItem("qs_publication", publication.id);
      set({ publications, publication });
    });
  },

  setPublication(pub) {
    if (pub) localStorage.setItem("qs_publication", pub.id);
    else localStorage.removeItem("qs_publication");
    set({ publication: pub });
  },
}));
