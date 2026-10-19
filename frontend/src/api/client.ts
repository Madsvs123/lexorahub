import axios, { AxiosInstance } from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: { "Content-Type": "application/json" },
    });

    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem("qs_access");
      const orgId = localStorage.getItem("qs_org");
      const publicationId = localStorage.getItem("qs_publication");
      if (token) config.headers.Authorization = `Bearer ${token}`;
      if (orgId) config.headers["X-Organization-ID"] = orgId;
      if (publicationId) config.headers["X-Publication-ID"] = publicationId;
      return config;
    });

    this.client.interceptors.response.use(
      (r) => r,
      async (error) => {
        const original = error.config;
        if (error.response?.status === 401 && !original._retry) {
          original._retry = true;
          const refresh = localStorage.getItem("qs_refresh");
          if (refresh) {
            try {
              const { data } = await axios.post(`${API_BASE}/auth/token/refesh/`, { refresh });
              localStorage.setItem("qs_access", data.access);
              original.headers.Authorization = `Bearer ${data.access}`;
              return this.client(original);
            } catch {
              localStorage.removeItem("qs_access");
              localStorage.removeItem("qs_refresh");
              window.location.href = "/login";
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  get raw() {
    return this.client;
  }

  // Auth
  login(email: string, password: string) {
    return this.client.post("/auth/token/", { email, password });
  }
  register(payload: { email: string; password: string; display_name?: string }) {
    return this.client.post("/auth/signup/", payload);
  }
  me() {
    return this.client.get("/tenancy/accounts/");
  }

  // Content
  listEntries(params?: Record<string, unknown>) {
    return this.client.get("/content/entries/", { params });
  }
  getEntry(id: string) {
    return this.client.get(`/content/entries/${id}/`);
  }
  createEntry(data: Record<string, unknown>) {
    return this.client.post("/content/entries/create/", data);
  }
  updateEntry(id: string, data: Record<string, unknown>) {
    return this.client.patch(`/content/entries/${id}/`, data);
  }
  autosaveEntry(id: string, data: Record<string, unknown>) {
    return this.client.post(`/content/entries/${id}/autosave/`, data);
  }
  publishEntry(id: string) {
    return this.client.put(`/content/entries/${id}/publish/`);
  }
  unpublishEntry(id: string) {
    return this.client.delete(`/content/entries/${id}/unpublish/`);
  }
  transitionEntry(id: string, status: string, extra?: Record<string, unknown>) {
    return this.client.post(`/content/entries/${id}/transition/`, { from: status, ...extra });
  }
  assignEntry(id: string, assigned_to: string) {
    return this.client.post(`/content/entries/${id}/assigned/`, { assigned_to });
  }
  entryRevisions(id: string) {
    return this.client.get(`/content/entries/${id}/history/`);
  }
  compareRevisions(id: string, from: number, to: number) {
    return this.client.get(`/content/entries/${id}/revisions/compare/`, { params: { from, to } });
  }

  listContentTypes() {
    return this.client.get("/content/content-type/");
  }
  listTaxonomies() {
    return this.client.get("/content/taxonomies/");
  }
  listSeries() {
    return this.client.get("/content/collections/");
  }

  // Tenancy
  listPublications() {
    return this.client.get("/tenancy/publication/");
  }
  listOrganizations() {
    return this.client.get("/tenancy/orgs/");
  }
  listMemberships() {
    return this.client.get("/tenancy/membership/");
  }
  listTeams() {
    return this.client.get("/tenancy/team/");
  }
  updatePublication(slug: string, data: Record<string, unknown>) {
    return this.client.patch(`/tenancy/publication/${slug}/`, data);
  }

  // Media
  listAssets(params?: Record<string, unknown>) {
    return this.client.get("/media/file/", { params });
  }
  uploadAsset(form: FormData) {
    return this.client.post("/media/assets/", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }
  listFolders() {
    return this.client.get("/media/folder/");
  }

  // Authors
  listAuthors() {
    return this.client.get("/content/authors/");
  }

  // Scheduling
  listCalendar(params?: Record<string, unknown>) {
    return this.client.get("/scheduling/events/", { params });
  }
  listQueues() {
    return this.client.get("/scheduling/queues/");
  }
  listSchedules() {
    return this.client.get("/scheduling/plans/");
  }
  createSchedule(data: Record<string, unknown>) {
    return this.client.post("/scheduling/plans/", data);
  }

  // Editorial
  listComments(entry: string) {
    return this.client.get("/editorial/comments/", { params: { entry } });
  }
  createComment(data: Record<string, unknown>) {
    return this.client.post("/editorial/comments/", data);
  }
  listNotes(entry: string) {
    return this.client.get("/editorial/note/", { params: { entry } });
  }
  listAssignments() {
    return this.client.get("/editorial/assignment/");
  }

  // Search & analytics
  search(q: string, params?: Record<string, unknown>) {
    return this.client.get("/search/", { params: { query: q, ...params } });
  }
  analyticsDashboard(params?: Record<string, unknown>) {
    return this.client.get("/analytics/overview/", { params });
  }

  // Delivery / API mgmt
  listApiKeys() {
    return this.client.get("/delivery/keys/");
  }
  createApiKey(data: Record<string, unknown>) {
    return this.client.post("/delivery/keys/", data);
  }
  listWebhooks() {
    return this.client.get("/webhook/endpoints/");
  }
  createWebhook(data: Record<string, unknown>) {
    return this.client.post("/webhooks/endpoint/", data);
  }

  // Notifications
  listNotifications() {
    return this.client.get("/notifications/all/");
  }
  markNotificationRead(id: string) {
    return this.client.post(`/notifications/${id}/mark_read/`);
  }

  // i18n
  listTranslationJobs() {
    return this.client.get("/i18n/jobs/");
  }
  listLocales() {
    return this.client.get("/i18n/locale/");
  }
}

export const api = new ApiClient();
