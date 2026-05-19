import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd'
import { motion, useReducedMotion } from 'framer-motion'
import { useArtifactStore } from '../../store/useStore'
import { toastWithUndo } from '../../lib/toastWithUndo'

const COLS = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'done', title: 'Done' },
]

function priorityClass(p) {
  const v = String(p || '').toLowerCase()
  if (v === 'critical') return 'prio crit'
  if (v === 'high') return 'prio high'
  if (v === 'low') return 'prio low'
  return 'prio med'
}

const EXPORT_GATE_HELP =
  'Only items marked approved for export are sent when you enable “Approved only” on exports — unreviewed work stays in Helix.'

export default function KanbanBoard({
  tasks,
  onGenerateArtifacts,
  projectId,
  onTaskExportToggle,
}) {
  const reduceMotion = useReducedMotion()
  const taskBoard = useArtifactStore((s) => s.taskBoard)
  const moveTask = useArtifactStore((s) => s.moveTask)

  const grouped = { todo: [], in_progress: [], done: [] }
  for (const t of tasks || []) {
    const col = taskBoard[t.id] || 'todo'
    grouped[col].push(t)
  }

  const onDragEnd = (result) => {
    const { destination, source, draggableId } = result
    if (!destination) return
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return
    }
    const fromCol = source.droppableId
    const toCol = destination.droppableId
    moveTask(draggableId, toCol)
    if (fromCol !== toCol) {
      toastWithUndo('Task moved', () => {
        moveTask(draggableId, fromCol)
      })
    }
  }

  if (!(tasks || []).length) {
    return (
      <motion.div
        className="panel-empty kanban-empty"
        initial={reduceMotion ? false : { opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 380, damping: 28 }}
      >
        <p className="muted small">No tasks yet. Generate artifacts from your requirements to populate the board.</p>
        {onGenerateArtifacts ? (
          <motion.button
            type="button"
            className="btn btn-primary"
            onClick={() => onGenerateArtifacts()}
            whileHover={reduceMotion ? undefined : { scale: 1.03 }}
            whileTap={reduceMotion ? undefined : { scale: 0.97 }}
          >
            Generate artifacts
          </motion.button>
        ) : null}
      </motion.div>
    )
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="kanban">
        {COLS.map((col) => (
          <Droppable droppableId={col.id} key={col.id}>
            {(provided, snap) => (
              <motion.div
                ref={provided.innerRef}
                {...provided.droppableProps}
                className={`kanban-col ${snap.isDraggingOver ? 'drag-over' : ''}`}
                initial={reduceMotion ? false : { opacity: 0, y: 16 }}
                animate={{
                  opacity: 1,
                  y: 0,
                  scale: reduceMotion ? 1 : snap.isDraggingOver ? 1.012 : 1,
                  boxShadow: snap.isDraggingOver
                    ? '0 0 0 1px rgba(56, 189, 248, 0.45), 0 16px 48px rgba(14, 165, 233, 0.14)'
                    : '0 0 0 0px transparent',
                }}
                transition={
                  reduceMotion
                    ? { duration: 0.01 }
                    : {
                        type: 'spring',
                        stiffness: 420,
                        damping: 32,
                      }
                }
              >
                <h3>{col.title}</h3>
                {grouped[col.id].map((task, index) => (
                  <Draggable draggableId={task.id} index={index} key={task.id}>
                    {(p, dragSnap) => (
                      <div
                        ref={p.innerRef}
                        {...p.draggableProps}
                        className={`kanban-card${dragSnap.isDragging ? ' is-dragging' : ''}`}
                      >
                        <div className="kanban-card-top" {...p.dragHandleProps}>
                          <span className={priorityClass(task.priority)}>
                            {task.priority || 'medium'}
                          </span>
                          <span className="points">{task.estimate_points ?? '—'} pts</span>
                        </div>
                        <p className="kanban-title">{task.title}</p>
                        {projectId && onTaskExportToggle && task.id ? (
                          <label
                            className="kanban-export-toggle muted small"
                            title={EXPORT_GATE_HELP}
                            onClick={(e) => e.stopPropagation()}
                            onPointerDown={(e) => e.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              checked={!!task.approved_for_export}
                              onChange={(e) =>
                                void onTaskExportToggle(task.id, e.target.checked)
                              }
                              aria-label={`Approve task “${task.title || task.id}” for export`}
                            />
                            Export OK
                          </label>
                        ) : null}
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </motion.div>
            )}
          </Droppable>
        ))}
      </div>
    </DragDropContext>
  )
}
