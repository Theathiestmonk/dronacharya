"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import { useSearchParams } from 'next/navigation';

interface IntegrationStatus {
  classroom_enabled: boolean;
  calendar_enabled: boolean;
  integrations: Array<{
    service_type: string;
    created_at: string;
    expires_at: string;
  }>;
}

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
}

const AdminDashboard: React.FC = () => {
  const { profile } = useAuth();
  const searchParams = useSearchParams();
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [classroomData, setClassroomData] = useState<ClassroomCourse[]>([]);
  const [calendarData, setCalendarData] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchIntegrationStatus = useCallback(async () => {
    console.log('🔍 [FETCH START] fetchIntegrationStatus called');
    try {
      const adminEmail = profile?.email; // Use logged-in user's email or null for first admin
      console.log(`🔍 [FETCH] Dashboard fetching integrations for email: ${adminEmail}`);
      console.log(`🔍 [FETCH] Profile exists:`, !!profile);
      console.log(`🔍 [FETCH] Profile email: ${profile?.email}`);
      
      // Add cache-busting parameter to force fresh data
      const timestamp = new Date().getTime();
      const emailParam = adminEmail ? `&email=${encodeURIComponent(adminEmail)}` : '';
      const response = await fetch(`/api/admin/integrations?t=${timestamp}${emailParam}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache'
        }
      });
      console.log(`🔍 Integration API response status: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`🔍 Integration data received:`, data);
        console.log(`🔍 Data type of classroom_enabled:`, typeof data.classroom_enabled);
        console.log(`🔍 Data type of calendar_enabled:`, typeof data.calendar_enabled);
        console.log(`🔍 Classroom enabled value:`, data.classroom_enabled);
        console.log(`🔍 Calendar enabled value:`, data.calendar_enabled);
        console.log(`🔍 Integrations array length:`, data.integrations?.length || 0);
        console.log(`🔍 Setting integration status - Classroom: ${data.classroom_enabled}, Calendar: ${data.calendar_enabled}`);
        
        // Ensure boolean values - but only update if we got actual data
        if (data !== null && data !== undefined) {
          const integrationData = {
            classroom_enabled: Boolean(data.classroom_enabled),
            calendar_enabled: Boolean(data.calendar_enabled),
            integrations: data.integrations || []
          };
          
          console.log(`🔍 Normalized integration data:`, integrationData);
          console.log(`🔍 About to call setIntegrationStatus with:`, JSON.stringify(integrationData));
          setIntegrationStatus(integrationData);
          console.log(`🔍 setIntegrationStatus called successfully`);
        } else {
          console.error('🔍 API returned null or undefined data');
        }
      } else {
        console.error('🔍 Failed to fetch integration status:', response.status);
        const errorText = await response.text();
        console.error('🔍 Error response:', errorText);
        // Don't set state to false on error - keep it null or previous value
      }
    } catch (error) {
      console.error('🔍 [ERROR] Error fetching integration status:', error);
      console.error('🔍 [ERROR] Error stack:', error instanceof Error ? error.stack : 'No stack trace');
      // Set error state but don't change integrationStatus to false
    }
  }, [profile]);

  const fetchClassroomData = useCallback(async () => {
    try {
      const adminEmail = profile?.email;
      const emailParam = adminEmail ? `?email=${encodeURIComponent(adminEmail)}` : '';
      // Add cache busting timestamp
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
        console.log(`🔍 [fetchClassroomData] Received ${data.courses?.length || 0} courses`);
        if (data.courses && data.courses.length > 0) {
          console.log(`🔍 [fetchClassroomData] First course last_synced: ${data.courses[0]?.last_synced}`);
        }
        setClassroomData(data.courses || []);
      }
    } catch (error) {
      console.error('Error fetching classroom data:', error);
    }
  }, [profile?.email]);

  const fetchCalendarData = useCallback(async () => {
    try {
      const adminEmail = profile?.email;
      const emailParam = adminEmail ? `?email=${encodeURIComponent(adminEmail)}` : '';
      // Add cache busting timestamp
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
        console.log(`🔍 [fetchCalendarData] Received ${data.events?.length || 0} events`);
        if (data.events && data.events.length > 0) {
          console.log(`🔍 [fetchCalendarData] First event last_synced: ${data.events[0]?.last_synced}`);
        }
        setCalendarData(data.events || []);
      }
    } catch (err) {
      console.error('Error fetching calendar data:', err);
    }
  }, [profile?.email]);

  const connectGoogleService = async (service: 'classroom' | 'calendar' | 'both') => {
    setLoading(true);
    setError(null);
    
    console.log(`🔍 Attempting to connect service: ${service}`);
    
    try {
      const adminEmail = profile?.email; // Use logged-in user's email or null for first admin
      const emailParam = adminEmail ? `&email=${encodeURIComponent(adminEmail)}` : '';
      const response = await fetch(`/api/admin/auth-url?service=${service}${emailParam}`);
      console.log(`🔍 Response status: ${response.status}`);
      console.log(`🔍 Response ok: ${response.ok}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`🔍 Auth URL received: ${data.auth_url}`);
        window.location.href = data.auth_url;
      } else {
        const errorData = await response.json();
        console.error(`🔍 Error response:`, errorData);
        setError(errorData.error || 'Failed to get auth URL');
      }
    } catch (error) {
      console.error(`🔍 Network error:`, error);
      setError('Failed to connect to Google service');
    } finally {
      setLoading(false);
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
        // Refresh data and integration status to update "Last synced" timestamp
        if (service === 'classroom') {
          await fetchClassroomData();
        } else if (service === 'calendar') {
          await fetchCalendarData();
        }
        // Note: website sync doesn't have data to refresh, but we can refresh integration status
        // Force refresh integration status to get updated timestamps
        await fetchIntegrationStatus();
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
    console.log('🔍 [MOUNT] Component mounted, calling fetchIntegrationStatus');
    fetchIntegrationStatus();
    fetchClassroomData();
    fetchCalendarData();
  }, [fetchIntegrationStatus, fetchClassroomData, fetchCalendarData]);

  // Re-fetch integrations when profile changes
  useEffect(() => {
    console.log('🔍 [PROFILE EFFECT] Profile effect triggered, profile:', profile?.email);
    if (profile) {
      console.log('🔍 [PROFILE EFFECT] Profile loaded, fetching integration status');
      console.log('🔍 [PROFILE EFFECT] Calling fetchIntegrationStatus...');
      fetchIntegrationStatus();
    } else {
      console.log('🔍 [PROFILE EFFECT] Profile is null, skipping fetch');
    }
  }, [profile?.email, profile, fetchIntegrationStatus]);

  // Handle URL parameters for connection status
  useEffect(() => {
    if (!searchParams) return;
    
    const connected = searchParams.get('connected');
    if (connected === 'true') {
      console.log('🔍 Detected connected=true in URL, refreshing integration status');
      // Refresh integration status when returning from OAuth
      setTimeout(() => {
        fetchIntegrationStatus();
      }, 1000); // Small delay to ensure callback processing is complete
      // Clean up URL parameter
      const url = new URL(window.location.href);
      url.searchParams.delete('connected');
      window.history.replaceState({}, '', url.toString());
    }
  }, [searchParams, fetchIntegrationStatus]);

  // Debug effect to log integration status changes
  useEffect(() => {
    if (integrationStatus) {
      console.log('🔍 Integration status updated:', integrationStatus);
      console.log('🔍 Classroom enabled value:', integrationStatus.classroom_enabled);
      console.log('🔍 Calendar enabled value:', integrationStatus.calendar_enabled);
      console.log('🔍 Integrations array:', integrationStatus.integrations);
    } else {
      console.log('🔍 Integration status is null/undefined');
    }
  }, [integrationStatus]);

  // Debug: Log current integrationStatus in render
  console.log('🔍 [RENDER] Current integrationStatus:', integrationStatus);
  console.log('🔍 [RENDER] Classroom enabled:', integrationStatus?.classroom_enabled);
  console.log('🔍 [RENDER] Calendar enabled:', integrationStatus?.calendar_enabled);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="mt-2 text-gray-600">Manage Google Classroom and Calendar integrations</p>
            </div>
            <button
              onClick={() => {
                console.log('🔄 Manual refresh triggered');
                fetchIntegrationStatus();
              }}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 text-sm"
            >
              Refresh Status
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Combined Google Integration Button */}
        {(!integrationStatus || !integrationStatus.classroom_enabled || !integrationStatus.calendar_enabled) && (
          <div className="mb-8 bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Connect Google Services</h2>
              <p className="text-gray-600 mb-4">
                Connect both Google Classroom and Calendar with a single click
              </p>
              <button
                onClick={() => connectGoogleService('both')}
                disabled={loading}
                className="bg-gradient-to-r from-blue-600 to-green-600 text-white px-8 py-3 rounded-lg hover:from-blue-700 hover:to-green-700 disabled:opacity-50 font-medium shadow-lg"
              >
                {loading ? 'Connecting...' : 'Connect Google Classroom & Calendar'}
              </button>
            </div>
          </div>
        )}

        {/* Google Integrations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Google Classroom */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Google Classroom</h2>
              <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                integrationStatus && integrationStatus.classroom_enabled === true
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {integrationStatus && integrationStatus.classroom_enabled === true ? 'Connected' : 'Not Connected'}
              </div>
            </div>
            
            <p className="text-gray-600 mb-4">
              Connect your Google Classroom to sync course data and enhance chatbot responses.
            </p>
            
            <div className="space-y-3">
              {!(integrationStatus && integrationStatus.classroom_enabled === true) ? (
                <div className="text-center text-gray-500">
                  <p>Use the &quot;Connect Google Services&quot; button above to connect both Classroom and Calendar</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <button
                    onClick={() => syncData('classroom')}
                    disabled={loading}
                    className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    {loading ? 'Syncing...' : 'Sync Classroom Data'}
                  </button>
                  <p className="text-sm text-gray-500">
                    Last synced: {classroomData.length > 0 && classroomData[0]?.last_synced 
                      ? new Date(classroomData[0].last_synced).toLocaleString('en-GB', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })
                      : 'Never'}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Google Calendar */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Google Calendar</h2>
              <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                integrationStatus && integrationStatus.calendar_enabled === true
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {integrationStatus && integrationStatus.calendar_enabled === true ? 'Connected' : 'Not Connected'}
              </div>
            </div>
            
            <p className="text-gray-600 mb-4">
              Connect your Google Calendar to sync events and provide calendar information.
            </p>
            
            <div className="space-y-3">
              {!(integrationStatus && integrationStatus.calendar_enabled === true) ? (
                <div className="text-center text-gray-500">
                  <p>Use the &quot;Connect Google Services&quot; button above to connect both Classroom and Calendar</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <button
                    onClick={() => syncData('calendar')}
                    disabled={loading}
                    className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    {loading ? 'Syncing...' : 'Sync Calendar Data'}
                  </button>
                  <p className="text-sm text-gray-500">
                    Last synced: {
                      (() => {
                        // Find the most recent sync timestamp from all calendar data
                        const syncTimestamps = calendarData
                          .map(event => event?.last_synced)
                          .filter(Boolean)
                          .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
                        
                        const mostRecent = syncTimestamps[0];
                        
                        return mostRecent 
                          ? new Date(mostRecent).toLocaleString('en-GB', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })
                          : 'Never';
                      })()
                    }
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Website Data Sync */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Website Data</h2>
              <div className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Available
              </div>
            </div>
            
            <p className="text-gray-600 mb-4">
              Sync website data from prakriti.edu.in to update team member information and other website content for the chatbot.
            </p>
            
            <div className="space-y-3">
              <div className="space-y-2">
                <button
                  onClick={() => syncData('website')}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Syncing...' : 'Sync Website Data'}
                </button>
                <p className="text-sm text-gray-500">
                  This will clear old cache and re-crawl the website to update team member profiles and other content.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Data Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Classroom Data */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Classroom Courses</h3>
              <p className="text-sm text-gray-500">{classroomData.length} courses synced</p>
            </div>
            <div className="px-6 py-4 max-h-96 overflow-y-auto">
              {classroomData.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No courses synced yet</p>
              ) : (
                <div className="space-y-3">
                  {classroomData.slice(0, 10).map((course) => (
                    <div key={course.id} className="border border-gray-200 rounded-lg p-3">
                      <h4 className="font-medium text-gray-900">{course.name}</h4>
                      <p className="text-sm text-gray-600">{course.description}</p>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-xs text-gray-500">{course.room}</span>
                        <span className="text-xs text-gray-500">{course.state}</span>
                      </div>
                    </div>
                  ))}
                  {classroomData.length > 10 && (
                    <p className="text-sm text-gray-500 text-center">
                      And {classroomData.length - 10} more courses...
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Calendar Data */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Upcoming Events</h3>
              <p className="text-sm text-gray-500">{calendarData.length} events synced</p>
            </div>
            <div className="px-6 py-4 max-h-96 overflow-y-auto">
              {calendarData.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No events synced yet</p>
              ) : (
                <div className="space-y-3">
                  {calendarData.slice(0, 10).map((event) => (
                    <div key={event.id} className="border border-gray-200 rounded-lg p-3">
                      <h4 className="font-medium text-gray-900">{event.title}</h4>
                      <p className="text-sm text-gray-600">{event.description}</p>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-xs text-gray-500">
                          {new Date(event.start).toLocaleDateString()}
                        </span>
                        <span className="text-xs text-gray-500">{event.location}</span>
                      </div>
                    </div>
                  ))}
                  {calendarData.length > 10 && (
                    <p className="text-sm text-gray-500 text-center">
                      And {calendarData.length - 10} more events...
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;















































