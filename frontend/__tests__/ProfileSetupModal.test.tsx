import React from 'react';
import { render, screen } from '@testing-library/react';
import { z } from 'zod';
import { ProfileSetupModal } from '@/components/ProfileSetupModal';

// Mock AuthContext
const mockRefreshProfile = jest.fn();
let mockUser: {
  full_name: string | null;
  institution: string | null;
  profession: string | null;
  email: string;
  id: string;
  role: string;
} | null = null;

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    refreshProfile: mockRefreshProfile,
    getToken: () => 'test-token',
  }),
}));

jest.mock('next-intl', () => ({
  useTranslations: () => (k: string) => k,
}));

jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('@/lib/api/auth', () => ({
  updateProfile: jest.fn().mockResolvedValue({}),
}));

// Schema for schema-level tests (same shape as target implementation)
const profileSetupSchema = z.object({
  full_name: z.string().min(1, 'required').max(200),
  institution: z.string().min(1, 'required').max(200),
  profession: z.string().min(1, 'required').max(200),
});

describe('ProfileSetupModal', () => {
  beforeEach(() => {
    sessionStorage.clear();
    jest.clearAllMocks();
  });

  it('opens when user.full_name is null', () => {
    mockUser = { id: '1', email: 'test@example.com', role: 'user', full_name: null, institution: 'X', profession: 'Y' };
    render(<ProfileSetupModal />);
    expect(screen.queryByRole('dialog')).not.toBeNull();
  });

  it('opens when user.institution is null', () => {
    mockUser = { id: '1', email: 'test@example.com', role: 'user', full_name: 'Alice', institution: null, profession: 'Y' };
    render(<ProfileSetupModal />);
    expect(screen.queryByRole('dialog')).not.toBeNull();
  });

  it('opens when user.profession is null', () => {
    mockUser = { id: '1', email: 'test@example.com', role: 'user', full_name: 'Alice', institution: 'X', profession: null };
    render(<ProfileSetupModal />);
    expect(screen.queryByRole('dialog')).not.toBeNull();
  });

  it('does NOT open when all three fields are filled', () => {
    mockUser = { id: '1', email: 'test@example.com', role: 'user', full_name: 'Alice', institution: 'X', profession: 'Y' };
    render(<ProfileSetupModal />);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('does NOT open when sessionStorage profile_setup_dismissed is set', () => {
    sessionStorage.setItem('profile_setup_dismissed', '1');
    mockUser = { id: '1', email: 'test@example.com', role: 'user', full_name: null, institution: null, profession: null };
    render(<ProfileSetupModal />);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('Zod schema rejects empty institution', () => {
    const result = profileSetupSchema.safeParse({ full_name: 'A', institution: '', profession: 'Y' });
    expect(result.success).toBe(false);
  });

  it('Zod schema rejects empty profession', () => {
    const result = profileSetupSchema.safeParse({ full_name: 'A', institution: 'X', profession: '' });
    expect(result.success).toBe(false);
  });

  it('Zod schema accepts all three fields filled', () => {
    const result = profileSetupSchema.safeParse({ full_name: 'A', institution: 'X', profession: 'Y' });
    expect(result.success).toBe(true);
  });
});
