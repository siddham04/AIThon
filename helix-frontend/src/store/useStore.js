import { create } from 'zustand'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem('helix_user') || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = create((set) => ({
  user: readUser(),
  token: localStorage.getItem('helix_token'),
  setAuth: (user, token) => {
    if (token) localStorage.setItem('helix_token', token)
    else localStorage.removeItem('helix_token')
    if (user) localStorage.setItem('helix_user', JSON.stringify(user))
    else localStorage.removeItem('helix_user')
    set({ user, token })
  },
  logout: () => {
    localStorage.removeItem('helix_token')
    localStorage.removeItem('helix_user')
    set({ user: null, token: null })
  },
}))

export const useProjectStore = create((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (currentProject) => set({ currentProject }),
  setLoading: (loading) => set({ loading }),
  upsertProject: (p) =>
    set({
      projects: (() => {
        const list = [...get().projects]
        const i = list.findIndex((x) => x.id === p.id)
        if (i >= 0) list[i] = p
        else list.push(p)
        return list
      })(),
    }),
}))

export const useArtifactStore = create((set, get) => ({
  stories: [],
  tasks: [],
  summary: null,
  citationItemRate: null,
  lastPipelineTimingsMs: null,
  testcases: [],
  ambiguities: [],
  rawRequirement: '',
  taskBoard: {},
  loadingArtifacts: false,
  loadingTests: false,
  setBundle: ({
    stories,
    tasks,
    summary,
    citation_item_rate: citationItemRate,
    last_pipeline_timings_ms: lastPipelineTimingsMs,
  }) =>
    set({
      stories: stories || [],
      tasks: tasks || [],
      summary: summary || null,
      citationItemRate:
        citationItemRate === undefined || citationItemRate === null
          ? null
          : Number(citationItemRate),
      lastPipelineTimingsMs: lastPipelineTimingsMs ?? null,
    }),
  setTestcases: (testcases) => set({ testcases: testcases || [] }),
  setAmbiguities: (ambiguities) => set({ ambiguities: ambiguities || [] }),
  setRawRequirement: (rawRequirement) => set({ rawRequirement }),
  setLoadingArtifacts: (loadingArtifacts) => set({ loadingArtifacts }),
  setLoadingTests: (loadingTests) => set({ loadingTests }),
  moveTask: (taskId, column) =>
    set({
      taskBoard: { ...get().taskBoard, [taskId]: column },
    }),
  resetBoard: (tasks) => {
    const board = { ...get().taskBoard }
    for (const t of tasks || []) {
      if (!board[t.id]) board[t.id] = 'todo'
    }
    set({ taskBoard: board })
  },
  setStoryExportApproval: (storyId, approved) =>
    set({
      stories: get().stories.map((s) =>
        s.id === storyId ? { ...s, approved_for_export: approved } : s,
      ),
    }),
  setTaskExportApproval: (taskId, approved) =>
    set({
      tasks: get().tasks.map((t) =>
        t.id === taskId ? { ...t, approved_for_export: approved } : t,
      ),
    }),
  resetArtifacts: () =>
    set({
      stories: [],
      tasks: [],
      summary: null,
      citationItemRate: null,
      lastPipelineTimingsMs: null,
      testcases: [],
      ambiguities: [],
      rawRequirement: '',
      taskBoard: {},
    }),
}))
