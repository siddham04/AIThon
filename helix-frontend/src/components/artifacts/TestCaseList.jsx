import { useMemo, useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { api } from '../../api/client'
import toast from 'react-hot-toast'
import { toastWithUndo } from '../../lib/toastWithUndo'

const FILTER_OPTIONS = [
  { value: 'all', label: 'All types' },
  { value: 'unit', label: 'Positive / unit' },
  { value: 'integration', label: 'Negative / integration' },
  { value: 'e2e', label: 'Edge / E2E' },
  { value: 'security', label: 'Security' },
]

function toGherkin(tc) {
  return `Feature: ${tc.title}\n\n  Scenario: ${tc.title}\n    Given ${tc.given}\n    When ${tc.when}\n    Then ${tc.then}\n`
}

export default function TestCaseList({ testcases, onRefresh, onGenerateTests, loadingTests }) {
  const [openId, setOpenId] = useState(null)
  const [filter, setFilter] = useState('all')

  const filtered = useMemo(() => {
    if (filter === 'all') return testcases || []
    return (testcases || []).filter(
      (t) => String(t.type || '').toLowerCase() === filter,
    )
  }, [testcases, filter])

  const list = filtered
  const showEmpty = !(testcases || []).length && !loadingTests
  const showLoadingList = loadingTests && !(testcases || []).length

  const toggleStatus = async (tc) => {
    const prev = tc.status ?? 'pending'
    const next = tc.status === 'passed' ? 'pending' : 'passed'
    try {
      await api.patch(`/testcases/${tc.id}/status`, { status: next })
      toastWithUndo('Test status updated', async () => {
        try {
          await api.patch(`/testcases/${tc.id}/status`, { status: prev })
          onRefresh?.()
        } catch {
          toast.error('Could not undo')
        }
      })
      onRefresh?.()
    } catch {
      toast.error('Could not update test')
    }
  }

  return (
    <div className="testcase-list">
      <div className="row spread">
        <h3>Test cases</h3>
        <select
          className="select"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter by type"
          disabled={!(testcases || []).length}
        >
          {FILTER_OPTIONS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </div>
      <p className="muted small">Gherkin preview with syntax highlighting.</p>
      {showLoadingList ? (
        <p className="muted small">Loading test cases…</p>
      ) : showEmpty ? (
        <div className="panel-empty testcase-empty">
          <p className="muted small">No test cases yet. Generate Gherkin-style cases from your artifacts.</p>
          {onGenerateTests ? (
            <button
              type="button"
              className="btn btn-primary"
              disabled={loadingTests}
              onClick={() => onGenerateTests()}
            >
              Generate tests
            </button>
          ) : null}
        </div>
      ) : (
        <div className="accordion">
          {list.map((tc) => {
            const open = openId === tc.id
            return (
              <div key={tc.id} className="acc-item">
                <button
                  type="button"
                  className="acc-head"
                  onClick={() => setOpenId(open ? null : tc.id)}
                >
                  <span>{tc.title}</span>
                  <span className="badge subtle">{tc.type || 'case'}</span>
                </button>
                {open && (
                  <div className="acc-body">
                    <SyntaxHighlighter language="gherkin" style={oneDark} wrapLongLines>
                      {toGherkin(tc)}
                    </SyntaxHighlighter>
                    <label className="toggle-line">
                      <input
                        type="checkbox"
                        checked={tc.status === 'passed'}
                        onChange={() => void toggleStatus(tc)}
                      />
                      Pass
                    </label>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
