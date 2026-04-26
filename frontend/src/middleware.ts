import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware to protect routes that require authentication.
 *
 * Public paths (no auth required):
 * - /login
 * - /register
 * - /api/auth/* (auth endpoints are public)
 * - /_next (static assets)
 * - any static files
 *
 * All other paths require a valid access_token cookie.
 */
export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Skip auth for public routes
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/api/auth/") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    request.nextUrl.pathname.endsWith(".png") ||
    request.nextUrl.pathname.endsWith(".svg") ||
    request.nextUrl.pathname.endsWith(".ico") ||
    request.nextUrl.pathname.endsWith(".txt") ||
    request.nextUrl.pathname.endsWith(".json")
  ) {
    return NextResponse.next();
  }

  // Check for access_token cookie
  const accessToken = request.cookies.get("access_token");

  if (!accessToken) {
    // Not authenticated: redirect to login
    const loginUrl = new URL("/login", request.url);
    // Optionally add returnUrl to redirect back after login
    loginUrl.searchParams.set("returnUrl", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated: allow
  return NextResponse.next();
}

/**
 * Match all paths except static assets and public API routes.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico
     * - public folder
     * - api/auth (public auth endpoints)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|svg|ico|txt|json)$|/api/auth).*)",
  ],
};
