"use client";
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import Image from 'next/image';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
type UserRole = 'student' | 'teacher' | 'parent';
type FormData = Record<string, unknown>;

const EditProfileModal: React.FC<EditProfileModalProps> = ({ isOpen, onClose }) => {
  const { profile, updateProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formData, setFormData] = useState<FormData>({});
  const [avatarColor, setAvatarColor] = useState('#3B82F6'); // Default blue color
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [googleClassroomConnected, setGoogleClassroomConnected] = useState(false);
  const [isCheckingConnection, setIsCheckingConnection] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    // Cleanup on unmount
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Check Google Classroom connection status for students
  useEffect(() => {
    const checkGoogleClassroomConnection = async () => {
      if (profile && profile.role === 'student' && profile.email) {
        setIsCheckingConnection(true);
        try {
          const response = await fetch(`/api/student/google-classroom/status?email=${encodeURIComponent(profile.email)}`);
          if (response.ok) {
            const data = await response.json();
            setGoogleClassroomConnected(data.connected || false);
          }
        } catch (error) {
          console.error('Error checking Google Classroom connection:', error);
        } finally {
          setIsCheckingConnection(false);
        }
      }
    };
    
    if (isOpen && profile?.role === 'student') {
      checkGoogleClassroomConnection();
    }
  }, [isOpen, profile]);

  // Initialize form data when profile changes
  useEffect(() => {
    if (profile) {
      console.log('Profile received in EditProfileModal:', profile);
      console.log('Profile role:', profile.role);
      const defaultColor = profile.avatar_color || '#3B82F6';
      setAvatarColor(defaultColor);
      setFormData({
        role: profile.role || 'student',
        first_name: profile.first_name || '',
        last_name: profile.last_name || '',
        gender: profile.gender || '',
        phone: profile.phone || '',
        date_of_birth: profile.date_of_birth || '',
        profile_picture_url: profile.profile_picture_url || '',
        avatar_color: profile.avatar_color || '#3B82F6',
        address: profile.address || '',
        city: profile.city || '',
        state: profile.state || '',
        postal_code: profile.postal_code || '',
        preferred_language: profile.preferred_language || 'en',
        // Student fields
        grade: profile.grade || '',
        student_id: profile.student_id || '',
        subjects: profile.subjects || [],
        learning_goals: profile.learning_goals || '',
        interests: profile.interests || [],
        learning_style: profile.learning_style || '',
        special_needs: profile.special_needs || '',
        emergency_contact_name: profile.emergency_contact_name || '',
        emergency_contact_phone: profile.emergency_contact_phone || '',
        // Teacher fields
        employee_id: profile.employee_id || '',
        department: profile.department || '',
        subjects_taught: profile.subjects_taught || [],
        years_of_experience: profile.years_of_experience || 0,
        qualifications: profile.qualifications || '',
        specializations: profile.specializations || [],
        office_location: profile.office_location || '',
        office_hours: profile.office_hours || '',
        // Parent fields
        relationship_to_student: profile.relationship_to_student || '',
        occupation: profile.occupation || '',
        workplace: profile.workplace || '',
        preferred_contact_method: profile.preferred_contact_method || '',
        communication_preferences: profile.communication_preferences || '',
      });
    }
  }, [profile]);

  const getStringValue = (value: unknown): string => {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value.join(', ');
    if (value === undefined || value === null) return '';
    return String(value);
  };

  // Helper function to get display value for array fields
  const getArrayDisplayValue = (field: string): string => {
    const rawValue = formData[`${field}_raw`];
    if (typeof rawValue === 'string') return rawValue;
    
    const arrayValue = formData[field];
    if (Array.isArray(arrayValue)) return arrayValue.join(', ');
    
    return '';
  };

  // Helper function to render field error
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const renderFieldError = (field: string) => {
    const error = fieldErrors[field];
    if (error) {
      return <p className="text-red-500 text-xs mt-1">{error}</p>;
    }
    return null;
  };

  const handleArrayInputChange = (field: string, value: string) => {
    // Store the raw string value for display, but also prepare the array
    const array = value
      .split(',')
      .map(item => item.trim())
      .filter(item => item.length > 0);
    
    setFormData(prev => ({
      ...prev,
      [field]: array,
      [`${field}_raw`]: value // Store raw string for display
    }));
  };

  const handleInputChange = (field: string, value: unknown) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    if (fieldErrors[field]) {
      setFieldErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleAvatarColorChange = (color: string) => {
    setAvatarColor(color);
    handleInputChange('avatar_color', color);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image size must be less than 5MB');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      // Convert file to base64
      const base64 = await convertToBase64(file);
      setUploadedImage(base64);
      handleInputChange('profile_picture_url', base64);
    } catch (err) {
      setError('Failed to process image. Please try again.');
      console.error('Error processing image:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const convertToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (error) => reject(error);
    });
  };

  const removeUploadedImage = () => {
    setUploadedImage(null);
    handleInputChange('profile_picture_url', '');
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        // Create a proper synthetic event for file upload
        const syntheticEvent = {
          target: { files: [file] }
        } as unknown as React.ChangeEvent<HTMLInputElement>;
        handleFileUpload(syntheticEvent);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    
    setLoading(true);
    setError(null);
    setFieldErrors({});

    try {
      const { 
        subjects_raw, 
        interests_raw, 
        subjects_taught_raw, 
        specializations_raw,
        ...cleanFormData 
      } = formData;
      
      // Suppress unused variable warnings
      void subjects_raw;
      void interests_raw;
      void subjects_taught_raw;
      void specializations_raw;

      const requestData = {
        ...cleanFormData,
        user_id: profile.user_id,
        role: formData.role,
        email: profile.email
      };
      
      // Handle gender field - if empty, set to null for students
      if (formData.role === 'student' && (!(requestData as Record<string, unknown>).gender || (requestData as Record<string, unknown>).gender === '')) {
        (requestData as Record<string, unknown>).gender = null;
      }
      
      console.log('Sending profile update:', requestData);
      console.log('Role value being sent:', requestData.role);
      console.log('Role type:', typeof requestData.role);
      
      const response = await fetch('/api/user-profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update profile');
      }

      const updatedProfile = await response.json();
      console.log('Profile updated successfully:', updatedProfile);

      // Update the profile in context
      if (updateProfile) {
        await updateProfile(updatedProfile);
      }

      onClose();
    } catch (err: unknown) {
      console.error('Error updating profile:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while updating your profile');
    } finally {
      setLoading(false);
    }
  };


  const renderStudentFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Student Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Grade</label>
          <select
            value={getStringValue(formData.grade)}
            onChange={(e) => handleInputChange('grade', e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 relative z-10"
            style={{ 
              position: 'relative',
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          >
            <option value="">Select Grade</option>
            <option value="Pre-Nursery">Pre-Nursery</option>
            <option value="Nursery">Nursery</option>
            <option value="KG">KG</option>
            {Array.from({ length: 12 }, (_, i) => `Grade ${i + 1}`).map(grade => (
              <option key={grade} value={grade}>{grade}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Student ID</label>
          <input
            type="text"
            value={getStringValue(formData.student_id)}
            onChange={(e) => handleInputChange('student_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects</label>
          <input
            type="text"
            value={getArrayDisplayValue('subjects')}
            onChange={(e) => handleArrayInputChange('subjects', e.target.value)}
            placeholder="Math, Science, English"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Learning Style</label>
          <select
            value={getStringValue(formData.learning_style)}
            onChange={(e) => handleInputChange('learning_style', e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 relative z-10"
            style={{ 
              position: 'relative',
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          >
            <option value="">Select Learning Style</option>
            <option value="visual">Visual</option>
            <option value="auditory">Auditory</option>
            <option value="kinesthetic">Kinesthetic</option>
            <option value="reading-writing">Reading/Writing</option>
            <option value="mixed">Mixed</option>
          </select>
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Learning Goals</label>
        <textarea
          value={getStringValue(formData.learning_goals)}
          onChange={(e) => handleInputChange('learning_goals', e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Interests</label>
        <input
          type="text"
          value={getArrayDisplayValue('interests')}
          onChange={(e) => handleArrayInputChange('interests', e.target.value)}
          placeholder="Sports, Music, Art"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Special Needs or Accommodations</label>
        <textarea
          value={getStringValue(formData.special_needs)}
          onChange={(e) => handleInputChange('special_needs', e.target.value)}
          rows={2}
          placeholder="Any special needs or accommodations you require"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>

      {/* Google Classroom Connection Section */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-md font-semibold text-gray-900 mb-3">Google Classroom Integration</h4>
        <p className="text-sm text-gray-600 mb-4">
          Connect your Google Classroom account to access your assignments, homework, and classwork directly from your profile.
        </p>
        
        {isCheckingConnection ? (
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Checking connection status...</span>
          </div>
        ) : googleClassroomConnected ? (
          <div className="space-y-3">
            <div className="flex items-center space-x-2 text-green-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium">Google Classroom Connected</span>
            </div>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={async () => {
                  if (!profile?.email) {
                    alert('Email not found in profile');
                    return;
                  }
                  setIsConnecting(true);
                  try {
                    const response = await fetch('/api/student/google-classroom/sync', { 
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ email: profile.email })
                    });
                    if (response.ok) {
                      alert('Classroom data synced successfully!');
                    } else {
                      const data = await response.json();
                      alert(data.error || 'Failed to sync classroom data. Please try again.');
                    }
                  } catch (error) {
                    console.error('Error syncing classroom:', error);
                    alert('Error syncing classroom data.');
                  } finally {
                    setIsConnecting(false);
                  }
                }}
                disabled={isConnecting}
                className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isConnecting ? 'Syncing...' : 'Sync Now'}
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!profile?.email) {
                    alert('Email not found in profile');
                    return;
                  }
                  if (confirm('Are you sure you want to disconnect Google Classroom? You will need to reconnect to access your assignments.')) {
                    try {
                      const response = await fetch('/api/student/google-classroom/disconnect', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: profile.email })
                      });
                      if (response.ok) {
                        setGoogleClassroomConnected(false);
                        alert('Google Classroom disconnected successfully.');
                      } else {
                        const data = await response.json();
                        alert(data.error || 'Failed to disconnect. Please try again.');
                      }
                    } catch (error) {
                      console.error('Error disconnecting:', error);
                      alert('Error disconnecting Google Classroom.');
                    }
                  }
                }}
                className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100"
              >
                Disconnect
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={async () => {
              setIsConnecting(true);
              try {
                const response = await fetch('/api/student/google-classroom/auth-url');
                if (response.ok) {
                  const data = await response.json();
                  if (data.auth_url) {
                    window.location.href = data.auth_url;
                  } else {
                    alert('Failed to get authentication URL. Please try again.');
                  }
                } else {
                  alert('Failed to initiate Google Classroom connection. Please try again.');
                }
              } catch (error) {
                console.error('Error connecting Google Classroom:', error);
                alert('Error connecting to Google Classroom.');
              } finally {
                setIsConnecting(false);
              }
            }}
            disabled={isConnecting}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isConnecting ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                <span>Connect Google Classroom</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );

  const renderTeacherFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Teacher Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Faculty ID</label>
          <input
            type="text"
            value={getStringValue(formData.employee_id)}
            onChange={(e) => handleInputChange('employee_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
          <input
            type="text"
            value={getStringValue(formData.department)}
            onChange={(e) => handleInputChange('department', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects Taught</label>
          <input
            type="text"
            value={getArrayDisplayValue('subjects_taught')}
            onChange={(e) => handleArrayInputChange('subjects_taught', e.target.value)}
            placeholder="Math, Science, English"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience</label>
          <input
            type="number"
            min="0"
            value={getStringValue(formData.years_of_experience)}
            onChange={(e) => handleInputChange('years_of_experience', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Location</label>
          <input
            type="text"
            value={getStringValue(formData.office_location)}
            onChange={(e) => handleInputChange('office_location', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Hours</label>
          <input
            type="text"
            value={getStringValue(formData.office_hours)}
            onChange={(e) => handleInputChange('office_hours', e.target.value)}
            placeholder="9:00 AM - 5:00 PM"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Qualifications</label>
        <textarea
          value={getStringValue(formData.qualifications)}
          onChange={(e) => handleInputChange('qualifications', e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Specializations</label>
        <input
          type="text"
          value={getArrayDisplayValue('specializations')}
          onChange={(e) => handleArrayInputChange('specializations', e.target.value)}
          placeholder="Special Education, STEM"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
    </div>
  );

  const renderParentFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Parent Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Relationship to Student</label>
          <select
            value={getStringValue(formData.relationship_to_student)}
            onChange={(e) => handleInputChange('relationship_to_student', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          >
            <option value="">Select Relationship</option>
            <option value="mother">Mother</option>
            <option value="father">Father</option>
            <option value="guardian">Guardian</option>
            <option value="grandparent">Grandparent</option>
            <option value="other">Other</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Occupation</label>
          <input
            type="text"
            value={getStringValue(formData.occupation)}
            onChange={(e) => handleInputChange('occupation', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Workplace</label>
          <input
            type="text"
            value={getStringValue(formData.workplace)}
            onChange={(e) => handleInputChange('workplace', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Contact Method</label>
          <select
            value={getStringValue(formData.preferred_contact_method)}
            onChange={(e) => handleInputChange('preferred_contact_method', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          >
            <option value="">Select Method</option>
            <option value="email">Email</option>
            <option value="phone">Phone</option>
            <option value="sms">SMS</option>
          </select>
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Communication Preferences</label>
        <textarea
          value={getStringValue(formData.communication_preferences)}
          onChange={(e) => handleInputChange('communication_preferences', e.target.value)}
          rows={3}
          placeholder="How would you like to be contacted? Any specific preferences?"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
    </div>
  );

  if (!isOpen || !profile) return null;

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop with blur */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-lg transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-2xl transform overflow-hidden rounded-2xl shadow-xl transition-all bg-white">
          <div className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Edit Profile</h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6 max-h-[70vh] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 hover:scrollbar-thumb-gray-400 p-1" style={{ overflowY: 'auto', overflowX: 'visible' }}>
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>
              
              {/* Profile Picture */}
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0 relative group">
                    {(uploadedImage || getStringValue(formData.profile_picture_url)) ? (
                      <div className="relative">
                        <Image
                          src={uploadedImage || getStringValue(formData.profile_picture_url)}
                          alt="Profile"
                          width={64}
                          height={64}
                          className="w-16 h-16 rounded-full object-cover border-2 border-gray-200"
                        />
                        <button
                          type="button"
                          onClick={removeUploadedImage}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          ×
                        </button>
                      </div>
                    ) : (
                      <div 
                        className="w-16 h-16 rounded-full flex items-center justify-center text-white text-xl font-semibold"
                        style={{ backgroundColor: avatarColor }}
                      >
                        {getStringValue(formData.first_name).charAt(0)}{getStringValue(formData.last_name).charAt(0)}
                      </div>
                    )}
                    
                    {/* Edit Pen Icon */}
                    <button
                      type="button"
                      onClick={() => setShowUploadModal(true)}
                      className="absolute -bottom-1 -right-1 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-blue-600 transition-all opacity-0 group-hover:opacity-100 shadow-lg"
                      title="Edit Avatar"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                {/* Avatar Color Picker - only show if no profile picture */}
                {!uploadedImage && !getStringValue(formData.profile_picture_url) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Avatar Color</label>
                    <div className="flex items-center space-x-3">
                      <input
                        type="color"
                        value={avatarColor}
                        onChange={(e) => handleAvatarColorChange(e.target.value)}
                        className="w-12 h-12 rounded-lg border border-gray-300 cursor-pointer"
                      />
                      <div className="flex space-x-2">
                        {[
                          '#3B82F6', // Blue
                          '#10B981', // Green
                          '#8B5CF6', // Purple
                          '#F59E0B', // Amber
                          '#EF4444', // Red
                          '#06B6D4', // Cyan
                          '#84CC16', // Lime
                          '#F97316', // Orange
                        ].map((color) => (
                          <button
                            key={color}
                            type="button"
                            onClick={() => handleAvatarColorChange(color)}
                            className={`w-8 h-8 rounded-full border-2 ${
                              avatarColor === color ? 'border-gray-400' : 'border-gray-200'
                            } hover:border-gray-300 transition-colors`}
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Choose a color for your avatar background</p>
                  </div>
                )}
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                  <input
                    type="text"
                    required
                    value={getStringValue(formData.first_name)}
                    onChange={(e) => handleInputChange('first_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                  <input
                    type="text"
                    required
                    value={getStringValue(formData.last_name)}
                    onChange={(e) => handleInputChange('last_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={getStringValue(formData.phone)}
                    onChange={(e) => handleInputChange('phone', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
                  <input
                    type="date"
                    value={getStringValue(formData.date_of_birth)}
                    onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                {/* Gender field - only for Teacher and Parent roles */}
                {formData.role !== 'student' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                    <select
                      value={getStringValue(formData.gender)}
                      onChange={(e) => handleInputChange('gender', e.target.value)}
                      className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 relative z-10"
                      style={{ 
                        position: 'relative',
                        borderColor: 'var(--brand-primary-200)',
                        boxShadow: '0 0 0 1px var(--brand-primary)'
                      }}
                    >
                      <option value="">Select Gender</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                      <option value="prefer_not_to_say">Prefer not to say</option>
                    </select>
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <textarea
                  value={getStringValue(formData.address)}
                  onChange={(e) => handleInputChange('address', e.target.value)}
                  rows={3}
                  placeholder="Enter your full address"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
                  style={{ 
                    borderColor: 'var(--brand-primary-200)',
                    boxShadow: '0 0 0 1px var(--brand-primary)'
                  }}
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={getStringValue(formData.city)}
                    onChange={(e) => handleInputChange('city', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                  <input
                    type="text"
                    value={getStringValue(formData.state)}
                    onChange={(e) => handleInputChange('state', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code</label>
                  <input
                    type="text"
                    value={getStringValue(formData.postal_code)}
                    onChange={(e) => handleInputChange('postal_code', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
              </div>
            </div>

            {/* Role-specific fields */}
            {profile.role === 'student' && renderStudentFields()}
            {profile.role === 'teacher' && renderTeacherFields()}
            {profile.role === 'parent' && renderParentFields()}

            {/* Emergency Contact */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Emergency Contact</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Name</label>
                  <input
                    type="text"
                    value={getStringValue(formData.emergency_contact_name)}
                    onChange={(e) => handleInputChange('emergency_contact_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Phone</label>
                  <input
                    type="tel"
                    value={getStringValue(formData.emergency_contact_phone)}
                    onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-[10000] overflow-y-auto">
          {/* Backdrop with blur */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-lg transition-opacity"
            onClick={() => setShowUploadModal(false)}
          />
          
          {/* Modal */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative w-full max-w-md transform overflow-hidden rounded-2xl shadow-xl transition-all bg-white">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Upload Profile Picture</h3>
                  <button
                    onClick={() => setShowUploadModal(false)}
                    className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

              <div className="space-y-4">
                {/* Current Avatar Preview */}
                <div className="flex justify-center">
                  <div className="relative">
                    {(uploadedImage || getStringValue(formData.profile_picture_url)) ? (
                      <Image
                        src={uploadedImage || getStringValue(formData.profile_picture_url)}
                        alt="Profile"
                        width={80}
                        height={80}
                        className="w-20 h-20 rounded-full object-cover border-4 border-gray-200"
                      />
                    ) : (
                      <div 
                        className="w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-semibold border-4 border-gray-200"
                        style={{ backgroundColor: avatarColor }}
                      >
                        {getStringValue(formData.first_name).charAt(0)}{getStringValue(formData.last_name).charAt(0)}
                      </div>
                    )}
                  </div>
                </div>

                {/* File Upload */}
                <div
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors"
                >
                  <div className="space-y-3">
                    <svg className="mx-auto h-10 w-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <div className="flex items-center justify-center space-x-2">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleFileUpload}
                        disabled={isUploading}
                        className="hidden"
                        id="upload-modal-file"
                      />
                      <label
                        htmlFor="upload-modal-file"
                        className={`px-4 py-2 text-sm font-medium text-white rounded-md cursor-pointer transition-colors ${
                          isUploading 
                            ? 'bg-gray-400 cursor-not-allowed' 
                            : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                      >
                        {isUploading ? 'Uploading...' : 'Choose File'}
                      </label>
                      <span className="text-sm text-gray-500">or drag and drop</span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Max 5MB, JPG/PNG/GIF supported
                    </p>
                  </div>
                </div>


                {/* Color Picker - only show if no image */}
                {!uploadedImage && !getStringValue(formData.profile_picture_url) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Choose Avatar Color</label>
                    <div className="flex items-center space-x-3">
                      <input
                        type="color"
                        value={avatarColor}
                        onChange={(e) => handleAvatarColorChange(e.target.value)}
                        className="w-12 h-12 rounded-lg border border-gray-300 cursor-pointer"
                      />
                      <div className="flex space-x-2">
                        {[
                          '#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', 
                          '#EF4444', '#06B6D4', '#84CC16', '#F97316'
                        ].map((color) => (
                          <button
                            key={color}
                            type="button"
                            onClick={() => handleAvatarColorChange(color)}
                            className={`w-8 h-8 rounded-full border-2 ${
                              avatarColor === color ? 'border-gray-400' : 'border-gray-200'
                            } hover:border-gray-300 transition-colors`}
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowUploadModal(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowUploadModal(false)}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 cursor-pointer"
                  >
                    Done
                  </button>
                </div>
              </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EditProfileModal;
