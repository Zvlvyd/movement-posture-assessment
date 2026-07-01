import { create } from 'zustand';
import type { User } from '../types';
import { authApi } from '../services/api';

function safeGetUser(): User | null {
  try {
    const raw = localStorage.getItem('user');
    if (!raw || raw === 'null') return null;
    return JSON.parse(raw);
  } catch {
    localStorage.removeItem('user');
    return null;
  }
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, phone?: string, gender?: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: safeGetUser(),
  token: localStorage.getItem('token'),
  loading: false,
  login: async (username, password) => {
    set({ loading: true });
    try {
      const res = await authApi.login({ username, password });
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
      set({ user: res.user, token: res.access_token, loading: false });
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },
  register: async (username, password, phone?, gender?) => {
    set({ loading: true });
    try {
      await authApi.register({ username, password, phone, gender });
      set({ loading: false });
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ user: null, token: null });
  },
  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user));
    set({ user });
  },
  fetchUser: async () => {
    try {
      const user = await authApi.me();
      set({ user });
    } catch {
      // Clear stale auth data on failure
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      set({ user: null, token: null });
    }
  },
}));
