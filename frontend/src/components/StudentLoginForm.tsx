"use client";
import React, { useState } from 'react';

interface StudentLoginFormProps {
  onSuccess?: (studentData: { id?: number; student_id?: string; email?: string } | null) => void;
  onCancel?: () => void;
  onSwitchToRegister?: () => void;
}

const StudentLoginForm: React.FC<StudentLoginFormProps> = ({ 
  onSuccess, 
  onCancel,
  onSwitchToRegister
}) => {
  const [formData, setFormData] = useState({
    student_id: '',
    password: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.student_id.trim()) {
      newErrors.student_id = 'Student ID is required';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    
    try {
      const response = await fetch('/api/students', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: formData.student_id,
          password: formData.password
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (onSuccess) {
          onSuccess(data.student);
        }
      } else {
        const errorData = await response.json();
        setErrors({ submit: errorData.error || 'Login failed' });
      }
    } catch {
      setErrors({ submit: 'Network error. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg p-8 border border-gray-200">
      <div className="flex justify-center mb-6">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/prakriti_logo.webp" alt="Prakriti Logo" style={{ maxWidth: '90px', height: 'auto' }} />
      </div>
      
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-900">Student Login</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Student ID
          </label>
          <input
            type="text"
            name="student_id"
            value={formData.student_id}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.student_id ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="Enter your Student ID"
            required
          />
          {errors.student_id && <p className="text-red-500 text-xs mt-1">{errors.student_id}</p>}
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.password ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="Enter your password"
            required
          />
          {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
        </div>

        {/* Submit Error */}
        {errors.submit && (
          <div className="text-red-700 text-sm font-semibold bg-red-50 border border-red-200 rounded px-3 py-2">
            {errors.submit}
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-3">
          <button
            type="submit"
            disabled={loading}
            className="w-full text-white py-3 px-6 rounded-md transition font-semibold shadow disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: 'var(--brand-primary)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
          
          {onSwitchToRegister && (
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="w-full bg-green-700 text-white py-3 px-6 rounded-md hover:bg-green-800 transition font-semibold shadow"
            >
              New Student? Register Here
            </button>
          )}
          
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="w-full bg-gray-500 text-white py-3 px-6 rounded-md hover:bg-gray-600 transition font-semibold shadow"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
      
      <div className="mt-6 text-center text-sm text-gray-600">
        <p>Forgot your password? Contact the school administration.</p>
      </div>
    </div>
  );
};

export default StudentLoginForm;
