/**
 * Astro Middleware for Authentication & Authorization
 *
 * Protects all routes except:
 * - Public routes: /login, /signup, /
 * - API routes: /api/*
 * - Static assets
 *
 * Redirects unauthenticated users to /login
 */

import { defineMiddleware } from 'astro:middleware';
import { getToken } from './lib/auth';

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/signup', '/', '/index'];

export const onRequest = defineMiddleware((context, next) => {
  const { pathname } = context.url;

  // Skip middleware for API routes, static files, and public routes
  if (
    pathname.startsWith('/api/') ||
    pathname.startsWith('/_') ||
    pathname.includes('.') ||
    PUBLIC_ROUTES.includes(pathname)
  ) {
    return next();
  }

  // Check if user is authenticated
  const token = getToken();

  if (!token) {
    // Redirect unauthenticated users to login
    return context.redirect('/login');
  }

  // Continue to requested page
  return next();
});
