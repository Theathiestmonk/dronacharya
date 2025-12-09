"use client";
import React from 'react';
import Image from 'next/image';

interface PrakritiLoaderProps {
  message?: string;
  className?: string;
}

const PrakritiLoader: React.FC<PrakritiLoaderProps> = ({ 
  message = "Loading Prakriti AI...",
  className = ""
}) => {
  return (
    <div className={`flex min-h-screen h-screen bg-[#0a1929] ${className}`}>
      <main className="flex-1 flex items-center justify-center h-screen">
        <div className="w-full max-w-2xl h-full flex flex-col justify-center">
          <div className="flex justify-center mb-6">
            <Image 
              src="/prakriti_logo.webp" 
              alt="Prakriti Visual" 
              width={150}
              height={150}
              style={{ maxWidth: '150px', height: 'auto' }}
              className="object-contain"
            />
          </div>
          <div className="text-center">
            <span className="text-white text-lg font-light">
              {message}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PrakritiLoader;

















