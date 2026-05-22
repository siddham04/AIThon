import { create } from 'zustand'
import {
  clearAuthStorage,
  readAuthToken,
  readAuthUser,
  writeAuthToken,
  writeAuthUser,
} from '../lib/authTokenStorage'

export const useAuthStore = create((set) => ({
  user: readAuthUser(),
  token: readAuthToken() || null,
  setAuth: (user, token) => {
    writeAuthToken(token)
    writeAuthUser(user)
    set({ user, token })
  },
  logout: () => {
    clearAuthStorage()
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
