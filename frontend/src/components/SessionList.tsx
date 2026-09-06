import { useMemo, useState } from "react";
import { SessionCard, type Role, type Session, type Student } from "./SessionCard";

type SessionFilter = "ALL" | "IN_PROGRESS" | "SCHEDULED" | "PAST";

const filters: Array<{ value: SessionFilter; label: string }> = [
  { value: "ALL", label: "All sessions" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "SCHEDULED", label: "Scheduled" },
  { value: "PAST", label: "Past history" },
];

type SessionListProps = {
  sessions: Session[];
  role: Role;
  students?: Student[];
  emptyMessage?: string;
};

function matchesFilter(session: Session, filter: SessionFilter) {
  if (filter === "ALL") return true;
  if (filter === "PAST") return session.status === "COMPLETED" || session.status === "AI_REVIEWED";
  return session.status === filter;
}

export function SessionList({ sessions, role, students = [], emptyMessage = "No sessions match this filter." }: SessionListProps) {
  const [filter, setFilter] = useState<SessionFilter>("ALL");
  const filteredSessions = useMemo(
    () => sessions.filter((session) => matchesFilter(session, filter)),
    [sessions, filter],
  );

  return (
    <section className="session-list" aria-label="Sessions">
      <div className="session-filter-tabs" role="tablist" aria-label="Session filters">
        {filters.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={filter === item.value}
            className={filter === item.value ? "session-filter-tab active" : "session-filter-tab"}
            onClick={() => setFilter(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {filteredSessions.length === 0 ? <p className="empty-state">{emptyMessage}</p> : null}
      <div className="card-list">
        {filteredSessions.map((session) => (
          <SessionCard key={session.id} session={session} role={role} students={students} />
        ))}
      </div>
    </section>
  );
}
