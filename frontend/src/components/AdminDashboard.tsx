"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import { 
  getCachedData, 
  setCachedData, 
  clearCache
} from '@/utils/adminCache';

interface ClassroomCourse {
  id: string;
  name: string;
  description: string;
  room: string;
  section: string;
  state: string;
  teacher_email: string;
  last_synced: string;
}

interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  start: string;
  end: string;
  location: string;
  status: string;
  last_synced: string;
  calendar_id?: string;
}

interface WebsitePage {
  url: string;
  title: string;
  content_type: string;
  last_crawled: string | null;
}


const ESSENTIAL_PAGES = [
  "https://prakriti.edu.in/",
  "https://prakriti.edu.in/team/",
  "https://prakriti.edu.in/prakriti-way-of-learning/",
  "https://prakriti.edu.in/roots-of-all-beings/",
  "https://prakriti.edu.in/our-programmes/",
  "https://prakriti.edu.in/admissions/",
  "https://prakriti.edu.in/school-fees/",
  "https://prakriti.edu.in/contact/",
  "https://prakriti.edu.in/calendar/",
  "https://prakriti.edu.in/blog-and-news/",
  "https://prakriti.edu.in/what-our-parents-say-about-us/",
];

const PAGE_CONTENT_TYPES: Record<string, string> = {
  "https://prakriti.edu.in/": "general",
  "https://prakriti.edu.in/team/": "team",
  "https://prakriti.edu.in/prakriti-way-of-learning/": "article",
  "https://prakriti.edu.in/roots-of-all-beings/": "article",
  "https://prakriti.edu.in/our-programmes/": "academic",
  "https://prakriti.edu.in/admissions/": "admission",
  "https://prakriti.edu.in/school-fees/": "admission",
  "https://prakriti.edu.in/contact/": "contact",
  "https://prakriti.edu.in/calendar/": "calendar",
  "https://prakriti.edu.in/blog-and-news/": "news",
  "https://prakriti.edu.in/what-our-parents-say-about-us/": "testimonial",
};

type TabType = 'classroom' | 'calendar' | 'website' | 'users';

interface UserData {
  email: string;
  name: string;
  lastSync: string | null;
  status: 'synced' | 'pending' | 'error';
}

interface GradeData {
  student: UserData[];
  teacher: UserData[];
  parent: UserData[];
}

interface UsersByGrade {
  [grade: string]: GradeData;
}

