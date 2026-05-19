export function SkeletonPulse({ className = '', style }) {
  return <div className={`skeleton-pulse ${className}`.trim()} style={style} />
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard-grid">
      <SkeletonPulse className="sk-summary" />
      <SkeletonPulse className="sk-kanban" />
      <SkeletonPulse className="sk-tests" />
      <SkeletonPulse className="sk-chat" />
    </div>
  )
}

export function CardRowSkeleton({ rows = 4 }) {
  return (
    <div className="sk-stack">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonPulse key={i} className="sk-row" />
      ))}
    </div>
  )
}

export function SidebarSkeleton() {
  return (
    <aside className="sidebar sk-sidebar">
      <SkeletonPulse className="sk-logo" />
      <CardRowSkeleton rows={6} />
    </aside>
  )
}
