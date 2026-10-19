export type UUID = string;

export interface User {
  id: UUID;
  email: string;
  display_name: string;
  avatar_url?: string;
  locale: string;
  timezone: string;
  preferences?: Record<string, unknown>;
}

export interface Organization {
  id: UUID;
  name: string;
  slug: string;
  primary_locale: string;
  timezone: string;
  logo_url?: string;
}

export interface Publication {
  id: UUID;
  name: string;
  slug: string;
  default_locale: string;
  supported_locales: string[];
  website_url?: string;
  is_active: boolean;
}

export interface Role {
  id: UUID;
  name: string;
  slug: string;
  privilege_codes: string[];
  is_org_admin: boolean;
  can_publish: boolean;
}

export interface Membership {
  id: UUID;
  organization: Organization;
  role: Role;
  publication_ids: UUID[];
  title?: string;
}

export type EntryStatus =
  | "draft"
  | "assigned"
  | "in_review"
  | "copy_edit"
  | "pending_approval"
  | "approved"
  | "scheduled"
  | "published"
  | "updated"
  | "correction"
  | "unpublished"
  | "archived";

export interface ContentEntry {
  id: UUID;
  publication: UUID;
  content_type: UUID;
  content_type_slug?: string;
  title: string;
  slug: string;
  locale: string;
  status: EntryStatus;
  body: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  excerpt: string;
  seo: SeoMeta;
  social: SocialMeta;
  authors?: UUID[];
  author_names?: string[];
  terms?: UUID[];
  featured_image?: UUID | null;
  assigned_to?: UUID | null;
  assigned_to_name?: string | null;
  published_at?: string | null;
  scheduled_for?: string | null;
  embargo_until?: string | null;
  revision_number: number;
  word_count: number;
  reading_time_minutes: number;
  path: string;
  is_locked?: boolean;
  locked_by?: UUID | null;
  updated_at: string;
  created_at: string;
}

export interface SeoMeta {
  title?: string;
  description?: string;
  canonical_url?: string;
  robots?: string[];
  og_image?: string;
}

export interface SocialMeta {
  twitter_title?: string;
  twitter_description?: string;
  facebook_title?: string;
  facebook_description?: string;
}

export interface ContentType {
  id: UUID;
  name: string;
  slug: string;
  description?: string;
  fields: FieldDefinition[];
  is_translatable: boolean;
  workflow_enabled: boolean;
}

export interface FieldDefinition {
  id: UUID;
  name: string;
  api_key: string;
  field_type: string;
  is_required: boolean;
  help_text?: string;
  validation?: Record<string, unknown>;
  options?: Record<string, unknown>;
  sort_order: number;
  group?: string;
}

export interface MediaAsset {
  id: UUID;
  title: string;
  asset_type: string;
  url?: string;
  mime_type: string;
  width?: number;
  height?: number;
  alt_text: string;
  caption: string;
  credit: string;
  copyright: string;
  focal_x: number;
  focal_y: number;
  file_size: number;
  library_name?: string;
  created_at: string;
}

export interface CalendarEvent {
  id: UUID;
  title: string;
  starts_at: string;
  ends_at?: string;
  event_type: string;
  publication: UUID;
  entry?: UUID;
  color?: string;
}

export interface NotificationItem {
  id: UUID;
  title: string;
  body: string;
  category: string;
  is_read: boolean;
  created_at: string;
  link?: string;
}

export interface AnalyticsDashboard {
  total_views: number;
  unique_sessions: number;
  published_count: number;
  draft_count: number;
  by_day: { day: string; views: number }[];
  top_entries: { entry_id: string; entry__title: string; views: number }[];
  status_breakdown: { status: string; total: number }[];
}

export interface PresenceUser {
  id: UUID;
  display_name: string;
  avatar_url?: string;
  color: string;
}

export interface WebhookEndpoint {
  id: UUID;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
}

export interface ApiKey {
  id: UUID;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at?: string;
  key?: string;
}
