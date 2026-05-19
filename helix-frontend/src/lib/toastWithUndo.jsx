import toast from 'react-hot-toast'

/** Toast with inline Undo; `undoFn` is only reliable until the toast auto-dismisses. */
export function toastWithUndo(message, undoFn, options = {}) {
  const duration = options.duration ?? 5000
  toast.custom(
    (t) => (
      <div className="toast-undo-wrap">
        <span>{message}</span>
        <button
          type="button"
          className="toast-undo-btn"
          onClick={() => {
            void Promise.resolve(undoFn()).finally(() => toast.dismiss(t.id))
          }}
        >
          Undo
        </button>
      </div>
    ),
    { duration },
  )
}
