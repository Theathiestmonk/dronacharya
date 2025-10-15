"use client";
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import Link from 'next/link';

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
  const { profile, signOut } = useAuth();
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [classroomData, setClassroomData] = useState<ClassroomCourse[]>([]);
  const [calendarData, setCalendarData] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchIntegrationStatus = async () => {
    try {
      const response = await fetch('/api/admin/integrations');
      if (response.ok) {
        const data = await response.json();
        setIntegrationStatus(data);
      }
    } catch (error) {
      console.error('Error fetching integration status:', error);
    }
  };

  const fetchClassroomData = async () => {
    try {
      const response = await fetch('/api/admin/data/classroom');
      if (response.ok) {
        const data = await response.json();
        setClassroomData(data.courses);
      }
    } catch (error) {
      console.error('Error fetching classroom data:', error);
    }
  };

  const fetchCalendarData = async () => {
    try {
      const response = await fetch('/api/admin/data/calendar');
      if (response.ok) {
        const data = await response.json();
        setCalendarData(data.events);
      }
    } catch (err) {
      console.error('Error fetching calendar data:', err);
    }
  };

  const connectGoogleService = async (service: 'classroom' | 'calendar') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/auth-url?service=${service}`);
      if (response.ok) {
        const data = await response.json();
        window.location.href = data.auth_url;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to get auth URL');
      }
    } catch {
      setError('Failed to connect to Google service');
    } finally {
      setLoading(false);
    }
  };

  const syncData = async (service: 'classroom' | 'calendar') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/sync/${service}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(data.message);
        // Refresh data
        if (service === 'classroom') {
          fetchClassroomData();
        } else {
          fetchCalendarData();
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Sync failed');
      }
    } catch {
      setError('Failed to sync data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrationStatus();
    fetchClassroomData();
    fetchCalendarData();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="mt-2 text-gray-600">Manage Google Classroom and Calendar integrations</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, {profile?.first_name} {profile?.last_name}</span>
              <Link
                href="/admin/management"
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
              >
                Manage Admins
              </Link>
              <button
                onClick={signOut}
                className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 text-sm"
              >
                Logout
              </button>
            </div>
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

        {/* Google Integrations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Google Classroom */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Google Classroom</h2>
              <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                integrationStatus?.classroom_enabled 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {integrationStatus?.classroom_enabled ? 'Connected' : 'Not Connected'}
              </div>
            </div>
            
            <p className="text-gray-600 mb-4">
              Connect your Google Classroom to sync course data and enhance chatbot responses.
            </p>
            
            <div className="space-y-3">
              {!integrationStatus?.classroom_enabled ? (
                <button
                  onClick={() => connectGoogleService('classroom')}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Connecting...' : 'Connect Google Classroom'}
                </button>
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
                    Last synced: {classroomData.length > 0 ? new Date(classroomData[0]?.last_synced).toLocaleString() : 'Never'}
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
                integrationStatus?.calendar_enabled 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {integrationStatus?.calendar_enabled ? 'Connected' : 'Not Connected'}
              </div>
            </div>
            
            <p className="text-gray-600 mb-4">
              Connect your Google Calendar to sync events and provide calendar information.
            </p>
            
            <div className="space-y-3">
              {!integrationStatus?.calendar_enabled ? (
                <button
                  onClick={() => connectGoogleService('calendar')}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Connecting...' : 'Connect Google Calendar'}
                </button>
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
                    Last synced: {calendarData.length > 0 ? new Date(calendarData[0]?.last_synced).toLocaleString() : 'Never'}
                  </p>
                </div>
              )}
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
