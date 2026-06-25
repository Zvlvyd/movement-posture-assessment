import { create } from 'zustand';
import type { User } from '../types';
import { authApi } from '../services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, phone?: string, gender?: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token'),
  loading: false,
  login: async (username, password) => {
    const res = await authApi.login({ username, password });
    localStorage.setItem('token', res.access_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    set({ user: res.user, token: res.access_token });
  },
  register: async (username, password, phone?, gender?) => {
    await authApi.register({ username, password, phone, gender });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ user: null, token: null });
  },
  fetchUser: async () => {
    try {
      const user = await authApi.me();
      set({ user });
    } catch { set({ user: null, token: null }); }
  },
}));
