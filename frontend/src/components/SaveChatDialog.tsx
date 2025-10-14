"use client";
import React, { useState } from 'react';

interface SaveChatDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => Promise<void>;
  onDiscard: () => void;
  isLoading?: boolean;
  unsavedCount?: number;
}

const SaveChatDialog: React.FC<SaveChatDialogProps> = ({
  isOpen,
  onClose,
  onSave,
  onDiscard,
  isLoading = false,
  unsavedCount = 0
}) => {
  const [saveChanges, setSaveChanges] = useState(true);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop with blur */}
      <div 
        className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex justify-center pt-20 p-4">
        <div className="relative w-72 transform overflow-hidden rounded-lg shadow-xl transition-all bg-white">
          <div className="p-3">
        {/* Header */}
        <div className="flex items-center mb-2">
          <div className="flex-shrink-0">
            <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div className="ml-2">
            <h3 className="text-sm font-medium text-gray-900">
              Unsaved Chat Sessions
            </h3>
          </div>
        </div>

        {/* Content */}
        <div className="mb-3">
          <p className="text-xs text-gray-700 mb-2">
            You have {unsavedCount} unsaved chat session{unsavedCount !== 1 ? 's' : ''}. 
            Save to your account before leaving?
          </p>
          
          {/* Checkbox for save preference */}
          <div className="flex items-center space-x-2 p-1.5 bg-gray-50 rounded border border-gray-200">
            <input
              type="checkbox"
              id="saveChanges"
              checked={saveChanges}
              onChange={(e) => setSaveChanges(e.target.checked)}
              className="h-3 w-3 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="saveChanges" className="text-xs text-gray-600 cursor-pointer">
              Save changes to account
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-1.5 justify-end">
          <button
            onClick={() => {
              if (saveChanges) {
                onSave();
              } else {
                onDiscard();
              }
            }}
            disabled={isLoading}
            className="px-2.5 py-1 text-xs font-medium text-white bg-blue-600 border border-transparent rounded hover:bg-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-1 h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {saveChanges ? 'Saving...' : 'Reloading...'}
              </>
            ) : (
              saveChanges ? 'Save & Reload' : 'Reload'
            )}
          </button>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded hover:bg-gray-200 focus:outline-none focus:ring-1 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SaveChatDialog;
