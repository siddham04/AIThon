import { useMemo } from 'react'
import DiffMatchPatch from 'diff-match-patch'

const DMP = DiffMatchPatch.default || DiffMatchPatch
const dmp = new DMP()

const DIFF_EQUAL = 0
const DIFF_INSERT = 1

function buildRequirementDiffNodes(oldText, newText) {
  const diffs = dmp.diff_main(oldText || '', newText || '')
  dmp.diff_cleanupSemantic(diffs)
  return diffs.map((part, i) => {
    const [op, text] = part
    if (op === DIFF_EQUAL) {
      return (
        <span key={i} className="diff-eq">
          {text}
        </span>
      )
    }
    if (op === DIFF_INSERT) {
      return (
        <span key={i} className="diff-ins">
          {text}
        </span>
      )
    }
    return (
      <span key={i} className="diff-del">
        {text}
      </span>
    )
  })
}

/** Semantic text diff (green = added, red = removed) — same styling as version history. */
export default function RequirementTextDiff({ oldText, newText, className = 'version-diff' }) {
  const nodes = useMemo(() => buildRequirementDiffNodes(oldText, newText), [oldText, newText])
  return <pre className={className}>{nodes}</pre>
}
