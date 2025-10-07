"use client";
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import Image from 'next/image';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

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

  // Initialize form data when profile changes
  useEffect(() => {
    if (profile) {
      const defaultColor = profile.avatar_color || '#3B82F6';
      setAvatarColor(defaultColor);
      setFormData({
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

  const getArrayDisplayValue = (field: string): string => {
    const rawValue = formData[`${field}_raw`];
    if (typeof rawValue === 'string') return rawValue;
    
    const arrayValue = formData[field];
    if (Array.isArray(arrayValue)) return arrayValue.join(', ');
    
    return '';
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

  const handleArrayInputChange = (field: string, value: string) => {
    const array = value
      .split(',')
      .map(item => item.trim())
      .filter(item => item.length > 0);
    
    setFormData(prev => ({
      ...prev,
      [field]: array,
      [`${field}_raw`]: value
    }));
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

      const response = await fetch('/api/user-profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...cleanFormData,
          user_id: profile.user_id,
          role: profile.role,
          email: profile.email
        }),
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects</label>
          <input
            type="text"
            value={getArrayDisplayValue('subjects')}
            onChange={(e) => handleArrayInputChange('subjects', e.target.value)}
            placeholder="Math, Science, English"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Learning Style</label>
          <select
            value={getStringValue(formData.learning_style)}
            onChange={(e) => handleInputChange('learning_style', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Interests</label>
        <input
          type="text"
          value={getArrayDisplayValue('interests')}
          onChange={(e) => handleArrayInputChange('interests', e.target.value)}
          placeholder="Sports, Music, Art"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
        />
      </div>
    </div>
  );

  const renderTeacherFields = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Teacher Information</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID</label>
          <input
            type="text"
            value={getStringValue(formData.employee_id)}
            onChange={(e) => handleInputChange('employee_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
          <input
            type="text"
            value={getStringValue(formData.department)}
            onChange={(e) => handleInputChange('department', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects Taught</label>
          <input
            type="text"
            value={getArrayDisplayValue('subjects_taught')}
            onChange={(e) => handleArrayInputChange('subjects_taught', e.target.value)}
            placeholder="Math, Science, English"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience</label>
          <input
            type="number"
            min="0"
            value={getStringValue(formData.years_of_experience)}
            onChange={(e) => handleInputChange('years_of_experience', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Location</label>
          <input
            type="text"
            value={getStringValue(formData.office_location)}
            onChange={(e) => handleInputChange('office_location', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Hours</label>
          <input
            type="text"
            value={getStringValue(formData.office_hours)}
            onChange={(e) => handleInputChange('office_hours', e.target.value)}
            placeholder="9:00 AM - 5:00 PM"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Qualifications</label>
        <textarea
          value={getStringValue(formData.qualifications)}
          onChange={(e) => handleInputChange('qualifications', e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Specializations</label>
        <input
          type="text"
          value={getArrayDisplayValue('specializations')}
          onChange={(e) => handleArrayInputChange('specializations', e.target.value)}
          placeholder="Special Education, STEM"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Workplace</label>
          <input
            type="text"
            value={getStringValue(formData.workplace)}
            onChange={(e) => handleInputChange('workplace', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Contact Method</label>
          <select
            value={getStringValue(formData.preferred_contact_method)}
            onChange={(e) => handleInputChange('preferred_contact_method', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
        />
      </div>
    </div>
  );

  if (!isOpen || !profile) return null;

  return (
    <div className="fixed inset-0 bg-transparent flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Edit Profile</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                  <input
                    type="text"
                    required
                    value={getStringValue(formData.last_name)}
                    onChange={(e) => handleInputChange('last_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                  <select
                    value={getStringValue(formData.gender)}
                    onChange={(e) => handleInputChange('gender', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  >
                    <option value="">Select Gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={getStringValue(formData.phone)}
                    onChange={(e) => handleInputChange('phone', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
                  <input
                    type="date"
                    value={getStringValue(formData.date_of_birth)}
                    onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <textarea
                  value={getStringValue(formData.address)}
                  onChange={(e) => handleInputChange('address', e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={getStringValue(formData.city)}
                    onChange={(e) => handleInputChange('city', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                  <input
                    type="text"
                    value={getStringValue(formData.state)}
                    onChange={(e) => handleInputChange('state', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code</label>
                  <input
                    type="text"
                    value={getStringValue(formData.postal_code)}
                    onChange={(e) => handleInputChange('postal_code', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Phone</label>
                  <input
                    type="tel"
                    value={getStringValue(formData.emergency_contact_phone)}
                    onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Upload Profile Picture</h3>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-400 hover:text-gray-600"
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
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowUploadModal(false)}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                  >
                    Done
                  </button>
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
