const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  // FastAPI Users expects form-urlencoded for login
  const response = await fetch(`${API_BASE_URL}/auth/jwt/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    if (error.detail === 'LOGIN_BAD_CREDENTIALS') {
      throw new Error('Invalid email or password');
    }
    throw new Error(error.detail || 'Login failed');
  }
  return response.json();
}

export async function register(email: string, password: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/jwt/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    if (error.detail === 'REGISTER_USER_ALREADY_EXISTS') {
      throw new Error('An account with this email already exists');
    }
    throw new Error(error.detail || 'Registration failed');
  }
  return response.json();
}

export async function getCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Failed to get user');
  return response.json();
}

export function logout(): void {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('auth_token_expiry');
}

export async function forgotPassword(email: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/auth/jwt/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send reset link');
  }
}

export async function resetPassword(token: string, password: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/auth/jwt/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    if (error.detail === 'RESET_PASSWORD_BAD_TOKEN') {
      throw new Error('Invalid or expired reset token');
    }
    throw new Error(error.detail || 'Password reset failed');
  }
}
