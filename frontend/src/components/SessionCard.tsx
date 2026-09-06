import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { StatusBadge, type SessionStatus } from "./StatusBadge";
import { formatSessionTime } from "../utils/formatSessionTime";

export type Role = "TUTOR" | "STUDENT";

export type Student = {
  id: string;
  user_id: string;
  tutor_id: string;
  name?: string | null;
  email?: string;
  learning_goals?: string | null;
  skill_level?: string | null;
  preferences?: string | null;
};

export type Session = {
  id: string;
  tutor_id: string;
  student_id: string;
  start_time: string;
  end_time: string;
  status: SessionStatus;
  notes?: string | null;
  homework?: string | null;
  ai_plan?: string | null;
  ai_summary?: string | null;
  created_at: string;
  updated_at: string;
  student_name?: string | null;
  tutor_name?: string | null;
};

type SessionCardProps = {
  session: Session;
  role: Role;
  students?: Student[];
  actions?: ReactNode;
};

function counterpartName(session: Session, role: Role, students: Student[]) {
  if (role === "STUDENT") return session.tutor_name || "Your tutor";
  const student = students.find((item) => item.user_id === session.student_id);
  return session.student_name || student?.name || student?.email || "Tutor";
}

export function SessionCard({ session, role, students = [], actions }: SessionCardProps) {
  const href = role === "STUDENT" ? `/student/sessions/${session.id}` : `/sessions/${session.id}`;
  return (
    <article className="session-card unified-session-card">
      <Link to={href} className="session-card-link">
        <div className="row-between">
          <strong>{counterpartName(session, role, students)}</strong>
          <StatusBadge status={session.status} />
        </div>
        <div><strong>Session time:</strong> {formatSessionTime(session.start_time, session.end_time, session.status)}</div>
      </Link>
      {actions ? <div className="session-card-actions">{actions}</div> : null}
    </article>
  );
}
