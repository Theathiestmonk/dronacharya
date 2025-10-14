"use client";
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import Image from 'next/image';

interface EditAvatarModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EditAvatarModal: React.FC<EditAvatarModalProps> = ({ isOpen, onClose }) => {
  const { profile, updateProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [avatarColor, setAvatarColor] = useState('#3B82F6');
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [profilePictureUrl, setProfilePictureUrl] = useState('');

  // Initialize data when profile changes
  useEffect(() => {
    if (profile) {
      const defaultColor = profile.avatar_color || '#3B82F6';
      setAvatarColor(defaultColor);
      setProfilePictureUrl(profile.profile_picture_url || '');
    }
  }, [profile]);

  const getInitials = () => {
    if (profile?.first_name && profile?.last_name) {
      return `${profile.first_name.charAt(0)}${profile.last_name.charAt(0)}`.toUpperCase();
    }
    if (profile?.email) {
      return profile.email.charAt(0).toUpperCase();
    }
    return 'U';
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
      setProfilePictureUrl(base64);
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
    setProfilePictureUrl('');
  };

  const handleAvatarColorChange = (color: string) => {
    setAvatarColor(color);
    setProfilePictureUrl(''); // Clear image when color is selected
    setUploadedImage(null);
  };

  const handleUrlChange = (url: string) => {
    setProfilePictureUrl(url);
    setUploadedImage(null); // Clear uploaded image when URL is entered
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

  const handleSave = async () => {
    if (!profile) return;

    setLoading(true);
    setError(null);

    try {
      const updateData = {
        profile_picture_url: profilePictureUrl,
        avatar_color: avatarColor,
      };

      const response = await fetch('/api/user-profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...updateData,
          user_id: profile.user_id,
          role: profile.role,
          email: profile.email
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update avatar');
      }

      const updatedProfile = await response.json();
      
      // Update the profile in context
      if (updateProfile) {
        await updateProfile(updatedProfile);
      }

      onClose();
    } catch (err: unknown) {
      console.error('Error updating avatar:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while updating your avatar');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !profile) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900">Edit Avatar</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-6">
            {/* Current Avatar Preview */}
            <div className="flex justify-center">
              <div className="relative">
                {(uploadedImage || profilePictureUrl) ? (
                  <div className="relative group">
                    <Image
                      src={uploadedImage || profilePictureUrl}
                      alt="Profile"
                      width={80}
                      height={80}
                      className="w-20 h-20 rounded-full object-cover border-4 border-gray-200"
                    />
                    <button
                      type="button"
                      onClick={removeUploadedImage}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600 transition-colors"
                    >
                      ×
                    </button>
                  </div>
                ) : (
                  <div 
                    className="w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-semibold border-4 border-gray-200"
                    style={{ backgroundColor: avatarColor }}
                  >
                    {getInitials()}
                  </div>
                )}
              </div>
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Upload Profile Picture</label>
              
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
                      id="avatar-upload"
                    />
                    <label
                      htmlFor="avatar-upload"
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
            </div>

            {/* URL Input - only show if no uploaded image */}
            {!uploadedImage && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Or enter image URL</label>
                <input
                  type="url"
                  value={profilePictureUrl}
                  onChange={(e) => handleUrlChange(e.target.value)}
                  placeholder="https://example.com/your-photo.jpg"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2"
                />
              </div>
            )}

            {/* Avatar Color Picker - only show if no profile picture */}
            {!uploadedImage && !profilePictureUrl && (
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
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
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
                onClick={handleSave}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save Avatar'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EditAvatarModal;
