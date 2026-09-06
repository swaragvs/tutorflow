import type { ReactNode } from "react";

type BottomPanelProps = {
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
};

export function BottomPanel({ collapsed, onToggle, children }: BottomPanelProps) {
  return (
    <section className={`bottom-panel ${collapsed ? "is-collapsed" : ""}`}>
      <div className="workspace-panel-header">
        <span className="panel-kicker">Session workspace</span>
        <button type="button" className="icon-button" onClick={onToggle} aria-label={collapsed ? "Expand bottom panel" : "Collapse bottom panel"}>
          {collapsed ? "⌃" : "⌄"}
        </button>
      </div>
      {!collapsed ? <div className="bottom-panel-content">{children}</div> : null}
    </section>
  );
}
