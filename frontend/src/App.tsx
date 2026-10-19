import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { EntriesPage } from "@/pages/EntriesPage";
import { EditorPage } from "@/pages/EditorPage";
import { QueuesPage } from "@/pages/QueuesPage";
import { CalendarPage } from "@/pages/CalendarPage";
import { MediaPage } from "@/pages/MediaPage";
import { AuthorsPage } from "@/pages/AuthorsPage";
import { TaxonomiesPage } from "@/pages/TaxonomiesPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { ApiKeysPage } from "@/pages/ApiKeysPage";
import { WebhooksPage } from "@/pages/WebhooksPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { WorkflowPage } from "@/pages/WorkflowPage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading, bootstrap } = useAuthStore();
  useEffect(() => {
    bootstrap();
  }, [user]);
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="entries" element={<EntriesPage />} />
        <Route path="entries/:slug" element={<EditorPage />} />
        <Route path="entries/new" element={<EditorPage />} />
        <Route path="queues" element={<QueuesPage />} />
        <Route path="workflow" element={<WorkflowPage />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="media" element={<MediaPage />} />
        <Route path="authors" element={<AuthorsPage />} />
        <Route path="taxonomies" element={<TaxonomiesPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="api-keys" element={<ApiKeysPage />} />
        <Route path="webhooks" element={<WebhooksPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
