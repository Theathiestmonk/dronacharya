/**
 * Browser Cache Manager for Web Crawler Data
 * This provides fast local storage caching to avoid repeated web crawler calls
 */

interface CachedWebData {
  queryHash: string;
  queryText: string;
  webData: string;
  cachedAt: string;
  expiresAt: string;
}

const CACHE_PREFIX = 'web_crawler_cache_';
const CACHE_DURATION_HOURS = 24; // Cache for 24 hours

/**
 * Generate hash for query string
 */
function generateQueryHash(query: string): string {
  // Simple hash function - can be improved with crypto.subtle for better hashing
  let hash = 0;
  const normalizedQuery = query.toLowerCase().trim();
  for (let i = 0; i < normalizedQuery.length; i++) {
    const char = normalizedQuery.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Check if query should use web crawler (based on keywords)
 */
function isWebCrawlerQuery(query: string): boolean {
  const webKeywords = [
    'latest', 'recent', 'news', 'update', 'current', 'new', 'recently',
    'prakriti school', 'prakrit school', 'progressive education',
    'alternative school', 'igcse', 'a level', 'bridge programme',
    'admission', 'fees', 'curriculum', 'activities', 'facilities',
    'article', 'articles', 'substack', 'philosophy', 'learning approach'
  ];
  
  // Exclude classroom-related queries (they use Classroom data, not web crawler)
  const classroomKeywords = [
    'announcement', 'announce', 'notice', 'update',
    'assignment', 'homework', 'coursework', 'task',
    'student', 'students', 'classmate',
    'teacher', 'teachers', 'faculty',
    'course', 'courses', 'class', 'classes',
    'event', 'events', 'calendar', 'schedule'
  ];
  
  const queryLower = query.toLowerCase();
  
  // If it's a classroom query, don't use web crawler cache
  if (classroomKeywords.some(keyword => queryLower.includes(keyword))) {
    return false;
  }
  
  // Check if it matches web crawler keywords
  return webKeywords.some(keyword => queryLower.includes(keyword));
}

/**
 * Get cached web crawler data from browser localStorage
 */
export function getCachedWebData(query: string): string | null {
  try {
    if (!isWebCrawlerQuery(query)) {
      return null; // Not a web crawler query, skip cache check
    }
    
    const queryHash = generateQueryHash(query);
    const cacheKey = `${CACHE_PREFIX}${queryHash}`;
    const cachedDataStr = localStorage.getItem(cacheKey);
    
    if (!cachedDataStr) {
      console.log('[BrowserCache] No cached web data found for query:', query);
      return null;
    }
    
    const cachedData: CachedWebData = JSON.parse(cachedDataStr);
    const now = new Date();
    const expiresAt = new Date(cachedData.expiresAt);
    
    // Check if cache is expired
    if (now > expiresAt) {
      console.log('[BrowserCache] Cached data expired, removing:', query);
      localStorage.removeItem(cacheKey);
      return null;
    }
    
    console.log('[BrowserCache] ✅ Found cached web data (fast response):', query);
    return cachedData.webData;
    
  } catch (error) {
    console.error('[BrowserCache] Error reading cache:', error);
    return null;
  }
}

/**
 * Store web crawler data in browser localStorage
 */
export function setCachedWebData(query: string, webData: string): void {
  try {
    if (!isWebCrawlerQuery(query)) {
      return; // Not a web crawler query, don't cache
    }
    
    if (!webData || webData.trim().length === 0) {
      return; // Don't cache empty data
    }
    
    const queryHash = generateQueryHash(query);
    const cacheKey = `${CACHE_PREFIX}${queryHash}`;
    const now = new Date();
    const expiresAt = new Date(now.getTime() + CACHE_DURATION_HOURS * 60 * 60 * 1000);
    
    const cachedData: CachedWebData = {
      queryHash,
      queryText: query,
      webData,
      cachedAt: now.toISOString(),
      expiresAt: expiresAt.toISOString()
    };
    
    localStorage.setItem(cacheKey, JSON.stringify(cachedData));
    console.log('[BrowserCache] 💾 Cached web data for future use:', query);
    
  } catch (error) {
    console.error('[BrowserCache] Error storing cache:', error);
    // If storage quota exceeded, try to clean old cache entries
    if (error instanceof DOMException && error.code === 22) {
      cleanExpiredCache();
    }
  }
}

/**
 * Extract web crawler data from chatbot response
 * This checks if the response might contain web crawler data
 */
export function extractWebDataFromResponse(query: string, response: string): string | null {
  // Only extract if this is a web crawler query
  if (!isWebCrawlerQuery(query)) {
    return null;
  }
  
  // If response contains URLs or seems to be web content, extract it
  // This is a heuristic - the backend should ideally return web_data separately
  const urlPattern = /https?:\/\/[^\s\)]+/g;
  const hasUrls = urlPattern.test(response);
  
  // Check for web-related content patterns
  const webContentPatterns = [
    /prakriti\.edu\.in/i,
    /prakriti\.edu/i,
    /source:/i,
    /\[.*\]\(https?:\/\/.*\)/i, // Markdown links
    /web search results/i,
    /information about/i,
    /admission/i,
    /curriculum/i,
    /igcse/i,
    /a level/i,
    /bridge programme/i,
  ];
  
  const hasWebContent = webContentPatterns.some(pattern => pattern.test(response));
  
  // Also check if response is substantial (more than 100 chars) and contains web keywords
  const webKeywords = ['prakriti', 'school', 'admission', 'fee', 'curriculum', 'programme', 'education'];
  const queryLower = query.toLowerCase();
  const responseLower = response.toLowerCase();
  const hasWebKeywords = webKeywords.some(keyword => 
    queryLower.includes(keyword) && responseLower.includes(keyword)
  );
  
  if (hasUrls || hasWebContent || (hasWebKeywords && response.length > 100)) {
    return response; // Cache the response as it likely contains web crawler data
  }
  
  return null;
}

/**
 * Clean expired cache entries
 */
function cleanExpiredCache(): void {
  try {
    const now = new Date();
    let cleanedCount = 0;
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(CACHE_PREFIX)) {
        try {
          const cachedDataStr = localStorage.getItem(key);
          if (cachedDataStr) {
            const cachedData: CachedWebData = JSON.parse(cachedDataStr);
            const expiresAt = new Date(cachedData.expiresAt);
            if (now > expiresAt) {
              localStorage.removeItem(key);
              cleanedCount++;
            }
          }
        } catch {
          // Invalid cache entry, remove it
          localStorage.removeItem(key);
          cleanedCount++;
        }
      }
    }
    
    if (cleanedCount > 0) {
      console.log(`[BrowserCache] 🧹 Cleaned ${cleanedCount} expired cache entries`);
    }
  } catch (error) {
    console.error('[BrowserCache] Error cleaning cache:', error);
  }
}

/**
 * Clear all web crawler cache
 */
export function clearWebCrawlerCache(): void {
  try {
    let clearedCount = 0;
    
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key && key.startsWith(CACHE_PREFIX)) {
        localStorage.removeItem(key);
        clearedCount++;
      }
    }
    
    console.log(`[BrowserCache] 🗑️ Cleared ${clearedCount} cache entries`);
  } catch (error) {
    console.error('[BrowserCache] Error clearing cache:', error);
  }
}

// Clean expired cache on module load
if (typeof window !== 'undefined') {
  cleanExpiredCache();
}

