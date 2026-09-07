import type { ReactNode } from "react";

export type SessionStatus = "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "AI_REVIEWED";

type StatusBadgeProps = {
  status: SessionStatus;
  children?: ReactNode;
};

const labels: Record<SessionStatus, string> = {
  SCHEDULED: "Scheduled",
  IN_PROGRESS: "In Progress",
  COMPLETED: "Completed",
  AI_REVIEWED: "AI Reviewed",
};

export function getStudentVisibleStatus(status: SessionStatus): Exclude<SessionStatus, "AI_REVIEWED"> {
  return status === "AI_REVIEWED" ? "COMPLETED" : status;
}

export function StatusBadge({ status, children }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-${status.toLowerCase()}`}>
      {children ?? labels[status]}
    </span>
  );
}
