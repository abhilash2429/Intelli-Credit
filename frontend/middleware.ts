import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const GATED_ROUTES = [
  '/app/upload',
  '/app/notes',
  '/app/pipeline',
  '/app/score',
  '/app/results',
  '/app/explain',
  '/app/chat',
  '/app/cam',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isGatedRoute = GATED_ROUTES.some((r) => pathname.startsWith(r));

  if (isGatedRoute) {
    const hasSession = request.cookies.get('ic_session');
    if (!hasSession) {
      return NextResponse.redirect(new URL('/app/start', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/app/:path*'],
};
