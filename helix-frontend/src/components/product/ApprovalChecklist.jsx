/**
 * Human-in-the-loop summary — AI did the work; human approves before export.
 */
export default function ApprovalChecklist({
  items,
  approved = false,
  compact = false,
}) {
  const ready = items.filter((i) => i.done).length
  const total = items.length

  return (
    <section
      className={`hx-approval${compact ? ' hx-approval--compact' : ''}`}
      aria-label="AI deliverables ready for your approval"
    >
      <p className="hx-approval-kicker muted small">
        Autonomous by default — nothing goes to Jira until you approve
      </p>
      <ul className="hx-approval-list">
        {items.map((item) => (
          <li
            key={item.id}
            className={`hx-approval-row${item.done ? ' is-done' : ' is-pending'}`}
          >
            <span className="hx-approval-mark" aria-hidden>
              {item.done ? '✓' : '○'}
            </span>
            <span className="hx-approval-label">{item.label}</span>
            {item.detail != null && item.detail !== '' && (
              <span className="hx-approval-detail muted small">{item.detail}</span>
            )}
          </li>
        ))}
      </ul>
      {!compact && (
        <p className="hx-approval-foot muted small">
          {ready}/{total} ready
          {approved ? ' · Approved for export' : ' · Review details below, then Approve & Export'}
        </p>
      )}
    </section>
  )
}
