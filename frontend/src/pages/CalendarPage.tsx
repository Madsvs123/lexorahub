import { useEffect, useMemo, useState } from "react";
import {
  addDays,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import { api } from "@/api/client";
import type { CalendarEvent } from "@/types";
import { useAuthStore } from "@/stores/auth";

export function CalendarPage() {
  const publication = useAuthStore((s) => s.publication);
  const [cursor, setCursor] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);

  const rangeStart = startOfWeek(startOfMonth(cursor));
  const rangeEnd = endOfWeek(endOfMonth(cursor));
  const days = eachDayOfInterval({ start: rangeStart, end: rangeEnd });

  useEffect(() => {
    api
      .listCalendar({
        publication: publication?.id,
        start: rangeStart.toISOString(),
        end: rangeEnd.toISOString(),
      })
      .then((r) => setEvents(r.data.results || r.data))
      .catch(() => setEvents([]));
  }, [publication?.id, cursor]);

  const byDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    for (const ev of events) {
      const key = format(new Date(ev.starts_at), "yyyy/MM/dd");
      (map[key] ||= []).push(ev);
    }
    return map;
  }, [events]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Editorial calendar</h1>
          <p>Embargoes, timed publishes, campaigns, and desk deadlines.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn secondary" onClick={() => setCursor(addDays(endOfMonth(cursor), 1))}>
            Prev
          </button>
          <button className="btn secondary" onClick={() => setCursor(addDays(new Date(), -1))}>
            Today
          </button>
          <button className="btn secondary" onClick={() => setCursor(addDays(startOfMonth(cursor), -1))}>
            Next
          </button>
        </div>
      </div>
      <h2 style={{ marginBottom: 12 }}>{format(cursor, "MMMM yyyy)}</h2>
      <div className="calendar-grid">
        {days.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          return (
            <div
              key={key}
              className="calendar-cell"
              style={{ opacity: isSameMonth(day, cursor) ? 1 : 0.45 }}
            >
              <div className="day">{format(day, "d")}</div>
              {(byDay[key] || []).map((ev) => (
                <div key={ev.id} className="cal-event" style={{ background: ev.color || undefined }}>
                  {ev.title}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
