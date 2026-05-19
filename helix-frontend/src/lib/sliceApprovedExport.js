/** Match backend `slice_for_export`: approved tasks need approved parent story when linked. */
export function sliceApprovedForExport(stories, tasks) {
  const ss = (stories || []).filter((s) => s.approved_for_export)
  const storyIds = new Set(ss.map((s) => s.id))
  const tt = (tasks || []).filter(
    (t) =>
      t.approved_for_export && (!t.story_id || storyIds.has(t.story_id)),
  )
  return { stories: ss, tasks: tt }
}
