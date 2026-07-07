import { create } from 'zustand'
import { User } from '@/types'

interface SessionState {
  user: User | null;
  sidebarOpen: boolean;
  wsStatus: 'connected' | 'reconnecting' | 'disconnected';
  setUser: (user: User | null) => void;
  toggleSidebar: () => void;
  setWsStatus: (status: 'connected' | 'reconnecting' | 'disconnected') => void;
}

export const useStore = create<SessionState>((set) => ({
  user: null, // Will be set after login
  sidebarOpen: true,
  wsStatus: 'disconnected',
  setUser: (user) => set({ user }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setWsStatus: (status) => set({ wsStatus: status }),
}));

export const useRole = () => {
  const user = useStore((state) => state.user);
  return user?.role || null;
}
