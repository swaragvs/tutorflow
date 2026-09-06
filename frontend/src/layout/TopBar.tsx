import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type Role = "TUTOR" | "STUDENT";

type TopBarProps = {
  role: Role | null;
  actions?: ReactNode;
  onMenuToggle: () => void;
};

export function TopBar({ role, actions, onMenuToggle }: TopBarProps) {
  return (
    <header className="ide-topbar">
      <button type="button" className="icon-button menu-button" onClick={onMenuToggle} aria-label="Toggle navigation">
        <span aria-hidden="true">☰</span>
      </button>
      <Link to={role === "STUDENT" ? "/student/dashboard" : "/dashboard"} className="ide-brand">
        <span className="brand-mark" aria-hidden="true">TF</span>
        <span>TutorFlow</span>
      </Link>
      <div className="topbar-spacer" />
      {actions ? <div className="topbar-primary">{actions}</div> : null}
    </header>
  );
}
