'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { toast } from 'sonner';
import * as authApi from '@/lib/api/auth';

interface User {
  id: string;
  email: string;
  role: string;
  full_name: string | null;
  profession: string | null;
  institution: string | null;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  getToken: () => string | null;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const getToken = useCallback(() => {
    return localStorage.getItem('auth_token');
  }, []);

  const validateAndSetUser = useCallback(async (token: string) => {
    try {
      const [userData, profile] = await Promise.all([
        authApi.getCurrentUser(token),
        authApi.getProfile(token).catch(() => ({ full_name: null, profession: null, institution: null })),
      ]);
      setUser({
        id: userData.id,
        email: userData.email,
        role: userData.role || 'user',
        full_name: profile.full_name,
        profession: profile.profession,
        institution: profile.institution,
      });
    } catch {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_token_expiry');
      setUser(null);
    }
  }, []);

  /* eslint-disable react-hooks/set-state-in-effect -- Async hydration from localStorage on mount */
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    const expiry = localStorage.getItem('auth_token_expiry');

    if (token && expiry) {
      const expiryDate = new Date(expiry);
      if (expiryDate > new Date()) {
        validateAndSetUser(token).finally(() => setIsLoading(false));
      } else {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_token_expiry');
        setIsLoading(false);
      }
    } else {
      setIsLoading(false);
    }
  }, [validateAndSetUser]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    localStorage.setItem('auth_token', access_token);

    const expiry = new Date();
    expiry.setDate(expiry.getDate() + 30);
    localStorage.setItem('auth_token_expiry', expiry.toISOString());

    await validateAndSetUser(access_token);
  };

  const register = async (email: string, password: string) => {
    await authApi.register(email, password);
    await login(email, password);
  };

  const refreshProfile = useCallback(async () => {
    const token = localStorage.getItem('auth_token');
    if (!token || !user) return;
    const profile = await authApi.getProfile(token);
    setUser(prev => prev ? { ...prev, ...profile } : null);
  }, [user]);

  const logout = () => {
    authApi.logout();
    setUser(null);
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, getToken, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
