"use client";
import React, { createContext, useContext, useState, useEffect } from 'react';

type Theme = 'light' | 'dark';

// Extend Window interface for global theme variable
declare global {
  interface Window {
    __INITIAL_THEME__?: Theme;
  }
}

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  resetToSystemTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize theme from localStorage immediately to prevent flash
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  // Apply theme to document immediately on mount
  useEffect(() => {
    setMounted(true);
    
    if (typeof window !== 'undefined') {
      // First, try to read the theme from the global variable set by the script
      const globalTheme = window.__INITIAL_THEME__;
      if (globalTheme && (globalTheme === 'light' || globalTheme === 'dark')) {
        setTheme(globalTheme);
        console.log('🎨 Theme read from global variable:', globalTheme);
        return;
      }
      
      // Second, try to read the theme that was already applied by the script
      const htmlElement = document.documentElement;
      const appliedTheme = htmlElement.classList.contains('dark') ? 'dark' : 'light';
      
      // If a theme is already applied, use it
      if (htmlElement.classList.contains('dark') || htmlElement.classList.contains('light')) {
        setTheme(appliedTheme);
        console.log('🎨 Theme read from HTML element:', appliedTheme);
        return;
      }
      
      // Fallback: read from localStorage
      const savedTheme = localStorage.getItem('theme') as Theme;
      let initialTheme: Theme = 'light';
      
      if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
        initialTheme = savedTheme;
      } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        initialTheme = 'dark';
      }
      
      // Apply theme immediately to prevent flash
      document.documentElement.classList.remove('light', 'dark');
      document.documentElement.classList.add(initialTheme);
      setTheme(initialTheme);
      
      console.log('🎨 Theme initialized from localStorage:', initialTheme);
    }
  }, []);

  // Save theme to localStorage and apply to document when theme changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', theme);
      document.documentElement.classList.remove('light', 'dark');
      document.documentElement.classList.add(theme);
      console.log('🎨 Theme saved and applied:', theme);
    }
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      const handleChange = (e: MediaQueryListEvent) => {
        // Only auto-switch if user hasn't manually set a preference
        const savedTheme = localStorage.getItem('theme');
        if (!savedTheme) {
          const newTheme = e.matches ? 'dark' : 'light';
          setTheme(newTheme);
          console.log('🎨 System theme changed to:', newTheme);
        }
      };

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    console.log('🎨 Theme toggled to:', newTheme);
  };

  const resetToSystemTheme = () => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      setTheme(systemTheme);
      console.log('🎨 Theme reset to system preference:', systemTheme);
    }
  };

  const value: ThemeContextType = {
    theme,
    toggleTheme,
    setTheme,
    resetToSystemTheme,
  };

  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <ThemeContext.Provider value={{ theme: 'light', toggleTheme, setTheme, resetToSystemTheme }}>
        {children}
      </ThemeContext.Provider>
    );
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};
