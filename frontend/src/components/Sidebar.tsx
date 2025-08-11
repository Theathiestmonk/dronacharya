import React from 'react';

interface SidebarProps {
  role: 'admin' | 'teacher' | 'student' | 'parent';
  onSelect: (page: string) => void;
}

const navItems = {
  admin: [
    { label: 'Dashboard', page: 'dashboard' },
    { label: 'Attendance', page: 'attendance' },
    { label: 'Lesson Plans', page: 'lessonplans' },
    { label: 'Homework', page: 'homework' },
    { label: 'Grading', page: 'grading' },
    { label: 'Insights', page: 'insights' },
  ],
  teacher: [
    { label: 'Dashboard', page: 'dashboard' },
    { label: 'Attendance', page: 'attendance' },
    { label: 'Lesson Plans', page: 'lessonplans' },
    { label: 'Homework', page: 'homework' },
    { label: 'Grading', page: 'grading' },
  ],
  student: [
    { label: 'Dashboard', page: 'dashboard' },
    { label: 'Homework', page: 'homework' },
    { label: 'Grades', page: 'grades' },
    { label: 'Insights', page: 'insights' },
  ],
  parent: [
    { label: 'Dashboard', page: 'dashboard' },
    { label: 'Attendance', page: 'attendance' },
    { label: 'Grades', page: 'grades' },
    { label: 'Insights', page: 'insights' },
  ],
};

const Sidebar: React.FC<SidebarProps> = ({ role, onSelect }) => {
  return (
    <aside className="w-64 h-full bg-white shadow-lg rounded-r-xl p-6 flex flex-col gap-4">
      <h2 className="text-2xl font-bold mb-6">School AI</h2>
      <nav className="flex flex-col gap-2">
        {navItems[role].map((item) => (
          <button
            key={item.page}
            onClick={() => onSelect(item.page)}
            className="text-left px-4 py-2 rounded-lg hover:bg-blue-100 transition"
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar; 