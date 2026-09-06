type Role = "TUTOR" | "STUDENT";

type StatusBarProps = {
  role: Role | null;
  userLabel: string;
  onLogout: () => void;
};

export function StatusBar({ role, userLabel, onLogout }: StatusBarProps) {
  return (
    <footer className="status-bar">
      <div className="account-cluster">
        <span className="status-online" aria-hidden="true" />
        <span>{userLabel}</span>
        <span className="status-role">{role === "STUDENT" ? "Student" : "Tutor"}</span>
        <button type="button" className="status-logout" onClick={onLogout}>Logout</button>
      </div>
    </footer>
  );
}
