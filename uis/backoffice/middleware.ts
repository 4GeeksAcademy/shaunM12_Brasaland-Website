import { NextRequest, NextResponse } from "next/server";

import { isPublicPath, LOGIN_PATH, REFRESH_COOKIE_NAME } from "@/lib/auth-config";

/**
 * Server-side route protection. Every backoffice route requires a session
 * except the public auth pages. "Session" here is the presence of the HttpOnly
 * refresh cookie — the access token (localStorage) is validated client-side and
 * refreshed on `401`. Missing cookie → redirect to `/login?next=...`.
 *
 * The matcher already excludes API/proxy paths (api, auth, users), Next
 * internals, and static files, so this never interferes with data fetching or
 * the public website (which is a separate app).
 */
export function middleware(request: NextRequest): NextResponse {
  const { pathname, search } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const hasSession = request.cookies.has(REFRESH_COOKIE_NAME);
  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = LOGIN_PATH;
  loginUrl.search = "";
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/((?!api|auth|users|_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
};
