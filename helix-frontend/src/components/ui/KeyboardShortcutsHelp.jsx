/**
 * Shared shortcuts sheet for hackathon demo / judge walkthrough.
 */
export default function KeyboardShortcutsHelp({ open, onClose, variant = 'ingest' }) {
  if (!open) return null

  const common = (
    <>
      <li>
        <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> — command palette (jump anywhere)
      </li>
      <li>
        <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>K</kbd> — focus copilot
      </li>
      <li>
        <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>E</kbd> — scroll to export hub
      </li>
      <li>
        <kbd>?</kbd> — toggle this panel (when not typing in a field)
      </li>
    </>
  )

  return (
    <dialog open className="modal" onClick={onClose}>
      <div className="modal-card modal-card--shortcuts" onClick={(e) => e.stopPropagation()}>
        <h3>Keyboard shortcuts</h3>
        <ul className="shortcuts-list">
          {variant === 'ingest' ? (
            <li>
              <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Enter</kbd> — submit ingest (paste / URL / file tab)
            </li>
          ) : (
            <>
              <li>
                <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Enter</kbd> — run generate artifacts (when focus is in the
                requirement editor)
              </li>
              <li>Readiness rows — click to jump to the related panel</li>
            </>
          )}
          {common}
        </ul>
        <button type="button" className="btn" onClick={onClose}>
          Close
        </button>
      </div>
    </dialog>
  )
}
