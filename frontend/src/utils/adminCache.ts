/**
 * Admin Dashboard Cache Utility
 * Manages localStorage caching for admin dashboard data
 */

const CACHE_PREFIX = 'admin_cache_';
const DEFAULT_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

export type CacheKey = 
  | 'admin_classroom_data'
  | 'admin_calendar_data'
  | 'admin_website_pages'
  | 'admin_integration_status'
  | 'admin_scheduler_status'
  | 'admin_dwd_status'
  | 'admin_users_by_grade_role';

interface CachedData<T> {
  data: T;
  timestamp: number;
  adminEmail?: string;
}

/**
 * Get the full cache key with prefix and admin email
 */
function getCacheKey(key: CacheKey, adminEmail?: string): string {
  const emailSuffix = adminEmail ? `_${adminEmail.replace(/[^a-zA-Z0-9]/g, '_')}` : '';
  return `${CACHE_PREFIX}${key}${emailSuffix}`;
}

/**
 * Get cached data if it exists and is still valid
 */
export function getCachedData<T>(key: CacheKey, adminEmail?: string, maxAge: number = DEFAULT_CACHE_DURATION): T | null {
  try {
    const cacheKey = getCacheKey(key, adminEmail);
    const cached = localStorage.getItem(cacheKey);
    
    if (!cached) {
      return null;
    }
    
    const parsed: CachedData<T> = JSON.parse(cached);
    const now = Date.now();
    const age = now - parsed.timestamp;
    
    // Check if cache is still valid
    if (age > maxAge) {
      // Cache expired, remove it
      localStorage.removeItem(cacheKey);
      return null;
    }
    
    // Verify admin email matches (if provided)
    if (adminEmail && parsed.adminEmail && parsed.adminEmail !== adminEmail) {
      // Different admin, don't use this cache
      return null;
    }
    
    return parsed.data;
  } catch (error) {
    console.error(`[Cache] Error reading cache for ${key}:`, error);
    return null;
  }
}

/**
 * Store data in cache with timestamp
 */
export function setCachedData<T>(key: CacheKey, data: T, adminEmail?: string): void {
  try {
    const cacheKey = getCacheKey(key, adminEmail);
    const cached: CachedData<T> = {
      data,
      timestamp: Date.now(),
      adminEmail
    };
    
    localStorage.setItem(cacheKey, JSON.stringify(cached));
  } catch (error) {
    console.error(`[Cache] Error writing cache for ${key}:`, error);
    // If storage is full, try to clear old caches
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      clearAllCache();
      // Retry once
      try {
        const cacheKey = getCacheKey(key, adminEmail);
        const cached: CachedData<T> = {
          data,
          timestamp: Date.now(),
          adminEmail
        };
        localStorage.setItem(cacheKey, JSON.stringify(cached));
      } catch (retryError) {
        console.error(`[Cache] Failed to write cache after clearing:`, retryError);
      }
    }
  }
}

/**
 * Check if cache exists and is still valid
 */
export function isCacheValid(key: CacheKey, adminEmail?: string, maxAge: number = DEFAULT_CACHE_DURATION): boolean {
  try {
    const cacheKey = getCacheKey(key, adminEmail);
    const cached = localStorage.getItem(cacheKey);
    
    if (!cached) {
      return false;
    }
    
    const parsed: CachedData<unknown> = JSON.parse(cached);
    const now = Date.now();
    const age = now - parsed.timestamp;
    
    // Check if cache is still valid
    if (age > maxAge) {
      return false;
    }
    
    // Verify admin email matches (if provided)
    if (adminEmail && parsed.adminEmail && parsed.adminEmail !== adminEmail) {
      return false;
    }
    
    return true;
  } catch (error) {
    console.error(`[Cache] Error checking cache validity for ${key}:`, error);
    return false;
  }
}

/**
 * Clear specific cache
 */
export function clearCache(key: CacheKey, adminEmail?: string): void {
  try {
    const cacheKey = getCacheKey(key, adminEmail);
    localStorage.removeItem(cacheKey);
  } catch (error) {
    console.error(`[Cache] Error clearing cache for ${key}:`, error);
  }
}

/**
 * Clear all admin cache
 */
export function clearAllCache(adminEmail?: string): void {
  try {
    if (adminEmail) {
      // Clear only caches for this admin
      const keys: CacheKey[] = [
        'admin_classroom_data',
        'admin_calendar_data',
        'admin_website_pages',
        'admin_integration_status',
        'admin_scheduler_status',
        'admin_dwd_status',
        'admin_users_by_grade_role'
      ];
      
      keys.forEach(key => clearCache(key, adminEmail));
    } else {
      // Clear all admin caches
      const keysToRemove: string[] = [];
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(CACHE_PREFIX)) {
          keysToRemove.push(key);
        }
      }
      
      keysToRemove.forEach(key => localStorage.removeItem(key));
    }
  } catch (error) {
    console.error('[Cache] Error clearing all cache:', error);
  }
}

/**
 * Get cache age in milliseconds
 */
export function getCacheAge(key: CacheKey, adminEmail?: string): number | null {
  try {
    const cacheKey = getCacheKey(key, adminEmail);
    const cached = localStorage.getItem(cacheKey);
    
    if (!cached) {
      return null;
    }
    
    const parsed: CachedData<unknown> = JSON.parse(cached);
    return Date.now() - parsed.timestamp;
  } catch (error) {
    console.error(`[Cache] Error getting cache age for ${key}:`, error);
    return null;
  }
}


