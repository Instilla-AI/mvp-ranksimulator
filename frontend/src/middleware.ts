import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  const { pathname } = request.nextUrl;

  // Public paths that don't require authentication
  const publicPaths = ['/signin', '/signup'];
  const isPublicPath = publicPaths.some(path => pathname.startsWith(path));

  // If trying to access protected route without token, redirect to signin
  if (!token && !isPublicPath) {
    const url = request.nextUrl.clone();
    url.pathname = '/signin';
    return NextResponse.redirect(url);
  }

  // If logged in and trying to access signin/signup, redirect to audit-ai
  if (token && isPublicPath) {
    const url = request.nextUrl.clone();
    url.pathname = '/audit-ai';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/',
    '/audit-ai/:path*',
    '/profile/:path*',
    '/signin',
    '/signup',
  ],
};
