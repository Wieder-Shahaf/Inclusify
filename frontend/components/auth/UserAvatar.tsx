'use client';

// Hash function for consistent color per email
function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return hash;
}

const AVATAR_COLORS = [
  'bg-red-500', 'bg-orange-500', 'bg-amber-500', 'bg-yellow-500',
  'bg-lime-500', 'bg-green-500', 'bg-emerald-500', 'bg-teal-500',
  'bg-cyan-500', 'bg-sky-500', 'bg-blue-500', 'bg-indigo-500',
  'bg-violet-500', 'bg-purple-500', 'bg-fuchsia-500', 'bg-pink-500',
];

interface UserAvatarProps {
  email: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function UserAvatar({ email, size = 'md', className = '' }: UserAvatarProps) {
  // Get first two characters (handles single-char emails)
  const initials = email.slice(0, 2).toUpperCase();

  // Consistent color based on email hash
  const colorIndex = Math.abs(hashCode(email)) % AVATAR_COLORS.length;
  const bgColor = AVATAR_COLORS[colorIndex];

  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
  };

  return (
    <div
      className={`${sizeClasses[size]} ${bgColor} rounded-full flex items-center justify-center text-white font-medium ${className}`}
      aria-label={`Avatar for ${email}`}
    >
      {initials}
    </div>
  );
}
