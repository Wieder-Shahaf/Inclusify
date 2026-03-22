import OAuthCallbackClient from './OAuthCallbackClient';

// This must be in a Server Component to take effect
export const dynamic = 'force-dynamic';

export default function OAuthCallbackPage() {
  return <OAuthCallbackClient />;
}
