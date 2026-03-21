'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { toast } from 'sonner';
import * as authApi from '@/lib/api/auth';

interface User {
  id: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string, rememberMe: boolean) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  getToken: () => string | null;
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
      const userData = await authApi.getCurrentUser(token);
      setUser({ id: userData.id, email: userData.email, role: userData.role || 'user' });
    } catch {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_token_expiry');
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    const expiry = localStorage.getItem('auth_token_expiry');

    if (token && expiry) {
      const expiryDate = new Date(expiry);
      if (expiryDate > new Date()) {
        validateAndSetUser(token).finally(() => setIsLoading(false)); // eslint-disable-line react-compiler/react-compiler
      } else {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_token_expiry');
        setIsLoading(false);
      }
    } else {
      setIsLoading(false);
    }
  }, [validateAndSetUser]);

  const login = async (email: string, password: string, rememberMe: boolean) => {
    const { access_token } = await authApi.login(email, password);
    localStorage.setItem('auth_token', access_token);

    // Per CONTEXT.md: rememberMe = 30 days, else session only (1 day)
    const expiryDays = rememberMe ? 30 : 1;
    const expiry = new Date();
    expiry.setDate(expiry.getDate() + expiryDays);
    localStorage.setItem('auth_token_expiry', expiry.toISOString());

    await validateAndSetUser(access_token);
  };

  const register = async (email: string, password: string) => {
    await authApi.register(email, password);
    // After registration, log in automatically
    await login(email, password, false);
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, getToken }}>
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
