/**
 * API Configuration utility
 * Handles backend URL configuration for different environments
 */

export function getBackendUrl(): string {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') {
    // Server-side rendering - use environment variable or localhost
    return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  }

  // Client-side - determine URL based on current domain
  const currentHost = window.location.host;
  const currentProtocol = window.location.protocol;

  // If we're on localhost (development), use localhost:8000
  if (currentHost.includes('localhost') || currentHost.includes('127.0.0.1')) {
    return 'http://localhost:8000';
  }

  // For production domains, try to use the same domain with /api prefix
  // This assumes the backend is served from the same domain
  // If your backend is on a different domain, set NEXT_PUBLIC_BACKEND_URL
  const envBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (envBackendUrl) {
    return envBackendUrl;
  }

  // Fallback: assume backend is on the same domain
  // You can modify this logic based on your deployment setup
  return `${currentProtocol}//${currentHost}`;
}

/**
 * Get the full API URL for a given endpoint
 */
export function getApiUrl(endpoint: string): string {
  const backendUrl = getBackendUrl();
  // Remove leading slash from endpoint if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${backendUrl}${cleanEndpoint}`;
}



