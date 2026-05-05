import { create } from 'zustand'

interface AppState {
  initialized: boolean
  setInitialized: (v: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  initialized: false,
  setInitialized: (v) => set({ initialized: v }),
}))
