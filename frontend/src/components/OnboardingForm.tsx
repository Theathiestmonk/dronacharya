"use client";
import React, { useState } from 'react';
import { useSupabase } from '@/providers/SupabaseProvider';
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
  const supabase = useSupabase();
  const { completeOnboarding } = useAuth();

  const [formData, setFormData] = useState<FormData>({
    role: 'student',
    first_name: '',
    last_name: '',
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
    specializations: [],
    // Parent fields
    relationship_to_student: '',
    occupation: '',
    workplace: '',
    preferred_contact_method: '',
    communication_preferences: '',
  });

  const handleInputChange = (field: string, value: unknown) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleArrayInputChange = (field: string, value: string) => {
    // Split by comma, trim whitespace, and filter out empty strings
    const array = value
      .split(',')
      .map(item => item.trim())
      .filter(item => item.length > 0);
    
    setFormData(prev => ({
      ...prev,
      [field]: array
    }));
  };

  // Helper function to safely get string values
  const getStringValue = (value: unknown): string => {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value.join(', ');
    if (value === undefined || value === null) return '';
    return String(value);
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

    try {
      if (!supabase) {
        throw new Error('Database not available');
      }

      const profileData = {
        ...formData,
        user_id: user.id,
        email: user.email || '',
        onboarding_completed: true,
      };

      const { error } = await supabase
        .from('user_profiles')
        .upsert(profileData);

      if (error) throw error;

      // Mark onboarding as completed
      completeOnboarding();
      onComplete();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred while saving your profile');
    } finally {
      setLoading(false);
    }
  };

  const renderRoleSelection = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Prakriti School!</h2>
        <p className="text-gray-600">Please select your role to get started</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { role: 'student', title: 'Student', description: 'I am a student at Prakriti School', icon: '🎓' },
          { role: 'teacher', title: 'Teacher', description: 'I am a teacher at Prakriti School', icon: '👩‍🏫' },
          { role: 'parent', title: 'Parent', description: 'I am a parent of a Prakriti student', icon: '👨‍👩‍👧‍👦' }
        ].map(({ role, title, description, icon }) => (
          <button
            key={role}
            type="button"
            onClick={() => handleRoleChange(role as UserRole)}
            className={`p-6 border-2 rounded-lg text-left transition-all ${
              formData.role === role
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="text-3xl mb-3">{icon}</div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-sm text-gray-600">{description}</p>
          </button>
        ))}
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.last_name)}
            onChange={(e) => handleInputChange('last_name', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number *</label>
          <input
            type="tel"
            required
            value={getStringValue(formData.phone)}
            onChange={(e) => handleInputChange('phone', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth *</label>
          <input
            type="date"
            required
            value={getStringValue(formData.date_of_birth)}
            onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">State *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.state)}
            onChange={(e) => handleInputChange('state', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.postal_code)}
            onChange={(e) => handleInputChange('postal_code', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects (comma-separated)</label>
          <input
            type="text"
            value={getStringValue(formData.subjects)}
            onChange={(e) => handleArrayInputChange('subjects', e.target.value)}
            placeholder="Math, Science, English, History"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">Separate multiple subjects with commas</p>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Learning Style</label>
          <select
            value={getStringValue(formData.learning_style)}
            onChange={(e) => handleInputChange('learning_style', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          placeholder="What do you hope to achieve this year?"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Interests (comma-separated)</label>
        <input
          type="text"
          value={getStringValue(formData.interests)}
          onChange={(e) => handleArrayInputChange('interests', e.target.value)}
          placeholder="Sports, Music, Art, Science, Technology"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact Phone *</label>
          <input
            type="tel"
            required
            value={getStringValue(formData.emergency_contact_phone)}
            onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
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
          <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID</label>
          <input
            type="text"
            value={getStringValue(formData.employee_id)}
            onChange={(e) => handleInputChange('employee_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.department)}
            onChange={(e) => handleInputChange('department', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subjects Taught (comma-separated) *</label>
          <input
            type="text"
            required
            value={getStringValue(formData.subjects_taught)}
            onChange={(e) => handleArrayInputChange('subjects_taught', e.target.value)}
            placeholder="Math, Science, English"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">Separate multiple subjects with commas</p>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience *</label>
          <input
            type="number"
            required
            min="0"
            value={getStringValue(formData.years_of_experience)}
            onChange={(e) => handleInputChange('years_of_experience', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Location</label>
          <input
            type="text"
            value={getStringValue(formData.office_location)}
            onChange={(e) => handleInputChange('office_location', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Office Hours</label>
          <input
            type="text"
            value={getStringValue(formData.office_hours)}
            onChange={(e) => handleInputChange('office_hours', e.target.value)}
            placeholder="9:00 AM - 5:00 PM"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
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
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Specializations (comma-separated)</label>
        <input
          type="text"
          value={getStringValue(formData.specializations)}
          onChange={(e) => handleArrayInputChange('specializations', e.target.value)}
          placeholder="Special Education, STEM, Language Arts"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">Separate multiple specializations with commas</p>
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Workplace</label>
          <input
            type="text"
            value={getStringValue(formData.workplace)}
            onChange={(e) => handleInputChange('workplace', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Contact Method *</label>
          <select
            required
            value={getStringValue(formData.preferred_contact_method)}
            onChange={(e) => handleInputChange('preferred_contact_method', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
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
        return formData.first_name && formData.last_name && formData.phone && formData.date_of_birth && formData.address && formData.city && formData.state && formData.postal_code;
      case 3:
        if (role === 'student') {
          return formData.grade && formData.emergency_contact_name && formData.emergency_contact_phone;
        }
        if (role === 'teacher') {
          return formData.department && formData.subjects_taught && formData.years_of_experience !== undefined && formData.qualifications;
        }
        if (role === 'parent') {
          return formData.relationship_to_student && formData.preferred_contact_method;
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
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(currentStep / 3) * 100}%` }}
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
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!canProceed() || loading}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Saving...' : 'Complete Setup'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OnboardingForm;
