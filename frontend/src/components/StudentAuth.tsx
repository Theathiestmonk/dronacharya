"use client";
import React, { useState } from 'react';
import StudentLoginForm from './StudentLoginForm';
import StudentRegistrationForm from './StudentRegistrationForm';

interface StudentAuthProps {
  onSuccess?: (studentData: { id?: number; student_id?: string; email?: string } | null) => void;
  onCancel?: () => void;
}

const StudentAuth: React.FC<StudentAuthProps> = ({ onSuccess, onCancel }) => {
  const [isLogin, setIsLogin] = useState(true);

  const handleSwitchMode = () => {
    setIsLogin(!isLogin);
  };

  const handleSuccess = (studentData: { id?: number; student_id?: string; email?: string } | null) => {
    if (onSuccess) {
      onSuccess(studentData);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      {isLogin ? (
        <StudentLoginForm
          onSuccess={handleSuccess}
          onCancel={handleCancel}
          onSwitchToRegister={handleSwitchMode}
        />
      ) : (
        <StudentRegistrationForm
          onSuccess={() => handleSuccess(null)}
          onCancel={handleCancel}
        />
      )}
      
      {/* Switch Mode Button */}
      <div className="fixed bottom-4 right-4">
        <button
          onClick={handleSwitchMode}
          className="text-white px-4 py-2 rounded-lg shadow-lg transition-colors"
          style={{ backgroundColor: 'var(--brand-primary)' }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
        >
          {isLogin ? 'Switch to Registration' : 'Switch to Login'}
        </button>
      </div>
    </div>
  );
};

export default StudentAuth;
