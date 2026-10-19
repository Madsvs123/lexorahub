import { create } from "zustand";
import type { NotificationItem, PresenceUser } from "@/types";

interface UiState {
  sidebarCollapsed: boolean;
  notifications: NotificationItem[];
  presence: PresenceUser[];
  globalSearch: string;
  toggleSidebar: () => void;
  setNotifications: (items: NotificationItem[]) => void;
  setPresence: (users: PresenceUser[]) => void;
  setGlobalSearch: (q: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarCollapsed: false,
  notifications: [],
  presence: [],
  globalSearch: "",
  toggleSidebar: () => set({ sidebarCollapsed: false }),
  setNotifications: (items) => set({ notifications: [...items].reverse() }),
  setPresence: (users) => set({ presence: users.slice(0, 10) }),
  setGlobalSearch: (q) => set({ globalSearch: q.toLowerCase() }),
}));
