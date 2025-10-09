"use client";
import React, { useState } from 'react';
import { useAuth } from '@/providers/AuthProvider';

interface OnboardingFormProps {
  user: {
    id: string;
    email?: string;
  };
  onComplete: () => void;
  onBack?: () => void;
}

type UserRole = 'student' | 'teacher' | 'parent';



// Record type for form data with all possible fields
type FormData = Record<string, unknown>;

const OnboardingForm: React.FC<OnboardingFormProps> = ({ user, onComplete, onBack }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [role, setRole] = useState<UserRole>('student');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const { completeOnboarding } = useAuth();

  const [formData, setFormData] = useState<FormData>({
    role: 'student',
    first_name: '',
    last_name: '',
    gender: '',
    phone: '',
    date_of_birth: '',
    address: '',
    city: '',
    state: '',
    postal_code: '',
    preferred_language: 'en',
    // Student fields
    grade: '',
    student_id: '',
    subjects: [],
    learning_goals: '',
    interests: [],
    learning_style: '',
    special_needs: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    // Teacher fields
    employee_id: '',
    department: '',
    subjects_taught: [],
    years_of_experience: 0,
    qualifications: '',
    office_location: '',
    office_hours: '',
    office_hours_start: '',
    office_hours_end: '',
    office_hours_start_display: '',
    office_hours_end_display: '',
    specializations: [],
    // Parent fields
    relationship_to_student: '',
    occupation: '',
    workplace: '',
    preferred_contact_method: '',
    communication_preferences: '',
  });

  const validateField = (field: string, value: unknown): string | null => {
    if (!value || (typeof value === 'string' && value.trim() === '')) {
      return null; // Empty values are allowed for optional fields
    }

    const stringValue = String(value);
    
    // Check VARCHAR(20) fields
    const varchar20Fields = ['phone', 'emergency_contact_phone', 'preferred_contact_method', 'postal_code'];
    if (varchar20Fields.includes(field) && stringValue.length > 20) {
      return `${field.replace('_', ' ')} cannot exceed 20 characters`;
    }
    
    // Check VARCHAR(50) fields
    if (field === 'learning_style' && stringValue.length > 50) {
      return 'Learning style cannot exceed 50 characters';
    }
    
    // Check phone number format
    if ((field === 'phone' || field === 'emergency_contact_phone') && stringValue.length > 0) {
      const phoneRegex = /^[\d\s\-\+\(\)]+$/;
      if (!phoneRegex.test(stringValue)) {
        return 'Please enter a valid phone number';
      }
    }
    
    return null;
  };

  const handleInputChange = (field: string, value: unknown) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear field error when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
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




  // Helper function to safely get string values
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
  const renderFieldError = (field: string) => {
    const error = fieldErrors[field];
    if (error) {
      return <p className="text-red-500 text-xs mt-1">{error}</p>;
    }
    return null;
  };

  const handleRoleChange = (newRole: UserRole) => {
    setRole(newRole);
    setFormData(prev => ({
      ...prev,
      role: newRole,
      // Reset role-specific fields
      grade: undefined,
      student_id: undefined,
      subjects: undefined,
      learning_goals: undefined,
      interests: undefined,
      learning_style: undefined,
      special_needs: undefined,
      emergency_contact_name: undefined,
      emergency_contact_phone: undefined,
      employee_id: undefined,
      department: undefined,
      subjects_taught: undefined,
      years_of_experience: undefined,
      qualifications: undefined,
      specializations: undefined,
      office_location: undefined,
      office_hours: undefined,
      office_hours_start: undefined,
      office_hours_end: undefined,
      office_hours_start_display: '',
      office_hours_end_display: '',
      relationship_to_student: undefined,
      occupation: undefined,
      workplace: undefined,
      preferred_contact_method: undefined,
      communication_preferences: undefined,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setFieldErrors({});

    try {
      // Filter out the _raw fields and time picker fields that are only for display purposes
      const { 
        subjects_raw, 
        interests_raw, 
        subjects_taught_raw, 
        specializations_raw,
        office_hours_start,
        office_hours_end,
        office_hours_start_display,
        office_hours_end_display,
        office_hours_start_hour,
        office_hours_start_minute,
        office_hours_start_ampm,
        office_hours_end_hour,
        office_hours_end_minute,
        office_hours_end_ampm,
        ...cleanFormData 
      } = formData;
      
      // Suppress unused variable warnings for destructured fields that are intentionally unused
      void subjects_raw;
      void interests_raw;
      void subjects_taught_raw;
      void specializations_raw;
      void office_hours_start;
      void office_hours_end;
      void office_hours_start_display;
      void office_hours_end_display;
      void office_hours_start_hour;
      void office_hours_start_minute;
      void office_hours_start_ampm;
      void office_hours_end_hour;
      void office_hours_end_minute;
      void office_hours_end_ampm;
      
      // Validate all fields before submission
      const newFieldErrors: Record<string, string> = {};
      const fieldsToValidate = ['phone', 'emergency_contact_phone', 'preferred_contact_method', 'postal_code', 'learning_style'];
      
      for (const field of fieldsToValidate) {
        const error = validateField(field, cleanFormData[field]);
        if (error) {
          newFieldErrors[field] = error;
        }
      }
      
      // Check role-specific required fields
      const baseRequiredFields = ['first_name', 'last_name'];
      
      // Add role-specific required fields
      const roleRequiredFields = [...baseRequiredFields];
      
      
        if (role === 'student') {
          roleRequiredFields.push('grade', 'student_id', 'learning_style', 'emergency_contact_name', 'emergency_contact_phone');
        } else if (role === 'teacher') {
        roleRequiredFields.push('employee_id', 'department', 'subjects_taught', 'years_of_experience', 'qualifications', 'gender', 'emergency_contact_name', 'emergency_contact_phone');
      } else if (role === 'parent') {
        roleRequiredFields.push('relationship_to_student', 'preferred_contact_method', 'gender', 'emergency_contact_name', 'emergency_contact_phone');
      }
      
      
      // Validate all required fields
      for (const field of roleRequiredFields) {
        const value = cleanFormData[field];
        if (!value || 
            (typeof value === 'string' && value.trim() === '') ||
            (Array.isArray(value) && value.length === 0) ||
            (typeof value === 'number' && value === 0 && field === 'years_of_experience')) {
          
          let fieldLabel = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          if (field === 'subjects_taught') fieldLabel = 'Subjects Taught';
          if (field === 'years_of_experience') fieldLabel = 'Years of Experience';
          if (field === 'preferred_contact_method') fieldLabel = 'Preferred Contact Method';
          if (field === 'relationship_to_student') fieldLabel = 'Relationship to Student';
          
          newFieldErrors[field] = `${fieldLabel} is required`;
        }
      }
      
      // If there are field errors, show them and stop submission
      if (Object.keys(newFieldErrors).length > 0) {
        setFieldErrors(newFieldErrors);
        setLoading(false);
        return;
      }
      
      // Create profile data with only relevant fields for the role
      const profileData: Record<string, unknown> = {
        ...cleanFormData,
        user_id: user.id,
        email: user.email || '',
        onboarding_completed: true,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      
      // Set office_hours from the time inputs
      if (formData.office_hours_start && formData.office_hours_end) {
        profileData.office_hours = `${formData.office_hours_start} - ${formData.office_hours_end}`;
      }

      // Remove undefined/null values to avoid database issues
      Object.keys(profileData).forEach(key => {
        if (profileData[key] === undefined || profileData[key] === null || profileData[key] === '') {
          delete profileData[key];
        }
      });


      // Use the API endpoint instead of direct Supabase calls
      const response = await fetch('/api/user-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save profile');
      }

      const savedProfile = await response.json();

      // Mark onboarding as completed
      await completeOnboarding();
      onComplete();
    } catch (err: unknown) {
      console.error('Error saving profile:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while saving your profile');
    } finally {
      setLoading(false);
    }
  };

  const renderRoleSelection = () => (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-3">Welcome to Prakriti School!</h2>
        <p className="text-lg text-gray-600">Please select your role to get started</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { 
            role: 'student', 
            title: 'Student', 
            description: 'I am a student at Prakriti School', 
            icon: '🎓',
            gradient: 'from-blue-500 to-purple-600',
            bgGradient: 'from-blue-50 to-purple-50',
            borderColor: 'border-blue-200',
            hoverShadow: 'hover:shadow-blue-200'
          },
          { 
            role: 'teacher', 
            title: 'Teacher', 
            description: 'I am a teacher at Prakriti School', 
            icon: '👩‍🏫',
            gradient: 'from-green-500 to-teal-600',
            bgGradient: 'from-green-50 to-teal-50',
            borderColor: 'border-green-200',
            hoverShadow: 'hover:shadow-green-200'
          },
          { 
            role: 'parent', 
            title: 'Parent', 
            description: 'I am a parent of a Prakriti student', 
            icon: '👨‍👩‍👧‍👦',
            gradient: 'from-orange-500 to-pink-600',
            bgGradient: 'from-orange-50 to-pink-50',
            borderColor: 'border-orange-200',
            hoverShadow: 'hover:shadow-orange-200'
          }
        ].map(({ role, title, description, icon, gradient, bgGradient, borderColor, hoverShadow }) => (
          <button
            key={role}
            type="button"
            onClick={() => handleRoleChange(role as UserRole)}
            className={`group relative p-8 border-2 rounded-2xl text-left transition-all duration-300 transform hover:scale-105 hover:-translate-y-2 ${
              formData.role === role
                ? `border-blue-500 bg-gradient-to-br ${bgGradient} shadow-xl shadow-blue-200`
                : `border-gray-200 bg-white hover:border-gray-300 ${hoverShadow} hover:shadow-xl`
            }`}
          >
            {/* Selection indicator */}
            {formData.role === role && (
              <div className="absolute -top-2 -right-2 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
            
            {/* Icon and Title - Centered */}
            <div className="text-center mb-4">
              <div className={`text-3xl mb-3 transition-transform duration-300 ${
                formData.role === role ? 'scale-110' : 'group-hover:scale-110'
              }`} style={{
                filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))',
                textShadow: '0 2px 4px rgba(0,0,0,0.3)'
              }}>
                {icon}
              </div>
              <h3 className={`text-xl font-bold transition-colors duration-300 ${
                formData.role === role ? 'text-blue-700' : 'text-gray-900 group-hover:text-gray-700'
              }`}>
                {title}
              </h3>
            </div>
            
            {/* Description */}
            <div className="text-center">
              <p className={`text-sm leading-relaxed transition-colors duration-300 ${
                formData.role === role ? 'text-blue-600' : 'text-gray-600 group-hover:text-gray-500'
              }`}>
                {description}
              </p>
            </div>
            
            {/* Hover effect overlay */}
            <div className={`absolute inset-0 rounded-2xl transition-opacity duration-300 ${
              formData.role === role 
                ? 'opacity-0' 
                : 'opacity-0 group-hover:opacity-5 bg-gradient-to-r from-gray-400 to-gray-600'
            }`}></div>
          </button>
        ))}
      </div>
      
      {/* Additional visual enhancement */}
      <div className="text-center mt-6">
        <div className="text-sm text-gray-500">
          Choose your role to continue
        </div>
      </div>
    </div>
  );

  const renderBasicInfo = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Basic Information</h2>
        <p className="text-gray-600">Tell us about yourself</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.first_name)}
            onChange={(e) => handleInputChange('first_name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.first_name ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.first_name ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.first_name ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('first_name')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.last_name)}
            onChange={(e) => handleInputChange('last_name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.last_name ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.last_name ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.last_name ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('last_name')}
        </div>
        
        {/* Gender field - only for Teacher and Parent roles */}
        {formData.role !== 'student' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Gender *</label>
            <select
              required
              value={getStringValue(formData.gender)}
              onChange={(e) => handleInputChange('gender', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
              style={{ 
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
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number *</label>
          <input
            type="tel"
            required
            value={getStringValue(formData.phone)}
            onChange={(e) => handleInputChange('phone', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth *</label>
          <input
            type="date"
            required
            value={getStringValue(formData.date_of_birth)}
            onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Address *</label>
        <textarea
          required
          value={getStringValue(formData.address)}
          onChange={(e) => handleInputChange('address', e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">City *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.city)}
            onChange={(e) => handleInputChange('city', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">State *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.state)}
            onChange={(e) => handleInputChange('state', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.postal_code)}
            onChange={(e) => handleInputChange('postal_code', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
      </div>
    </div>
  );

  const renderStudentFields = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Student Information</h2>
        <p className="text-gray-600">Help us personalize your learning experience</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Grade *</label>
          <select
            required
            value={getStringValue(formData.grade)}
            onChange={(e) => handleInputChange('grade', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.grade ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.grade ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.grade ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects (comma-separated)</label>
          <input
            type="text"
            value={getArrayDisplayValue('subjects')}
            onChange={(e) => handleArrayInputChange('subjects', e.target.value)}
            placeholder="Math, Science, English, History"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
          <p className="text-xs text-gray-500 mt-1">Separate multiple subjects with commas</p>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Learning Style *</label>
          <select
            required
            value={getStringValue(formData.learning_style)}
            onChange={(e) => handleInputChange('learning_style', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.learning_style ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.learning_style ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.learning_style ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          >
            <option value="">Select Learning Style</option>
            <option value="visual">Visual</option>
            <option value="auditory">Auditory</option>
            <option value="kinesthetic">Kinesthetic</option>
            <option value="reading-writing">Reading/Writing</option>
            <option value="mixed">Mixed</option>
          </select>
          {renderFieldError('learning_style')}
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Learning Goals</label>
        <textarea
          value={getStringValue(formData.learning_goals)}
          onChange={(e) => handleInputChange('learning_goals', e.target.value)}
          rows={3}
          placeholder="What do you hope to achieve this year?"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Interests (comma-separated)</label>
        <input
          type="text"
          value={getArrayDisplayValue('interests')}
          onChange={(e) => handleArrayInputChange('interests', e.target.value)}
          placeholder="Sports, Music, Art, Science, Technology"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
        <p className="text-xs text-gray-500 mt-1">Separate multiple interests with commas</p>
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Name *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.emergency_contact_name)}
            onChange={(e) => handleInputChange('emergency_contact_name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.emergency_contact_name ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.emergency_contact_name ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.emergency_contact_name ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('emergency_contact_name')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Phone *</label>
          <input
            type="tel"
            required
            value={getStringValue(formData.emergency_contact_phone)}
            onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.emergency_contact_phone ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.emergency_contact_phone ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.emergency_contact_phone ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('emergency_contact_phone')}
        </div>
      </div>
    </div>
  );

  const renderTeacherFields = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Teacher Information</h2>
        <p className="text-gray-600">Help us understand your teaching background</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Faculty ID *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.employee_id)}
            onChange={(e) => handleInputChange('employee_id', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.employee_id ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.employee_id ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.employee_id ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('employee_id')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.department)}
            onChange={(e) => handleInputChange('department', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.department ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.department ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.department ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('department')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects Taught (comma-separated) *</label>
          <input
            type="text"
            required
            value={getArrayDisplayValue('subjects_taught')}
            onChange={(e) => handleArrayInputChange('subjects_taught', e.target.value)}
            placeholder="Math, Science, English"
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.subjects_taught ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.subjects_taught ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.subjects_taught ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          <p className="text-xs text-gray-500 mt-1">Separate multiple subjects with commas</p>
          {renderFieldError('subjects_taught')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience *</label>
          <input
            type="number"
            required
            min="0"
            value={getStringValue(formData.years_of_experience)}
            onChange={(e) => handleInputChange('years_of_experience', parseInt(e.target.value))}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.years_of_experience ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.years_of_experience ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.years_of_experience ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('years_of_experience')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Location</label>
          <input
            type="text"
            value={getStringValue(formData.office_location)}
            onChange={(e) => handleInputChange('office_location', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Hours</label>
          <div className="flex flex-col sm:flex-row sm:items-center space-y-2 sm:space-y-0 sm:space-x-2">
            {/* Start Time */}
            <div className="flex-1 min-w-0">
              <input
                type="text"
                placeholder="HH:MM"
                value={getStringValue(formData.office_hours_start_display)}
                onChange={(e) => {
                  const value = e.target.value;
                  setFormData(prev => {
                    // Convert to 24-hour format for display
                    let displayValue = value;
                    if (value.includes('PM') || value.includes('pm')) {
                      const timeMatch = value.match(/(\d{1,2}):(\d{2})\s*(PM|pm)/);
                      if (timeMatch) {
                        const [, hour, minute] = timeMatch;
                        let hour24 = parseInt(hour);
                        if (hour24 !== 12) hour24 += 12;
                        displayValue = `${hour24.toString().padStart(2, '0')}:${minute}`;
                      }
                    } else if (value.includes('AM') || value.includes('am')) {
                      const timeMatch = value.match(/(\d{1,2}):(\d{2})\s*(AM|am)/);
                      if (timeMatch) {
                        const [, hour, minute] = timeMatch;
                        let hour24 = parseInt(hour);
                        if (hour24 === 12) hour24 = 0;
                        displayValue = `${hour24.toString().padStart(2, '0')}:${minute}`;
                      }
                    } else {
                      // If no AM/PM specified, assume 12-hour format and convert based on time
                      const timeMatch = value.match(/^(\d{1,2}):(\d{2})$/);
                      if (timeMatch) {
                        const [, hour, minute] = timeMatch;
                        let hour24 = parseInt(hour);
                        // For start time, assume AM if hour is 1-11, PM if 12
                        if (hour24 === 12) hour24 = 12; // 12 PM = 12:00
                        // 1-11 AM stays as is
                        displayValue = `${hour24.toString().padStart(2, '0')}:${minute}`;
                      }
                    }
                    
                    return {
                      ...prev,
                      office_hours_start_display: value,
                      office_hours_start: displayValue
                    };
                  });
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 text-sm"
                style={{ 
                  borderColor: 'var(--brand-primary-200)',
                  boxShadow: '0 0 0 1px var(--brand-primary)'
                }}
              />
            </div>
            
            <span className="text-gray-500 font-medium text-sm text-center">to</span>
            
            {/* End Time */}
            <div className="flex-1 min-w-0">
              <input
                type="text"
                placeholder="HH:MM"
                value={getStringValue(formData.office_hours_end_display)}
                onChange={(e) => {
                  const value = e.target.value;
                  setFormData(prev => {
                    // Convert to 24-hour format for display
                    let displayValue = value;
                    if (value.includes('PM') || value.includes('pm')) {
                      const timeMatch = value.match(/(\d{1,2}):(\d{2})\s*(PM|pm)/);
                      if (timeMatch) {
                        const [, hour, minute] = timeMatch;
                        let hour24 = parseInt(hour);
                        if (hour24 !== 12) hour24 += 12;
                        displayValue = `${hour24.toString().padStart(2, '0')}:${minute}`;
                      }
                    } else if (value.includes('AM') || value.includes('am')) {
                      const timeMatch = value.match(/(\d{1,2}):(\d{2})\s*(AM|am)/);
                      if (timeMatch) {
                        const [, hour, minute] = timeMatch;
                        let hour24 = parseInt(hour);
                        if (hour24 === 12) hour24 = 0;
                        displayValue = `${hour24.toString().padStart(2, '0')}:${minute}`;
                      }
                    } else {
                      // If no AM/PM specified, assume 12-hour format and convert based on time
                      const timeMatch = value.match(/^(\d{1,2}):(\d{2})$/);
                      if (timeMatch) {
                        const [, hour, minute] = timeMatch;
                        let hour24 = parseInt(hour);
                        // For end time, assume PM if hour is 1-11, AM if 12
                        if (hour24 >= 1 && hour24 <= 11) hour24 += 12; // 1-11 PM
                        else if (hour24 === 12) hour24 = 0; // 12 AM = 00:00
                        displayValue = `${hour24.toString().padStart(2, '0')}:${minute}`;
                      }
                    }
                    
                    return {
                      ...prev,
                      office_hours_end_display: value,
                      office_hours_end: displayValue
                    };
                  });
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 text-sm"
                style={{ 
                  borderColor: 'var(--brand-primary-200)',
                  boxShadow: '0 0 0 1px var(--brand-primary)'
                }}
              />
            </div>
          </div>
          {getStringValue(formData.office_hours_start) && getStringValue(formData.office_hours_end) && (
            <div className="mt-1 text-xs text-gray-600">
              <span className="font-medium">Hours:</span> {getStringValue(formData.office_hours_start)} - {getStringValue(formData.office_hours_end)}
            </div>
          )}
          </div>
        </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Qualifications *</label>
        <textarea
          required
          value={getStringValue(formData.qualifications)}
          onChange={(e) => handleInputChange('qualifications', e.target.value)}
          rows={3}
          placeholder="B.Ed, M.A. in Mathematics, etc."
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
            fieldErrors.qualifications ? 'border-red-500' : 'border-gray-300'
          }`}
          style={{ 
            borderColor: fieldErrors.qualifications ? '#ef4444' : 'var(--brand-primary-200)',
            boxShadow: fieldErrors.qualifications ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
          }}
        />
        {renderFieldError('qualifications')}
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Specializations (comma-separated)</label>
        <input
          type="text"
          value={getArrayDisplayValue('specializations')}
          onChange={(e) => handleArrayInputChange('specializations', e.target.value)}
          placeholder="Special Education, STEM, Language Arts"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1"
          style={{ 
            borderColor: 'var(--brand-primary-200)',
            boxShadow: '0 0 0 1px var(--brand-primary)'
          }}
        />
        <p className="text-xs text-gray-500 mt-1">Separate multiple specializations with commas</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Name *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.emergency_contact_name)}
            onChange={(e) => handleInputChange('emergency_contact_name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.emergency_contact_name ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.emergency_contact_name ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.emergency_contact_name ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('emergency_contact_name')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Phone *</label>
          <input
            type="tel"
            required
            value={getStringValue(formData.emergency_contact_phone)}
            onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.emergency_contact_phone ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.emergency_contact_phone ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.emergency_contact_phone ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('emergency_contact_phone')}
        </div>
      </div>
    </div>
  );

  const renderParentFields = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Parent Information</h2>
        <p className="text-gray-600">Help us keep you informed about your child&apos;s progress</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Relationship to Student *</label>
          <select
            required
            value={getStringValue(formData.relationship_to_student)}
            onChange={(e) => handleInputChange('relationship_to_student', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
            style={{ 
              borderColor: 'var(--brand-primary-200)',
              boxShadow: '0 0 0 1px var(--brand-primary)'
            }}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Contact Method *</label>
          <select
            required
            value={getStringValue(formData.preferred_contact_method)}
            onChange={(e) => handleInputChange('preferred_contact_method', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Name *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.emergency_contact_name)}
            onChange={(e) => handleInputChange('emergency_contact_name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.emergency_contact_name ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.emergency_contact_name ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.emergency_contact_name ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('emergency_contact_name')}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Phone *</label>
          <input
            type="tel"
            required
            value={getStringValue(formData.emergency_contact_phone)}
            onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              fieldErrors.emergency_contact_phone ? 'border-red-500' : 'border-gray-300'
            }`}
            style={{ 
              borderColor: fieldErrors.emergency_contact_phone ? '#ef4444' : 'var(--brand-primary-200)',
              boxShadow: fieldErrors.emergency_contact_phone ? '0 0 0 1px #ef4444' : '0 0 0 1px var(--brand-primary)'
            }}
          />
          {renderFieldError('emergency_contact_phone')}
        </div>
      </div>
    </div>
  );

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return renderRoleSelection();
      case 2:
        return renderBasicInfo();
      case 3:
        if (role === 'student') return renderStudentFields();
        if (role === 'teacher') return renderTeacherFields();
        if (role === 'parent') return renderParentFields();
        return null;
      default:
        return null;
    }
  };


  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return formData.role !== undefined;
      case 2:
        const basicFields = formData.first_name && formData.last_name && formData.phone && formData.date_of_birth && formData.address && formData.city && formData.state && formData.postal_code;
        // For teacher and parent roles, also require gender in step 2
        if (role === 'teacher' || role === 'parent') {
          return basicFields && formData.gender;
        }
        return basicFields;
      case 3:
        if (role === 'student') {
          const canProceedStudent = formData.grade && formData.student_id && formData.learning_style && formData.emergency_contact_name && formData.emergency_contact_phone;
          return canProceedStudent;
        }
        if (role === 'teacher') {
          const canProceedTeacher = formData.employee_id && formData.department && formData.subjects_taught && formData.years_of_experience !== undefined && formData.qualifications && formData.gender && formData.emergency_contact_name && formData.emergency_contact_phone;
          return canProceedTeacher;
        }
        if (role === 'parent') {
          const canProceedParent = formData.relationship_to_student && formData.preferred_contact_method && formData.gender && formData.emergency_contact_name && formData.emergency_contact_phone;
          return canProceedParent;
        }
        return false;
      default:
        return false;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full space-y-8">
        {/* Back button */}
        {onBack && (
          <div className="flex justify-start">
            <button
              onClick={onBack}
              className="flex items-center text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Chatbot
            </button>
          </div>
        )}
        
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {/* Progress Bar */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Step {currentStep} of 3</span>
              <span className="text-sm text-gray-500">{Math.round((currentStep / 3) * 100)}% Complete</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="h-2 rounded-full transition-all duration-300"
                style={{ 
                  width: `${(currentStep / 3) * 100}%`,
                  backgroundColor: 'var(--brand-primary)'
                }}
              ></div>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            {renderStepContent()}
            
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div className="flex justify-between mt-8">
              <button
                type="button"
                onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
                disabled={currentStep === 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              {currentStep < 3 ? (
                <button
                  type="button"
                  onClick={() => setCurrentStep(currentStep + 1)}
                  disabled={!canProceed()}
                  className="px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ backgroundColor: 'var(--brand-primary)' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
                >
                  Next
                </button>
              ) : (
                <div>
                  <button
                    type="submit"
                    disabled={!canProceed() || loading}
                    className="px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ backgroundColor: 'var(--brand-primary)' }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
                  >
                    {loading ? 'Saving...' : 'Complete Setup'}
                  </button>
                  
                </div>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OnboardingForm;