const AdminDashboard: React.FC = () => {
  const { profile } = useAuth();
  const [classroomData, setClassroomData] = useState<ClassroomCourse[]>([]);
  const [calendarData, setCalendarData] = useState<CalendarEvent[]>([]);
  const [websitePages, setWebsitePages] = useState<WebsitePage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [syncingItems, setSyncingItems] = useState<Set<string>>(new Set());
  const [schedulerStatus, setSchedulerStatus] = useState<{ status: string; next_sync: string | null } | null>(null);
  const [dwdStatus, setDwdStatus] = useState<{
    available: boolean;
    workspace_domain?: string;
    service_account_path?: string;
    error?: string;
  } | null>(null);
  const [usersByGrade, setUsersByGrade] = useState<UsersByGrade>({});
  const [gradeFilter, setGradeFilter] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [serviceFilter, setServiceFilter] = useState<string>('');
  const [syncingGrade, setSyncingGrade] = useState<{ grade: string; service: string } | null>(null);

  const fetchClassroomData = useCallback(async (forceRefresh: boolean = false) => {
    try {
      const adminEmail = profile?.email;
      
      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData<ClassroomCourse[]>('admin_classroom_data', adminEmail);
        if (cached) {
          console.log('🔍 [Cache] Using cached classroom data');
          setClassroomData(cached);
          return; // Don't fetch in background, only fetch when Refresh Status is clicked
        }
      }
      
      const emailParam = adminEmail ? `?email=${encodeURIComponent(adminEmail)}` : '';
      const timestamp = new Date().getTime();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/admin/data/classroom${emailParam}&t=${timestamp}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache'
        }
      });
      if (response.ok) {
        const data = await response.json();
        const courses = data.courses || [];
        console.log(`🔍 [fetchClassroomData] Received ${courses.length} courses`);
        setClassroomData(courses);
        // Update cache
        setCachedData('admin_classroom_data', courses, adminEmail);
      }
    } catch (error) {
      console.error('Error fetching classroom data:', error);
    }
  }, [profile?.email]);

  const fetchCalendarData = useCallback(async (forceRefresh: boolean = false) => {
    try {
      const adminEmail = profile?.email;
      
      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData<CalendarEvent[]>('admin_calendar_data', adminEmail);
        if (cached) {
          console.log('🔍 [Cache] Using cached calendar data');
          setCalendarData(cached);
          return; // Don't fetch in background, only fetch when Refresh Status is clicked
        }
      }
      
      const emailParam = adminEmail ? `?email=${encodeURIComponent(adminEmail)}` : '';
      const timestamp = new Date().getTime();
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/admin/data/calendar${emailParam}&t=${timestamp}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache'
        }
      });
      if (response.ok) {
        const data = await response.json();
        const events = data.events || [];
        console.log(`🔍 [fetchCalendarData] Received ${events.length} events`);
        setCalendarData(events);
        // Update cache
        setCachedData('admin_calendar_data', events, adminEmail);
      }
    } catch (err) {
      console.error('Error fetching calendar data:', err);
    }
  }, [profile?.email]);

  const fetchWebsitePages = useCallback(async (forceRefresh: boolean = false) => {
    try {
      const adminEmail = profile?.email;
      
      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData<WebsitePage[]>('admin_website_pages', adminEmail);
        if (cached) {
          console.log('🔍 [Cache] Using cached website pages');
          setWebsitePages(cached);
          return; // Don't fetch in background, only fetch when Refresh Status is clicked
        }
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const pages: WebsitePage[] = [];
      
      // Fetch status for each essential page
      for (const url of ESSENTIAL_PAGES) {
        try {
          const response = await fetch(`${backendUrl}/api/admin/data/website?url=${encodeURIComponent(url)}`, {
            cache: 'no-store'
          });
          if (response.ok) {
            const data = await response.json();
            pages.push({
              url,
              title: data.title || url.split('/').filter(Boolean).pop() || url,
              content_type: PAGE_CONTENT_TYPES[url] || 'general',
              last_crawled: data.crawled_at || null
            });
          } else {
            // Page not found in database
            pages.push({
              url,
              title: url.split('/').filter(Boolean).pop() || url,
              content_type: PAGE_CONTENT_TYPES[url] || 'general',
              last_crawled: null
            });
          }
        } catch {
          pages.push({
            url,
            title: url.split('/').filter(Boolean).pop() || url,
            content_type: PAGE_CONTENT_TYPES[url] || 'general',
            last_crawled: null
          });
        }
      }
      
      setWebsitePages(pages);
      // Update cache
      setCachedData('admin_website_pages', pages, adminEmail);
    } catch (err) {
      console.error('Error fetching website pages:', err);
    }
  }, [profile?.email]);

  const fetchSchedulerStatus = useCallback(async (forceRefresh: boolean = false) => {
    try {
      const adminEmail = profile?.email;
      
      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData<{ status: string; next_sync: string | null }>('admin_scheduler_status', adminEmail);
        if (cached) {
          console.log('🔍 [Cache] Using cached scheduler status');
          setSchedulerStatus(cached);
          return; // Don't fetch in background, only fetch when Refresh Status is clicked
        }
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/health`);
      if (response.ok) {
        const data = await response.json();
        const statusData = {
          status: data.scheduler || 'unknown',
          next_sync: data.next_sync || null
        };
        setSchedulerStatus(statusData);
        // Update cache
        setCachedData('admin_scheduler_status', statusData, adminEmail);
      }
    } catch (err) {
      console.error('Error fetching scheduler status:', err);
    }
  }, [profile?.email]);

  const fetchDwdStatus = useCallback(async (forceRefresh: boolean = false) => {
    try {
      const adminEmail = profile?.email;
      
      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData<{
          available: boolean;
          workspace_domain?: string;
          service_account_path?: string;
          error?: string;
        }>('admin_dwd_status', adminEmail);
        if (cached) {
          console.log('🔍 [Cache] Using cached DWD status');
          setDwdStatus(cached);
          return; // Don't fetch in background, only fetch when Refresh Status is clicked
        }
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/admin/dwd/status`);
      if (response.ok) {
        const data = await response.json();
        setDwdStatus(data);
        // Update cache
        setCachedData('admin_dwd_status', data, adminEmail);
      } else {
        const errorData = await response.json();
        const errorStatus = {
          available: false,
          error: errorData.error || 'Failed to check DWD status'
        };
        setDwdStatus(errorStatus);
        // Cache error status too
        setCachedData('admin_dwd_status', errorStatus, adminEmail);
      }
    } catch (err) {
      console.error('Error fetching DWD status:', err);
      const errorStatus = {
        available: false,
        error: 'Failed to check DWD status'
      };
      setDwdStatus(errorStatus);
      // Cache error status too
      const adminEmail = profile?.email;
      setCachedData('admin_dwd_status', errorStatus, adminEmail);
    }
  }, [profile?.email]);

  const fetchUsersByGradeRole = useCallback(async (forceRefresh: boolean = false) => {
    try {
      const adminEmail = profile?.email;
      
      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData<UsersByGrade>('admin_users_by_grade_role', adminEmail);
        if (cached) {
          console.log('🔍 [Cache] Using cached users by grade/role data');
          setUsersByGrade(cached);
          return; // Don't fetch in background, only fetch when Refresh Status is clicked
        }
      }
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const emailParam = profile?.email ? `?email=${encodeURIComponent(profile.email)}` : '';
      const response = await fetch(`${backendUrl}/api/admin/users/by-grade-role${emailParam}`);
      
      if (response.ok) {
        const data = await response.json();
        const usersByGradeData = data || {};
        setUsersByGrade(usersByGradeData);
        // Update cache
        setCachedData('admin_users_by_grade_role', usersByGradeData, adminEmail);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('Error fetching users by grade/role:', errorData);
        setError(`Failed to fetch users: ${errorData.detail || errorData.error || 'Unknown error'}`);
        setUsersByGrade({});
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Error fetching users by grade/role:', err);
      setError(`Failed to fetch users: ${errorMessage}`);
      setUsersByGrade({});
    }
  }, [profile?.email]);

  const syncGrade = async (grade: string) => {
    if (!confirm(`Sync Classroom and Calendar for all users in ${grade}? This may take a few minutes.`)) {
      return;
    }

    setSyncingGrade({ grade, service: 'all' });
    setError(null);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      
      // Sync both services sequentially
      const results = {
        classroom: { synced: 0, failed: 0 },
        calendar: { synced: 0, failed: 0 }
      };

      // Sync Classroom
      try {
        const classroomResponse = await fetch(`${backendUrl}/api/admin/sync/grade/${encodeURIComponent(grade)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            service: 'classroom',
            email: profile?.email
          })
        });
        const classroomData = await classroomResponse.json();
        if (classroomResponse.ok) {
          results.classroom = { synced: classroomData.synced || 0, failed: classroomData.failed || 0 };
        }
      } catch (err) {
        console.error('Error syncing classroom:', err);
      }

      // Sync Calendar
      try {
        const calendarResponse = await fetch(`${backendUrl}/api/admin/sync/grade/${encodeURIComponent(grade)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            service: 'calendar',
            email: profile?.email
          })
        });
        const calendarData = await calendarResponse.json();
        if (calendarResponse.ok) {
          results.calendar = { synced: calendarData.synced || 0, failed: calendarData.failed || 0 };
        }
      } catch (err) {
        console.error('Error syncing calendar:', err);
      }

      const totalSynced = results.classroom.synced + results.calendar.synced;
      const totalFailed = results.classroom.failed + results.calendar.failed;
      
      alert(`Sync completed for ${grade}!\nClassroom: ${results.classroom.synced} synced, ${results.classroom.failed} failed\nCalendar: ${results.calendar.synced} synced, ${results.calendar.failed} failed\nTotal: ${totalSynced} synced, ${totalFailed} failed`);
      
      // Force refresh to get updated data from Supabase
      await fetchUsersByGradeRole(true);
      await fetchClassroomData(true);
      await fetchCalendarData(true);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to sync ${grade}: ${errorMessage}`);
    } finally {
      setSyncingGrade(null);
    }
  };

  const syncUser = async (email: string) => {
    if (!confirm(`Sync Classroom and Calendar for ${email}?`)) {
      return;
    }

    const itemKey = `user-${email}-all`;
    setSyncingItems(prev => new Set(prev).add(itemKey));
    setError(null);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      
      // Sync both services sequentially
      let successCount = 0;
      const errorMessages: string[] = [];

      // Sync Classroom
      try {
        const classroomResponse = await fetch(`${backendUrl}/api/admin/sync-dwd/classroom`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_email: email
          })
        });
        const classroomData = await classroomResponse.json();
        if (classroomResponse.ok) {
          successCount++;
        } else {
          errorMessages.push(`Classroom: ${classroomData.detail || classroomData.error || 'Failed'}`);
        }
      } catch {
        errorMessages.push('Classroom: Network error');
      }

      // Sync Calendar
      try {
        const calendarResponse = await fetch(`${backendUrl}/api/admin/sync-dwd/calendar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_email: email
          })
        });
        const calendarData = await calendarResponse.json();
        if (calendarResponse.ok) {
          successCount++;
        } else {
          errorMessages.push(`Calendar: ${calendarData.detail || calendarData.error || 'Failed'}`);
        }
      } catch {
        errorMessages.push('Calendar: Network error');
      }

      if (successCount === 2) {
        alert(`Sync completed for ${email}! Both Classroom and Calendar synced successfully.`);
      } else if (successCount === 1) {
        alert(`Partial sync for ${email}:\n${errorMessages.join('\n')}`);
      } else {
        setError(`Failed to sync ${email}: ${errorMessages.join(', ')}`);
      }

      // Force refresh to get updated data from Supabase
      await fetchUsersByGradeRole(true);
      await fetchClassroomData(true);
      await fetchCalendarData(true);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to sync ${email}: ${errorMessage}`);
    } finally {
      setSyncingItems(prev => {
        const next = new Set(prev);
        next.delete(itemKey);
        return next;
      });
    }
  };

  const getSyncStatus = (lastSynced: string | null | undefined): 'fresh' | 'stale' | 'outdated' => {
    if (!lastSynced) return 'outdated';
    const lastSyncedTime = new Date(lastSynced).getTime();
    const now = Date.now();
    const hoursSinceSync = (now - lastSyncedTime) / (1000 * 60 * 60);
    
    if (hoursSinceSync < 6) return 'fresh';
    if (hoursSinceSync < 24) return 'stale';
    return 'outdated';
  };

  const syncIndividualCourse = async (courseId: string) => {
    const itemKey = `course-${courseId}`;
    setSyncingItems(prev => new Set(prev).add(itemKey));
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/sync/classroom/${courseId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ adminEmail: profile?.email })
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(data.message || 'Course synced successfully');
        // Clear cache and refresh
        clearCache('admin_classroom_data', profile?.email);
        await fetchClassroomData(true);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to sync course');
      }
    } catch {
      setError('Failed to sync course');
    } finally {
      setSyncingItems(prev => {
        const next = new Set(prev);
        next.delete(itemKey);
        return next;
      });
    }
  };

  // Removed unused syncIndividualCalendar function - using DWD sync instead

  const syncIndividualEvent = async (eventId: string, calendarId: string) => {
    const itemKey = `event-${eventId}`;
    setSyncingItems(prev => new Set(prev).add(itemKey));
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/sync/event/${eventId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ adminEmail: profile?.email, calendarId })
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(data.message || 'Event synced successfully');
        await fetchCalendarData();
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to sync event');
      }
    } catch {
      setError('Failed to sync event');
    } finally {
      setSyncingItems(prev => {
        const next = new Set(prev);
        next.delete(itemKey);
        return next;
      });
    }
  };

  const syncIndividualPage = async (url: string) => {
    const itemKey = `page-${url}`;
    setSyncingItems(prev => new Set(prev).add(itemKey));
    setError(null);
    
    try {
      const encodedUrl = encodeURIComponent(url);
      const response = await fetch(`/api/admin/sync/website/${encodedUrl}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ adminEmail: profile?.email })
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(data.message || 'Page synced successfully');
        await fetchWebsitePages();
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to sync page');
      }
    } catch {
      setError('Failed to sync page');
    } finally {
      setSyncingItems(prev => {
        const next = new Set(prev);
        next.delete(itemKey);
        return next;
      });
    }
  };


  const syncData = async (service: 'classroom' | 'calendar' | 'website') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/sync/${service}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          adminEmail: profile?.email
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(data.message || `Successfully synced ${service} data`);
        // Wait a moment for backend to finish processing
        await new Promise(resolve => setTimeout(resolve, 500));
        // Clear cache and refresh data
        if (service === 'classroom') {
          clearCache('admin_classroom_data', profile?.email);
          await fetchClassroomData(true);
        } else if (service === 'calendar') {
          clearCache('admin_calendar_data', profile?.email);
          await fetchCalendarData(true);
        } else if (service === 'website') {
          clearCache('admin_website_pages', profile?.email);
          await fetchWebsitePages(true);
        }
      } else {
        const errorData = await response.json();
        setError(errorData.error || errorData.detail || 'Sync failed');
      }
    } catch {
      setError('Failed to sync data');
    } finally {
      setLoading(false);
    }
  };



  useEffect(() => {
    console.log('🔍 [MOUNT] Component mounted');
    fetchClassroomData();
    fetchCalendarData();
    fetchWebsitePages();
    fetchSchedulerStatus();
    fetchDwdStatus();
    fetchUsersByGradeRole();
  }, [fetchClassroomData, fetchCalendarData, fetchWebsitePages, fetchSchedulerStatus, fetchDwdStatus, fetchUsersByGradeRole]);

  // Calculate sync status for display
  const getStatusBadge = (status: 'fresh' | 'stale' | 'outdated') => {
    const styles = {
      fresh: 'bg-green-50 text-green-800 border-2 border-green-300',
      stale: 'bg-yellow-50 text-yellow-800 border-2 border-yellow-300',
      outdated: 'bg-red-50 text-red-800 border-2 border-red-300 animate-pulse'
    };
    const labels = {
      fresh: '✓ Fresh',
      stale: '⚠ Stale',
      outdated: '✗ Outdated'
    };
    return (
      <span className={`px-2 sm:px-3 py-1 sm:py-1.5 rounded-full text-xs font-semibold transition-all duration-300 ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  // Get most recent sync time for sections
  const getMostRecentSync = (data: Array<{ last_synced?: string | null }>) => {
    const timestamps = data
      .map(item => item?.last_synced)
      .filter(Boolean)
      .sort((a, b) => new Date(b!).getTime() - new Date(a!).getTime());
    return timestamps[0] || null;
  };

  const formatTimeAgo = (dateString: string | null) => {
    if (!dateString) return 'Never synced';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const days = Math.floor(hours / 24);

      if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
      if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
      return 'Just now';
    } catch {
      return 'Unknown';
    }
  };

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="min-h-screen chat-grid-bg py-4 sm:py-6 md:py-8">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-4 sm:mb-6 md:mb-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4">
            <div className="flex items-center gap-3 sm:gap-4 flex-nowrap flex-1 min-w-0">
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold whitespace-nowrap" style={{ color: 'var(--brand-primary)' }}>Admin Dashboard</h1>
              {/* Auto-sync Status Icon */}
              {schedulerStatus && (
                <div className="relative inline-block flex-shrink-0">
                  <button
                    className="relative flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-full transition-all duration-300 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-offset-2"
                    style={{
                      backgroundColor: 'var(--brand-primary-50)',
                      color: 'var(--brand-primary-700)'
                    }}
                    onMouseEnter={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.remove('hidden');
                    }}
                    onMouseLeave={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.add('hidden');
                    }}
                    onFocus={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.remove('hidden');
                    }}
                    onBlur={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.add('hidden');
                    }}
                    title="Auto-sync Status"
                  >
                    <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                  
                  {/* Tooltip */}
                  <div className="hidden absolute left-0 top-full mt-2 w-64 sm:w-80 bg-white rounded-lg shadow-xl border-2 z-50 p-4"
                    style={{
                      borderColor: 'var(--brand-primary-200)'
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-3 h-3 rounded-full flex-shrink-0 mt-1 bg-blue-500"></div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-gray-900 mb-2">
                          Auto-sync Status
                        </h3>
                        <p className="text-xs font-semibold mb-1" style={{ color: 'var(--brand-primary-700)' }}>
                          Auto-sync: Every 12 hours
                        </p>
                        {schedulerStatus.next_sync && (
                          <p className="text-xs mt-1" style={{ color: 'var(--brand-primary-600)' }}>
                            Next: {formatDateTime(schedulerStatus.next_sync)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {/* DWD Status Icon */}
              {dwdStatus && (
                <div className="relative inline-block flex-shrink-0">
                  <button
                    onClick={() => fetchDwdStatus(true)}
                    className="relative flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-full transition-all duration-300 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-offset-2"
                    style={{
                      backgroundColor: dwdStatus.available ? 'var(--brand-secondary-50)' : '#fee2e2',
                      color: dwdStatus.available ? 'var(--brand-secondary-700)' : '#dc2626'
                    }}
                    onMouseEnter={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.remove('hidden');
                    }}
                    onMouseLeave={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.add('hidden');
                    }}
                    onFocus={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.remove('hidden');
                    }}
                    onBlur={(e) => {
                      const tooltip = e.currentTarget.nextElementSibling as HTMLElement;
                      if (tooltip) tooltip.classList.add('hidden');
                    }}
                    title="DWD Status"
                  >
                    {dwdStatus.available ? (
                      <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                  </button>
                  
                  {/* Tooltip */}
                  <div className="hidden absolute left-0 top-full mt-2 w-64 sm:w-80 bg-white rounded-lg shadow-xl border-2 z-50 p-4"
                    style={{
                      borderColor: dwdStatus.available ? 'var(--brand-secondary-300)' : '#fca5a5'
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-3 h-3 rounded-full flex-shrink-0 mt-1 ${
                        dwdStatus.available 
                          ? 'bg-green-500 shadow-lg shadow-green-500/50 animate-pulse' 
                          : 'bg-red-500 shadow-lg shadow-red-500/50'
                      }`}></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-sm font-semibold text-gray-900">
                            {dwdStatus.available ? 'DWD Configured' : 'DWD Not Available'}
                          </h3>
                          <button
                            onClick={() => fetchDwdStatus(true)}
                            className="text-xs text-gray-500 hover:text-gray-700 underline transition-colors"
                          >
                            Refresh
                          </button>
                        </div>
                        <p className="text-xs text-gray-600 mb-2">
                          {dwdStatus.available ? 'Domain-Wide Delegation is configured and ready to use.' : 'Domain-Wide Delegation is not properly configured.'}
                        </p>
                        {dwdStatus.workspace_domain && (
                          <p className="text-xs text-gray-700 mb-1">
                            <span className="font-medium">Workspace Domain:</span> {dwdStatus.workspace_domain}
                          </p>
                        )}
                        {dwdStatus.error && (
                          <p className="text-xs text-red-700 mt-2 break-words">
                            <span className="font-medium">Error:</span> {dwdStatus.error}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="flex items-center space-x-2 sm:space-x-3 gap-2 flex-nowrap flex-shrink-0">
              <button
                onClick={() => {
                  // Force refresh all data from Supabase
                  console.log('🔄 [Refresh] Fetching fresh data from Supabase...');
                  fetchClassroomData(true);
                  fetchCalendarData(true);
                  fetchWebsitePages(true);
                  fetchSchedulerStatus(true);
                  fetchDwdStatus(true);
                  fetchUsersByGradeRole(true);
                }}
                className="hidden sm:inline-flex text-white px-4 sm:px-5 py-2 sm:py-2.5 rounded-lg font-medium text-xs sm:text-sm transition-all duration-300 transform hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:transform-none"
                style={{ backgroundColor: 'var(--brand-primary)' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-700)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
              >
                Refresh Status
              </button>
            </div>
          </div>
          <p className="mt-2 sm:mt-3 text-sm sm:text-base text-gray-600 font-medium">Manage Google Classroom, Calendar, and Website data</p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 sm:mb-6 bg-red-50 border-2 border-red-300 rounded-lg sm:rounded-xl p-4 sm:p-5 shadow-md transition-all duration-300">
            <div className="flex items-start gap-3">
              <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-white text-xs font-bold">!</span>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-red-800">Error</h3>
                <div className="mt-1 text-xs sm:text-sm text-red-700 break-words">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs Navigation */}
        <div className="mb-4 sm:mb-6 border-b-2 border-gray-200 overflow-x-auto">
          <nav className="flex space-x-4 sm:space-x-6 md:space-x-8 min-w-max sm:min-w-0">
            <button
              onClick={() => setActiveTab('users')}
              className={`relative border-b-2 py-3 sm:py-4 px-1 text-xs sm:text-sm font-medium transition-all duration-300 whitespace-nowrap ${
                activeTab === 'users'
                  ? 'border-transparent'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              style={activeTab === 'users' ? { 
                color: 'var(--brand-primary)',
                borderBottomColor: 'var(--brand-primary)'
              } : {}}
            >
              Users by Grade & Role
            </button>
            <button
              onClick={() => setActiveTab('classroom')}
              className={`relative border-b-2 py-3 sm:py-4 px-1 text-xs sm:text-sm font-medium transition-all duration-300 whitespace-nowrap ${
                activeTab === 'classroom'
                  ? 'border-transparent'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              style={activeTab === 'classroom' ? { 
                color: 'var(--brand-primary)',
                borderBottomColor: 'var(--brand-primary)'
              } : {}}
            >
              Google Classroom
            </button>
            <button
              onClick={() => setActiveTab('calendar')}
              className={`relative border-b-2 py-3 sm:py-4 px-1 text-xs sm:text-sm font-medium transition-all duration-300 whitespace-nowrap ${
                activeTab === 'calendar'
                  ? 'border-transparent'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              style={activeTab === 'calendar' ? { 
                color: 'var(--brand-primary)',
                borderBottomColor: 'var(--brand-primary)'
              } : {}}
            >
              Google Calendar
            </button>
            <button
              onClick={() => setActiveTab('website')}
              className={`relative border-b-2 py-3 sm:py-4 px-1 text-xs sm:text-sm font-medium transition-all duration-300 whitespace-nowrap ${
                activeTab === 'website'
                  ? 'border-transparent'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              style={activeTab === 'website' ? { 
                color: 'var(--brand-primary)',
                borderBottomColor: 'var(--brand-primary)'
              } : {}}
            >
              Website Pages
            </button>
          </nav>
        </div>

        {/* Users by Grade & Role Tab */}
        {activeTab === 'users' && (
          <div className="mb-8">
            {/* Stats Bar */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 md:gap-4 mb-4 sm:mb-6">
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1 border border-gray-200">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Total Users</div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900 transition-all duration-300">
                  {Object.values(usersByGrade).reduce((sum, grade) => 
                    sum + (grade.student?.length || 0) + (grade.teacher?.length || 0) + (grade.parent?.length || 0), 0
                  )}
                </div>
              </div>
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1 border border-green-200" style={{ backgroundColor: 'var(--brand-secondary-50)' }}>
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Synced Today</div>
                <div className="text-2xl sm:text-3xl font-bold transition-all duration-300" style={{ color: 'var(--brand-secondary-700)' }}>
                  {Object.values(usersByGrade).reduce((sum, grade) => {
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    return sum + [...(grade.student || []), ...(grade.teacher || []), ...(grade.parent || [])].filter(u => {
                      if (!u.lastSync) return false;
                      const syncDate = new Date(u.lastSync);
                      return syncDate >= today && u.status === 'synced';
                    }).length;
                  }, 0)}
                </div>
              </div>
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1 border border-yellow-200" style={{ backgroundColor: '#fef3c7' }}>
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Pending Sync</div>
                <div className="text-2xl sm:text-3xl font-bold text-yellow-600 transition-all duration-300">
                  {Object.values(usersByGrade).reduce((sum, grade) => 
                    sum + [...(grade.student || []), ...(grade.teacher || []), ...(grade.parent || [])].filter(u => u.status === 'pending').length, 0
                  )}
                </div>
              </div>
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1 border border-gray-200">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Total Grades</div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900 transition-all duration-300">{Object.keys(usersByGrade).length}</div>
              </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-4 sm:p-5 mb-4 sm:mb-6 flex flex-col sm:flex-row gap-3 sm:gap-4 border border-gray-200">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <label className="text-xs sm:text-sm font-semibold text-gray-700 whitespace-nowrap">Filter by Grade:</label>
                <select
                  value={gradeFilter}
                  onChange={(e) => setGradeFilter(e.target.value)}
                  className="flex-1 px-3 sm:px-4 py-2 border-2 border-gray-300 rounded-lg text-xs sm:text-sm transition-all duration-300 focus:outline-none hover:border-gray-400 min-w-0"
                  style={{ 
                    '--tw-ring-color': 'var(--brand-primary-200)',
                  } as React.CSSProperties}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = 'var(--brand-primary)';
                    e.currentTarget.style.boxShadow = '0 0 0 2px var(--brand-primary-200)';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = '';
                    e.currentTarget.style.boxShadow = '';
                  }}
                >
                  <option value="">All Grades</option>
                  {Object.keys(usersByGrade).sort().map(grade => (
                    <option key={grade} value={grade}>{grade}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <label className="text-xs sm:text-sm font-semibold text-gray-700 whitespace-nowrap">Filter by Role:</label>
                <select
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                  className="flex-1 px-3 sm:px-4 py-2 border-2 border-gray-300 rounded-lg text-xs sm:text-sm transition-all duration-300 focus:outline-none hover:border-gray-400 min-w-0"
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = 'var(--brand-primary)';
                    e.currentTarget.style.boxShadow = '0 0 0 2px var(--brand-primary-200)';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = '';
                    e.currentTarget.style.boxShadow = '';
                  }}
                >
                  <option value="">All Roles</option>
                  <option value="student">Students</option>
                  <option value="teacher">Teachers</option>
                  <option value="parent">Parents</option>
                </select>
              </div>
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <label className="text-xs sm:text-sm font-semibold text-gray-700 whitespace-nowrap">Service:</label>
                <select
                  value={serviceFilter}
                  onChange={(e) => setServiceFilter(e.target.value)}
                  className="flex-1 px-3 sm:px-4 py-2 border-2 border-gray-300 rounded-lg text-xs sm:text-sm transition-all duration-300 focus:outline-none hover:border-gray-400 min-w-0"
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = 'var(--brand-primary)';
                    e.currentTarget.style.boxShadow = '0 0 0 2px var(--brand-primary-200)';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = '';
                    e.currentTarget.style.boxShadow = '';
                  }}
                >
                  <option value="">All Services</option>
                  <option value="classroom">Classroom</option>
                  <option value="calendar">Calendar</option>
                </select>
              </div>
            </div>

            {/* Grade Sections */}
            {Object.keys(usersByGrade)
              .filter(grade => !gradeFilter || grade === gradeFilter)
              .sort()
              .map(grade => {
                const gradeData = usersByGrade[grade];
                const totalUsers = (gradeData.student?.length || 0) + (gradeData.teacher?.length || 0) + (gradeData.parent?.length || 0);
                const isSyncing = syncingGrade?.grade === grade;

                return (
                  <div key={grade} className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md mb-4 sm:mb-6 p-4 sm:p-6 transition-all duration-300 hover:shadow-md sm:hover:shadow-xl border border-gray-200">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-0 mb-4 pb-4 border-b border-gray-200">
                      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                        <h2 className="text-lg sm:text-xl font-semibold text-gray-900">{grade}</h2>
                        <span className="px-2 sm:px-3 py-1 rounded-full text-xs font-semibold border whitespace-nowrap" style={{ 
                          backgroundColor: 'var(--brand-primary-50)',
                          color: 'var(--brand-primary-700)',
                          borderColor: 'var(--brand-primary-200)'
                        }}>
                          {totalUsers} Users
                        </span>
                      </div>
                      <div className="flex gap-2 w-full sm:w-auto">
                        <button
                          onClick={() => syncGrade(grade)}
                          disabled={isSyncing || !dwdStatus?.available}
                          className={`relative flex-1 sm:flex-none px-3 sm:px-4 md:px-5 py-2 sm:py-2.5 text-white rounded-lg font-medium text-xs sm:text-sm flex items-center justify-center gap-2 transition-all duration-300 transform hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:hover:shadow-none ${
                            syncingGrade?.grade === grade ? 'animate-pulse shadow-lg' : ''
                          }`}
                          style={{ 
                            backgroundColor: syncingGrade?.grade === grade 
                              ? 'var(--brand-primary-700)' 
                              : 'var(--brand-primary)'
                          }}
                          onMouseEnter={(e) => {
                            if (!e.currentTarget.disabled) {
                              e.currentTarget.style.backgroundColor = 'var(--brand-primary-700)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!e.currentTarget.disabled) {
                              e.currentTarget.style.backgroundColor = 'var(--brand-primary)';
                            }
                          }}
                        >
                          {syncingGrade?.grade === grade ? (
                            <>
                              <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              <span className="hidden sm:inline">Syncing...</span>
                              <span className="sm:hidden">Sync...</span>
                            </>
                          ) : (
                            <>
                              <span className="text-sm sm:text-base">🔄</span>
                              <span className="hidden sm:inline">Sync All</span>
                              <span className="sm:hidden">Sync</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Role Sections */}
                    {(['student', 'teacher', 'parent'] as const).map(role => {
                      const users = gradeData[role] || [];
                      if (users.length === 0 || (roleFilter && roleFilter !== role)) return null;
                      
                      const roleLabel = role.charAt(0).toUpperCase() + role.slice(1);

                      return (
                        <div key={role} className="mb-4 p-4 sm:p-5 bg-gray-50 rounded-lg sm:rounded-xl border border-gray-200 transition-all duration-300 hover:shadow-md">
                          <div className="flex items-center gap-2 flex-wrap mb-4">
                            <h3 className="text-base sm:text-lg font-semibold text-gray-800">{roleLabel}s</h3>
                            <span className={`px-2 sm:px-3 py-1 rounded-full text-xs font-semibold transition-all duration-300 border whitespace-nowrap ${
                              role === 'student' ? 'bg-blue-100 text-blue-700 border-blue-200' :
                              role === 'teacher' ? 'bg-yellow-100 text-yellow-700 border-yellow-200' :
                              'bg-purple-100 text-purple-700 border-purple-200'
                            }`}>
                              {users.length}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {users.map(user => {
                              const isUserSyncing = syncingItems.has(`user-${user.email}-all`);
                              const lastSyncText = user.lastSync 
                                ? `Last sync: ${formatTimeAgo(user.lastSync)}`
                                : 'Never synced';

                              return (
                                <div key={user.email} className="bg-white border-2 border-gray-200 rounded-lg p-3 sm:p-4 hover:border-gray-300 hover:shadow-md transition-all duration-300 transform hover:-translate-y-0.5 sm:hover:-translate-y-1">
                                  <div className="flex justify-between items-start mb-2 sm:mb-3 gap-2">
                                    <div className="flex-1 min-w-0">
                                      <div className="font-semibold text-xs sm:text-sm text-gray-900 mb-1 truncate">{user.email}</div>
                                      <div className="text-xs text-gray-500 truncate">{user.name}</div>
                                    </div>
                                    <span className={`px-2 sm:px-2.5 py-1 rounded-full text-xs font-semibold transition-all duration-300 flex-shrink-0 ${
                                      user.status === 'synced' ? 'bg-green-100 text-green-700' :
                                      user.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                      'bg-red-100 text-red-700'
                                    }`}>
                                      {user.status === 'synced' ? '✓' : user.status === 'pending' ? '⏳' : '✗'}
                                    </span>
                                  </div>
                                  <div className="text-xs text-gray-400 mb-2 sm:mb-3 truncate">{lastSyncText}</div>
                                  <button
                                    onClick={() => syncUser(user.email)}
                                    disabled={isUserSyncing || !dwdStatus?.available}
                                    className={`w-full px-2 sm:px-3 py-1.5 sm:py-2 text-xs font-medium border-2 rounded-lg transition-all duration-300 transform hover:scale-105 hover:shadow-sm disabled:opacity-50 disabled:transform-none disabled:hover:shadow-none ${
                                      isUserSyncing ? 'animate-pulse text-white' : ''
                                    }`}
                                    style={isUserSyncing ? {
                                      backgroundColor: 'var(--brand-primary)',
                                      borderColor: 'var(--brand-primary)'
                                    } : {
                                      borderColor: 'var(--brand-primary)',
                                      color: 'var(--brand-primary)'
                                    }}
                                    onMouseEnter={(e) => {
                                      if (!e.currentTarget.disabled && !isUserSyncing) {
                                        e.currentTarget.style.backgroundColor = 'var(--brand-primary)';
                                        e.currentTarget.style.color = 'white';
                                      }
                                    }}
                                    onMouseLeave={(e) => {
                                      if (!e.currentTarget.disabled && !isUserSyncing) {
                                        e.currentTarget.style.backgroundColor = '';
                                        e.currentTarget.style.color = 'var(--brand-primary)';
                                      }
                                    }}
                                  >
                                    {isUserSyncing ? (
                                      <span className="flex items-center justify-center gap-1">
                                        <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span className="hidden sm:inline">Syncing...</span>
                                        <span className="sm:hidden">Sync...</span>
                                      </span>
                                    ) : (
                                      <span className="flex items-center justify-center gap-1">
                                        <span>🔄</span>
                                        <span>Sync</span>
                                      </span>
                                    )}
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}

            {Object.keys(usersByGrade).length === 0 && (
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-8 sm:p-12 text-center border border-gray-200">
                <p className="text-gray-500 text-sm sm:text-base md:text-lg">No users found. Users will be organized by grade and role here.</p>
              </div>
            )}
          </div>
        )}

        {/* Google Classroom Tab */}
        {activeTab === 'classroom' && (
          <div className="mb-8">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Classroom Courses</h2>
                <p className="text-sm text-gray-500">
                  {classroomData.length} courses synced
                  {getMostRecentSync(classroomData) && ` • Last full sync: ${formatDateTime(getMostRecentSync(classroomData)!)}`}
                </p>
              </div>
              <button
                onClick={() => syncData('classroom')}
                disabled={loading}
                className={`px-4 sm:px-5 py-2 sm:py-2.5 text-white rounded-lg font-medium text-xs sm:text-sm transition-all duration-300 transform hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:transform-none disabled:hover:shadow-none ${
                  loading ? 'animate-pulse shadow-lg' : ''
                }`}
                style={{ backgroundColor: loading ? 'var(--brand-primary-700)' : 'var(--brand-primary)' }}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--brand-primary-700)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--brand-primary)';
                  }
                }}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="hidden sm:inline">Syncing...</span>
                    <span className="sm:hidden">Sync...</span>
                  </span>
                ) : (
                  <>
                    <span className="hidden sm:inline">Sync All Courses</span>
                    <span className="sm:hidden">Sync All</span>
                  </>
                )}
              </button>
            </div>

            {classroomData.length === 0 ? (
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-8 sm:p-12 text-center border border-gray-200">
                <p className="text-gray-500 text-sm sm:text-base md:text-lg">No courses synced yet. Click &quot;Sync All Courses&quot; to get started.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                {classroomData.map((course) => {
                  const status = getSyncStatus(course.last_synced);
                  const isSyncing = syncingItems.has(`course-${course.id}`);
                  return (
                    <div key={course.id} className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md border border-gray-200 p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1">
                      <div className="flex justify-between items-start mb-3 gap-2">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-sm sm:text-base text-gray-900 mb-1 line-clamp-2">{course.name}</h3>
                          <p className="text-xs text-gray-500">
                            {course.room && `Room: ${course.room}`}
                            {course.room && course.section && ' • '}
                            {course.section && `Section: ${course.section}`}
                          </p>
                        </div>
                        <div className="flex-shrink-0">{getStatusBadge(status)}</div>
                      </div>
                      <p className="text-xs sm:text-sm text-gray-600 mb-3 line-clamp-2">
                        {course.description || 'No description'}
                      </p>
                      <div className="text-xs text-gray-500 mb-3">
                        <p>Last synced: {formatDateTime(course.last_synced || null)}</p>
                        <p>State: {course.state || 'Unknown'}</p>
                      </div>
                      <button
                        onClick={() => syncIndividualCourse(course.id)}
                        disabled={isSyncing || loading}
                        className={`w-full px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:hover:shadow-none ${
                          isSyncing ? 'animate-pulse shadow-md' : ''
                        }`}
                        style={{ 
                          backgroundColor: status === 'outdated' 
                            ? '#dc2626' 
                            : isSyncing 
                              ? 'var(--brand-primary-700)' 
                              : 'var(--brand-primary)',
                          color: 'white'
                        }}
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = status === 'outdated' ? '#b91c1c' : 'var(--brand-primary-700)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = status === 'outdated' ? '#dc2626' : 'var(--brand-primary)';
                          }
                        }}
                      >
                        {isSyncing ? (
                          <span className="flex items-center justify-center gap-2">
                            <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span className="hidden sm:inline">Syncing...</span>
                            <span className="sm:hidden">Sync...</span>
                          </span>
                        ) : (
                          'Sync This Course'
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Google Calendar Tab */}
        {activeTab === 'calendar' && (
          <div className="mb-6 sm:mb-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-0 mb-4">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Calendar Events</h2>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">
                  {calendarData.length} events synced
                  {getMostRecentSync(calendarData) && (
                    <span className="hidden sm:inline"> • Last full sync: {formatDateTime(getMostRecentSync(calendarData)!)}</span>
                  )}
                </p>
              </div>
              <button
                onClick={() => syncData('calendar')}
                disabled={loading}
                className={`px-4 sm:px-5 py-2 sm:py-2.5 text-white rounded-lg font-medium text-xs sm:text-sm transition-all duration-300 transform hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:transform-none disabled:hover:shadow-none ${
                  loading ? 'animate-pulse shadow-lg' : ''
                }`}
                style={{ backgroundColor: loading ? 'var(--brand-secondary-700)' : 'var(--brand-secondary)' }}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--brand-secondary-700)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--brand-secondary)';
                  }
                }}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="hidden sm:inline">Syncing...</span>
                    <span className="sm:hidden">Sync...</span>
                  </span>
                ) : (
                  <>
                    <span className="hidden sm:inline">Sync All Events</span>
                    <span className="sm:hidden">Sync All</span>
                  </>
                )}
              </button>
            </div>

            {calendarData.length === 0 ? (
              <div className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md p-8 sm:p-12 text-center border border-gray-200">
                <p className="text-gray-500 text-sm sm:text-base md:text-lg">No events synced yet. Click &quot;Sync All Events&quot; to get started.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                {calendarData.map((event) => {
                  const status = getSyncStatus(event.last_synced);
                  const isSyncing = syncingItems.has(`event-${event.id}`);
                  return (
                    <div key={event.id} className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md border border-gray-200 p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1">
                      <div className="flex justify-between items-start mb-3 gap-2">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-sm sm:text-base text-gray-900 mb-1 line-clamp-2">{event.title || 'Untitled Event'}</h3>
                          <p className="text-xs text-gray-500">
                            {new Date(event.start).toLocaleDateString('en-GB', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric'
                            })}
                            {event.start && event.end && (
                              <> • {new Date(event.start).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</>
                            )}
                          </p>
                        </div>
                        <div className="flex-shrink-0">{getStatusBadge(status)}</div>
                      </div>
                      <p className="text-xs sm:text-sm text-gray-600 mb-3 line-clamp-2">
                        {event.description || 'No description'}
                      </p>
                      <div className="text-xs text-gray-500 mb-3">
                        <p>Last synced: {formatDateTime(event.last_synced || null)}</p>
                        {event.location && <p className="truncate">Location: {event.location}</p>}
                      </div>
                      <button
                        onClick={() => syncIndividualEvent(event.id, event.calendar_id || 'primary')}
                        disabled={isSyncing || loading}
                        className={`w-full px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:hover:shadow-none ${
                          isSyncing ? 'animate-pulse shadow-md' : ''
                        }`}
                        style={{ 
                          backgroundColor: status === 'outdated' 
                            ? '#dc2626' 
                            : isSyncing 
                              ? 'var(--brand-secondary-700)' 
                              : 'var(--brand-secondary)',
                          color: 'white'
                        }}
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = status === 'outdated' ? '#b91c1c' : 'var(--brand-secondary-700)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = status === 'outdated' ? '#dc2626' : 'var(--brand-secondary)';
                          }
                        }}
                      >
                        {isSyncing ? (
                          <span className="flex items-center justify-center gap-2">
                            <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span className="hidden sm:inline">Syncing...</span>
                            <span className="sm:hidden">Sync...</span>
                          </span>
                        ) : (
                          'Sync This Event'
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Website Pages Tab */}
        {activeTab === 'website' && (
          <div className="mb-6 sm:mb-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-0 mb-4">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Website Pages</h2>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">
                  {websitePages.length} essential pages
                  {getMostRecentSync(websitePages.map(p => ({ last_synced: p.last_crawled }))) && (
                    <span className="hidden sm:inline"> • Last full sync: {formatDateTime(getMostRecentSync(websitePages.map(p => ({ last_synced: p.last_crawled })))!)}</span>
                  )}
                </p>
              </div>
              <button
                onClick={() => syncData('website')}
                disabled={loading}
                className={`px-4 sm:px-5 py-2 sm:py-2.5 text-white rounded-lg font-medium text-xs sm:text-sm transition-all duration-300 transform hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:transform-none disabled:hover:shadow-none ${
                  loading ? 'animate-pulse shadow-lg' : ''
                }`}
                style={{ backgroundColor: loading ? 'var(--brand-primary-700)' : 'var(--brand-primary)' }}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--brand-primary-700)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!e.currentTarget.disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--brand-primary)';
                  }
                }}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="hidden sm:inline">Syncing...</span>
                    <span className="sm:hidden">Sync...</span>
                  </span>
                ) : (
                  <>
                    <span className="hidden sm:inline">Sync All Pages</span>
                    <span className="sm:hidden">Sync All</span>
                  </>
                )}
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {websitePages.map((page) => {
                const status = getSyncStatus(page.last_crawled);
                const isSyncing = syncingItems.has(`page-${page.url}`);
                return (
                  <div key={page.url} className="bg-white rounded-lg sm:rounded-xl shadow-sm sm:shadow-md border border-gray-200 p-4 sm:p-5 transition-all duration-300 hover:shadow-md sm:hover:shadow-lg hover:-translate-y-0.5 sm:hover:-translate-y-1">
                    <div className="flex justify-between items-start mb-3 gap-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm sm:text-base text-gray-900 mb-1 line-clamp-2">{page.title || 'Untitled Page'}</h3>
                        <p className="text-xs text-gray-500 capitalize">{page.content_type}</p>
                      </div>
                      <div className="flex-shrink-0">{getStatusBadge(status)}</div>
                    </div>
                    <p className="text-xs text-gray-600 mb-3 break-all">
                      {page.url}
                    </p>
                    <div className="text-xs text-gray-500 mb-3">
                      <p>Last crawled: {formatDateTime(page.last_crawled)}</p>
                    </div>
                    <button
                      onClick={() => syncIndividualPage(page.url)}
                      disabled={isSyncing || loading}
                      className={`w-full px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:hover:shadow-none ${
                        isSyncing ? 'animate-pulse shadow-md' : ''
                      }`}
                      style={{ 
                        backgroundColor: status === 'outdated' 
                          ? '#dc2626' 
                          : isSyncing 
                            ? 'var(--brand-primary-700)' 
                            : 'var(--brand-primary)',
                        color: 'white'
                      }}
                      onMouseEnter={(e) => {
                        if (!e.currentTarget.disabled) {
                          e.currentTarget.style.backgroundColor = status === 'outdated' ? '#b91c1c' : 'var(--brand-primary-700)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!e.currentTarget.disabled) {
                          e.currentTarget.style.backgroundColor = status === 'outdated' ? '#dc2626' : 'var(--brand-primary)';
                        }
                      }}
                    >
                      {isSyncing ? (
                        <span className="flex items-center justify-center gap-2">
                          <svg className="animate-spin h-3 w-3 sm:h-4 sm:w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="hidden sm:inline">Syncing...</span>
                          <span className="sm:hidden">Sync...</span>
                        </span>
                      ) : (
                        'Sync This Page'
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;















































