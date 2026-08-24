import createMiddleware from 'next-intl/middleware';
import { NextRequest, NextResponse } from 'next/server';
import { locales, defaultLocale, localePrefix } from './i18n/config';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix,
});

// Site-wide HTTP Basic Auth gate. Unset BASIC_AUTH_USER/PASSWORD (e.g. local
// dev) disables it entirely — no accidental lockout of `npm run dev`.
export default function proxy(request: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASSWORD;

  if (user && pass) {
    const auth = request.headers.get('authorization');
    const [scheme, encoded] = auth?.split(' ') ?? [];
    const [u, p] = scheme === 'Basic' && encoded ? atob(encoded).split(':') : [];
    if (u !== user || p !== pass) {
      return new NextResponse('Authentication required', {
        status: 401,
        headers: { 'WWW-Authenticate': 'Basic realm="Inclusify"' },
      });
    }
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
};
