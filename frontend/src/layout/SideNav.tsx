import { Link, NavLink } from "react-router-dom";

type Role = "TUTOR" | "STUDENT";

type SideNavProps = {
  role: Role | null;
  collapsed: boolean;
};

function NavItem({ to, icon, label, passive = false }: { to: string; icon: string; label: string; passive?: boolean }) {
  if (passive) {
    return (
      <Link to={to} className="side-nav-link" title={label}>
        <span className="side-nav-icon" aria-hidden="true">{icon}</span>
        <span className="side-nav-label">{label}</span>
      </Link>
    );
  }
  return (
    <NavLink to={to} end={label === "Dashboard"} className="side-nav-link" title={label}>
      <span className="side-nav-icon" aria-hidden="true">{icon}</span>
      <span className="side-nav-label">{label}</span>
    </NavLink>
  );
}

export function SideNav({ role, collapsed }: SideNavProps) {
  return (
    <aside className={`side-nav ${collapsed ? "is-collapsed" : ""}`} aria-label="Primary navigation">
      <div className="side-nav-heading">Menu</div>
      {role === "STUDENT" ? (
        <>
          <NavItem to="/student/dashboard" icon="⌂" label="Dashboard" />
          <NavItem to="/student/history" icon="▤" label="History" />
        </>
      ) : (
        <>
          <NavItem to="/dashboard" icon="⌂" label="Dashboard" />
          <NavItem to="/students" icon="◉" label="Students" />
          <NavItem to="/dashboard" icon="▣" label="Sessions" passive />
        </>
      )}
    </aside>
  );
}
