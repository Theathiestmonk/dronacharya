// Utility function to generate intelligent chat names based on the first user message

export const generateChatName = (messages: Array<{sender: string; text: string}>) => {
  if (messages.length === 0) return 'New Chat';
  
  const firstUserMessage = messages.find(msg => msg.sender === 'user');
  if (!firstUserMessage || !firstUserMessage.text) return 'New Chat';
  
  const text = firstUserMessage.text.toLowerCase();
  
  // Education-related topics
  if (text.includes('homework') || text.includes('assignment')) return 'Homework Help';
  if (text.includes('math') || text.includes('mathematics')) return 'Math Questions';
  if (text.includes('science') || text.includes('physics') || text.includes('chemistry') || text.includes('biology')) return 'Science Help';
  if (text.includes('english') || text.includes('literature') || text.includes('writing')) return 'English & Writing';
  if (text.includes('history') || text.includes('social studies')) return 'History & Social Studies';
  if (text.includes('art') || text.includes('drawing') || text.includes('painting')) return 'Art & Creativity';
  if (text.includes('music') || text.includes('singing') || text.includes('instrument')) return 'Music & Arts';
  if (text.includes('sports') || text.includes('physical education') || text.includes('pe')) return 'Sports & PE';
  
  // School-related topics
  if (text.includes('schedule') || text.includes('timetable')) return 'School Schedule';
  if (text.includes('exam') || text.includes('test') || text.includes('quiz')) return 'Exam Preparation';
  if (text.includes('project') || text.includes('presentation')) return 'School Project';
  if (text.includes('curriculum') || text.includes('syllabus')) return 'Curriculum Questions';
  if (text.includes('teacher') || text.includes('instructor')) return 'Teacher Communication';
  if (text.includes('parent') || text.includes('family')) return 'Parent Discussion';
  
  // General topics
  if (text.includes('hello') || text.includes('hi') || text.includes('greetings')) return 'Greeting & Introduction';
  if (text.includes('help') || text.includes('support')) return 'General Help';
  if (text.includes('question') || text.includes('ask')) return 'Questions & Answers';
  if (text.includes('explain') || text.includes('understand')) return 'Explanation Request';
  if (text.includes('study') || text.includes('learn') || text.includes('learning')) return 'Study Session';
  if (text.includes('tips') || text.includes('advice')) return 'Tips & Advice';
  
  // Prakriti-specific
  if (text.includes('prakriti') || text.includes('school')) return 'Prakriti School Info';
  if (text.includes('progressive') || text.includes('alternative')) return 'Progressive Education';
  if (text.includes('happiness') || text.includes('joy')) return 'Learning for Happiness';
  
  // Default fallback - use first few words (max 30 characters)
  const words = firstUserMessage.text.trim().split(/\s+/).slice(0, 4);
  const title = words.join(' ');
  return title.length > 30 ? title.substring(0, 27) + '...' : title;
};






