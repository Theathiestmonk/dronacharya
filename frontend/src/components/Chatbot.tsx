import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useState as useCopyState } from 'react';
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/providers/AuthProvider';
import { useChatHistory } from '@/providers/ChatHistoryProvider';

type Message =
  | { sender: 'user' | 'bot'; text: string }
  | { sender: 'bot'; type: 'calendar'; url: string }
  | { sender: 'bot'; type: 'map'; url: string }
  | { sender: 'bot'; type: 'videos'; videos: Array<{video_id: string; title: string; description: string; category: string; duration: string; thumbnail_url: string}> };

// Typing animation component - shows "Searching" character by character, then dots
const TypingAnimation: React.FC = () => {
  const [displayText, setDisplayText] = React.useState('');
  const animationRef = React.useRef<number | null>(null);
  const dotRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const word = 'Searching';
    const dots = '...';
    let currentIndex = 0;
    let isTypingWord = true;

    const typeText = () => {
      if (isTypingWord) {
        // Typing "Searching" character by character
        if (currentIndex < word.length) {
          setDisplayText(word.substring(0, currentIndex + 1));
          currentIndex++;
          animationRef.current = window.setTimeout(typeText, 150); // Slower speed - 150ms per character
        } else {
          // Finished typing "Searching", now add dots one by one
          isTypingWord = false;
          currentIndex = 0;
          animationRef.current = window.setTimeout(typeText, 200); // Brief pause before dots
        }
      } else {
        // Adding dots one by one
        if (currentIndex < dots.length) {
          const dotsText = dots.substring(0, currentIndex + 1);
          setDisplayText(word + dotsText);
          currentIndex++;
          animationRef.current = window.setTimeout(typeText, 150); // Speed of typing dots
        } else {
          // Finished, reset and start over
          currentIndex = 0;
          isTypingWord = true;
          setDisplayText('');
          animationRef.current = window.setTimeout(typeText, 500); // Brief pause before restarting
        }
      }
    };

    // Start typing immediately
    typeText();

    // Cleanup on unmount
    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
  }, []);

  // Split displayText into word and dots for styling
  const word = 'Searching';
  const isShowingDots = displayText.startsWith(word) && displayText.length > word.length;
  const wordPart = isShowingDots ? word : displayText;
  const dotsPart = isShowingDots ? displayText.substring(word.length) : '';

  return (
    <div className="flex items-center gap-3">
        {/* First dot - bigger, blinking slowly */}
        <div 
          ref={dotRef}
          className="rounded-full"
          style={{
            width: '14px',
            height: '14px',
            backgroundColor: 'var(--brand-primary)',
            animation: 'first-dot-blink 2s ease-in-out infinite'
          }}
        />
        {/* Searching text */}
        <span 
          className="text-sm font-medium"
          style={{ 
            color: 'var(--brand-primary)',
            minWidth: '100px',
            display: 'inline-block'
          }}
        >
          {wordPart}
          {dotsPart && (
            <span style={{ fontSize: '10px', display: 'inline-block' }}>
              {dotsPart}
  </span>
          )}
        </span>
    </div>
);
};

// Simple copy icon SVG
const CopyIcon = ({ copied }: { copied: boolean }) => (
  copied ? (
    <svg className="w-5 h-5 text-green-500 ml-2" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
  ) : (
    <svg className="w-5 h-5 text-gray-400 ml-2 cursor-pointer hover:opacity-70" style={{ color: 'var(--brand-primary)' }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>
  )
);

interface ChatbotProps {
  clearChat?: () => void;
  externalQuery?: string;
  onQueryProcessed?: () => void;
}

const Chatbot = React.forwardRef<{ clearChat: () => void }, ChatbotProps>(({ clearChat, externalQuery, onQueryProcessed }, ref) => {
  const { user, profile } = useAuth();
  const { 
    getActiveSession, 
    addMessage, 
    clearActiveSession, 
    activeSessionId,
    refreshChatComponents,
    isLoading: chatHistoryLoading,
    createNewSession,
    activeSessionMessageCount // Track message count to detect session updates
  } = useChatHistory();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [requestInProgress, setRequestInProgress] = useState(false);
  const [listening, setListening] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [, setHasFirstResponse] = useState(false);
  const [micPlaceholder, setMicPlaceholder] = useState<string>('Ask me anything...');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const mainContainerRef = useRef<HTMLDivElement>(null); // Ref for main container to prevent blinking
  const isInbuiltQueryRef = useRef(false); // Track if current message is from inbuilt query
  const [isInbuiltQueryActive, setIsInbuiltQueryActive] = useState(false); // State to prevent blinking
  const [displayedBotText, setDisplayedBotText] = useState<string>('');
  const [isTyping, setIsTyping] = useState(false);
  const [typingAnimationKey, setTypingAnimationKey] = useState(0); // Key to retrigger animation
  const [shouldAnimate, setShouldAnimate] = useState(false); // Control animation trigger
  const loadingStartTimeRef = useRef<number | null>(null); // Track when loading starts
  const [showTypingAnimation, setShowTypingAnimation] = useState(false); // Control typing animation visibility
  const responseStartedTypingRef = useRef<boolean>(false); // Track if response has started typing to prevent animation from showing again
  const [isDesktop, setIsDesktop] = useState(false); // Track desktop for scrollbar hiding
  // For copy feedback per message
  const [copiedIdx, setCopiedIdx] = useCopyState<number | null>(null);
  const [showClearedMessage, setShowClearedMessage] = useState(false);
  // Conversation history for context
  const [conversationHistory, setConversationHistory] = useState<Array<{role: string, content: string}>>([]);

  // Dynamic welcome messages with focus words
  const welcomeMessages = useMemo(() => [
    { text: "What curiosity leads the way?", focusWord: "curiosity" },
    { text: "Which idea is lighting your path?", focusWord: "idea" },
    { text: "What learning spark calls you onward?", focusWord: "spark" },
    { text: "Which question opens your world?", focusWord: "question" },
    { text: "What secret is the wind sharing?", focusWord: "secret" },
    { text: "Which dream is calling your name?", focusWord: "dream" },
    { text: "What story is unfolding around you?", focusWord: "story" },
    { text: "Which adventure is waiting quietly?", focusWord: "adventure" },
    { text: "What whispers guide your steps?", focusWord: "whispers" },
    { text: "Which spark are you chasing?", focusWord: "spark" },
    { text: "What gentle voice do you hear?", focusWord: "voice" },
    { text: "Which call of wonder do you follow?", focusWord: "wonder" }
  ], []);

  // Get a random welcome message
  const getRandomWelcomeMessage = useCallback(() => {
    const randomIndex = Math.floor(Math.random() * welcomeMessages.length);
    return welcomeMessages[randomIndex];
  }, [welcomeMessages]);

  // Initialize welcome message immediately to prevent "Loading..." flash
  const [welcomeMessage, setWelcomeMessage] = useState<{ text: string; focusWord: string } | null>(() => {
    // Set welcome message immediately on mount to prevent "Loading..." from showing
    if (typeof window !== 'undefined') {
      try {
        const randomIndex = Math.floor(Math.random() * welcomeMessages.length);
        return welcomeMessages[randomIndex];
      } catch {
        return welcomeMessages[0];
      }
    }
    return null;
  });

  // Initialize welcome message on client side only (fallback)
  useEffect(() => {
    try {
      if (!welcomeMessage) {
        setWelcomeMessage(getRandomWelcomeMessage());
      }
    } catch (error) {
      console.error('Error setting welcome message:', error);
      // Fallback to first message if random generation fails
      setWelcomeMessage(welcomeMessages[0]);
    }
  }, [getRandomWelcomeMessage, welcomeMessages, welcomeMessage]);


  // Function to render welcome message with highlighted focus word
  const renderWelcomeMessage = (message: { text: string; focusWord: string }) => {
    try {
      const focusWordIndex = message.text.toLowerCase().indexOf(message.focusWord.toLowerCase());
      
      if (focusWordIndex === -1) {
        return message.text;
      }
      
      const beforeFocus = message.text.substring(0, focusWordIndex);
      const afterFocus = message.text.substring(focusWordIndex + message.focusWord.length);
      
      return (
        <>
          {beforeFocus}
          <span className="font-bold" style={{ color: '#23479f' }}>{message.focusWord}</span>
          {afterFocus}
        </>
      );
    } catch (error) {
      console.error('Error rendering welcome message:', error);
      return message.text;
    }
  };

  // Speech-to-text logic
  const handleMic = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return;
    }
    
    // Check if already listening
    if (listening) {
      return;
    }
    
    // @ts-expect-error - webkitSpeechRecognition is not in TypeScript types
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false; // Stop after first result
    
    setListening(true);
    setMicPlaceholder('Listening...');
    
    recognition.onresult = async (event: Event) => {
      try {
      const results = (event as unknown as { results: SpeechRecognitionResultList }).results;
        if (!results || results.length === 0) {
          console.warn('No speech recognition results');
          setListening(false);
          setMicPlaceholder('Ask me anything...');
          return;
        }

      const transcript = results[0][0].transcript;
        console.log('Speech recognition transcript:', transcript);
      setListening(false);

      // Set transcript in input field and update placeholder - user must manually send
      if (transcript && transcript.trim()) {
        setInput(transcript);
        setMicPlaceholder(transcript);
        console.log('✅ Speech transcript set in input field - user must click send button');
      } else {
        setMicPlaceholder('Ask me anything...');
      }

      inputRef.current?.focus({ preventScroll: true });
      } catch (error) {
        console.error('Error processing speech recognition result:', error);
        setListening(false);
        setMicPlaceholder('Error processing speech. Try again...');
        setTimeout(() => setMicPlaceholder('Ask me anything...'), 2000);
      }
    };
    
    recognition.onerror = (event: Event) => {
      const errorEvent = event as unknown as { error: string; message?: string };
      const errorName = errorEvent.error || 'unknown';
      
      setListening(false);
      
      // Handle "no-speech" errors silently (just update placeholder, no alert)
      if (errorName === 'no-speech') {
        console.log('No speech detected - user may not have spoken');
        setMicPlaceholder('No speech detected. Try again...');
        setTimeout(() => setMicPlaceholder('Ask me anything...'), 2000);
        return; // Exit early, don't show alert
      }
      
      // Log other errors for debugging
      console.error('Speech recognition error:', errorName, errorEvent.message);
      setMicPlaceholder('Ask me anything...');
      
      // Provide user-friendly error messages for critical errors only
      let errorMessage = 'Speech recognition failed. ';
      switch (errorName) {
        case 'audio-capture':
          errorMessage = 'Microphone not found or access denied. Please check your microphone permissions.';
          break;
        case 'not-allowed':
          errorMessage = 'Microphone permission denied. Please allow microphone access in your browser settings.';
          break;
        case 'network':
          errorMessage = 'Network error. Please check your internet connection.';
          break;
        case 'aborted':
          // Aborted errors are usually intentional (user stopped), so handle silently
          console.log('Speech recognition was aborted');
          return; // Exit early, don't show alert
        case 'service-not-allowed':
          errorMessage = 'Speech recognition service not allowed. Please check your browser settings.';
          break;
        default:
          errorMessage = `Speech recognition error: ${errorName}. Please try again.`;
      }
      
      // Show error message to user only for critical errors
      alert(errorMessage);
    };
    
    recognition.onend = () => {
      console.log('Speech recognition ended');
      setListening(false);
      setMicPlaceholder('Ask me anything...');
    };
    
    recognition.onstart = () => {
      console.log('Speech recognition started');
    };
    
    try {
    recognition.start();
    } catch (error) {
      console.error('Error starting speech recognition:', error);
      setListening(false);
      setMicPlaceholder('Ask me anything...');
      alert('Failed to start speech recognition. Please try again or check your microphone permissions.');
    }
  };

  // Helper function to hide typing animation with minimum display duration
  const hideTypingAnimationWithMinDuration = (immediate: boolean = false) => {
    if (immediate || !loadingStartTimeRef.current) {
      setShowTypingAnimation(false);
      responseStartedTypingRef.current = true; // Mark that response has started
      return;
    }
    
    // Ensure minimum display duration (3-4 seconds for all queries)
    const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
    const elapsed = Date.now() - loadingStartTimeRef.current;
    const remainingTime = Math.max(0, minDisplayDuration - elapsed);
    
    if (remainingTime > 0) {
      // Don't set responseStartedTypingRef immediately - wait for minimum duration
      setTimeout(() => {
        setShowTypingAnimation(false);
        responseStartedTypingRef.current = true; // Mark that response has started after minimum duration
      }, remainingTime);
    } else {
      setShowTypingAnimation(false);
      responseStartedTypingRef.current = true; // Mark that response has started
    }
  };

  // Helper function to set loading to false with minimum display duration
  const setLoadingWithMinDuration = (immediate: boolean = false) => {
    if (immediate || !loadingStartTimeRef.current) {
      setLoading(false);
      setShowTypingAnimation(false);
      loadingStartTimeRef.current = null;
      responseStartedTypingRef.current = false; // Reset flag
      return;
    }
    
    // Ensure minimum display duration (3-4 seconds for all queries)
    const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
    const elapsed = Date.now() - loadingStartTimeRef.current;
    const remainingTime = Math.max(0, minDisplayDuration - elapsed);
    
    if (remainingTime > 0) {
      setTimeout(() => {
        setLoading(false);
        setShowTypingAnimation(false);
        loadingStartTimeRef.current = null;
        responseStartedTypingRef.current = false; // Reset flag
      }, remainingTime);
    } else {
      setLoading(false);
      setShowTypingAnimation(false);
      loadingStartTimeRef.current = null;
      responseStartedTypingRef.current = false; // Reset flag
    }
  };

  // Stop current generation
  const stopGeneration = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setIsGenerating(false);
    setLoadingWithMinDuration(true); // Immediate when user stops
    setRequestInProgress(false);
    setIsTyping(false);
    setDisplayedBotText('');
    setShouldAnimate(false);
  };

  // Store sendMessage in a ref to avoid dependency issues  
  const sendMessageRef = useRef<((messageText?: string) => Promise<void>) | null>(null);

  // Handle suggestion button clicks with specific prompts
  const handleSuggestionClick = useCallback((suggestion: string) => {
    // Prevent clicking if already processing
    if (loading || requestInProgress || isGenerating) {
      return;
    }

    // CRITICAL: Set inbuilt query flag IMMEDIATELY and SYNCHRONOUSLY to prevent scrolling and blinking
    // Set ref FIRST (instant, before any other operations) - this prevents className from changing
    isInbuiltQueryRef.current = true;
    
    // Force the container to have full opacity IMMEDIATELY via DOM manipulation
    // This must happen BEFORE any state updates or React re-renders
    // Use both class and inline styles for maximum protection
    if (mainContainerRef.current) {
      // Add CSS class for !important override
      mainContainerRef.current.classList.add('chatbot-no-blink');
      // Also set inline styles with !important
      mainContainerRef.current.style.setProperty('opacity', '1', 'important');
      mainContainerRef.current.style.setProperty('transform', 'scale(1)', 'important');
      mainContainerRef.current.style.setProperty('transition', 'none', 'important');
    }
    
    // Also set state to prevent blinking (triggers re-render but opacity is already forced)
    setIsInbuiltQueryActive(true);
    
    // Re-apply in next frame to ensure it sticks even after React re-renders
    requestAnimationFrame(() => {
      if (mainContainerRef.current) {
        mainContainerRef.current.classList.add('chatbot-no-blink');
        mainContainerRef.current.style.setProperty('opacity', '1', 'important');
        mainContainerRef.current.style.setProperty('transform', 'scale(1)', 'important');
        mainContainerRef.current.style.setProperty('transition', 'none', 'important');
      }
    });
    
    // Also apply after a microtask to catch any delayed renders
    Promise.resolve().then(() => {
      if (mainContainerRef.current) {
        mainContainerRef.current.classList.add('chatbot-no-blink');
        mainContainerRef.current.style.setProperty('opacity', '1', 'important');
        mainContainerRef.current.style.setProperty('transform', 'scale(1)', 'important');
        mainContainerRef.current.style.setProperty('transition', 'none', 'important');
      }
    });
    
    // Remove the class when done (after 2 seconds to be safe)
    setTimeout(() => {
      if (mainContainerRef.current) {
        mainContainerRef.current.classList.remove('chatbot-no-blink');
      }
    }, 2000);

    // Create specific prompts for each suggestion type
    const suggestionPrompts: { [key: string]: string } = {
      "Help with homework": "I need help with my homework. Can you provide step-by-step guidance and explanations?",
      "Explain a concept": "Can you explain a concept in simple terms with examples? I'm looking for a clear understanding.",
      "Study tips": "What are some effective study tips and techniques that can help me learn better?",
      "School schedule": "Can you help me with information about school schedules, timetables, or academic planning?",
      "Assignment help": "I need assistance with an assignment. Can you guide me through the process and requirements?",
      "Math problems": "I have math problems that I need help solving. Can you provide solutions with explanations?",
      "Science questions": "I have science questions that need answering. Can you provide detailed scientific explanations?",
      "History facts": "I'm interested in learning about historical facts and events. Can you share some interesting information?",
      "Prakriti School info": "Tell me about Prakriti School - its philosophy, programs, and what makes it special.",
      "Progressive education": "What is progressive education and how does it differ from traditional education?",
      "Learning for happiness": "How does Prakriti School's 'learning for happiness' philosophy work in practice?",
      "IGCSE curriculum": "Can you explain the IGCSE curriculum offered at Prakriti School and its benefits?"
    };

    const prompt = suggestionPrompts[suggestion] || suggestion;
    
    console.log('🎯 Suggestion clicked:', suggestion, '→ Auto-sending prompt:', prompt);
    
    // CRITICAL: Save scroll position BEFORE any operations that might cause scrolling
    // Also check if user is at bottom - if so, we'll keep them at bottom
    const container = messagesContainerRef.current;
    const savedScrollPosition = container?.scrollTop || 0;
    const scrollHeight = container?.scrollHeight || 0;
    const clientHeight = container?.clientHeight || 0;
    const isAtBottom = scrollHeight - savedScrollPosition - clientHeight < 50; // Within 50px of bottom
    const shouldStayAtBottom = isAtBottom || savedScrollPosition === 0; // At bottom or at top
    
    // CRITICAL: Restore scroll position to prevent any scrolling
    // Use multiple attempts to ensure scroll position is preserved
    // If user was at bottom, keep them at bottom; otherwise restore exact position
    const restoreScroll = () => {
      if (messagesContainerRef.current) {
        if (shouldStayAtBottom && isAtBottom) {
          // User was at bottom - scroll to bottom
          messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        } else {
          // User was somewhere in the middle - restore exact position
          messagesContainerRef.current.scrollTop = savedScrollPosition;
        }
      }
    };
    
    // Immediate restoration
    requestAnimationFrame(restoreScroll);
    setTimeout(restoreScroll, 0);
    setTimeout(restoreScroll, 10);
    setTimeout(restoreScroll, 50);
    setTimeout(restoreScroll, 100);
    setTimeout(restoreScroll, 200);
    setTimeout(restoreScroll, 300);
    setTimeout(restoreScroll, 500);
    setTimeout(restoreScroll, 800);
    setTimeout(restoreScroll, 1000);
    
    // AUTO-SEND: Automatically send the message immediately (no input population)
    // Small delay to ensure all scroll/blink prevention is in place
    setTimeout(() => {
      // Only auto-send if not already processing
      if (!loading && !requestInProgress && !isGenerating) {
        console.log('🚀 Auto-sending inbuilt query:', prompt);
        // Use ref to call sendMessage - ref is updated immediately after sendMessage is defined
        if (sendMessageRef.current) {
          sendMessageRef.current(prompt);
        } else {
          console.error('❌ sendMessageRef.current is null - cannot send inbuilt query');
        }
      }
    }, 100); // Small delay to ensure scroll position is preserved
    
    // Reset inbuilt query flag after a delay to allow all operations to complete
    // This prevents any delayed scrolls or state changes
    setTimeout(() => {
      isInbuiltQueryRef.current = false;
      setIsInbuiltQueryActive(false);
      // Keep the no-blink class a bit longer to ensure no blinking
      setTimeout(() => {
        if (mainContainerRef.current) {
          mainContainerRef.current.classList.remove('chatbot-no-blink');
        }
      }, 500);
    }, 1500);
    
    // Call onQueryProcessed if provided (for external query handling)
    if (onQueryProcessed) {
      onQueryProcessed();
    }
  }, [loading, requestInProgress, isGenerating, onQueryProcessed]);

  // Handle external query from sidebar - using ref to avoid dependency issues
  const previousQueryRef = useRef<string>('');
  
  // Detect desktop for scrollbar hiding
  useEffect(() => {
    const checkDesktop = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    checkDesktop();
    window.addEventListener('resize', checkDesktop);
    return () => window.removeEventListener('resize', checkDesktop);
  }, []);

  // Apply webkit scrollbar hiding styles directly to the element
  useEffect(() => {
    if (messagesContainerRef.current && isDesktop) {
      const style = document.createElement('style');
      style.id = 'chatbot-scrollbar-hide';
      style.textContent = `
        #chatbot-messages-container::-webkit-scrollbar {
          display: none !important;
          width: 0 !important;
          height: 0 !important;
        }
        #chatbot-messages-container::-webkit-scrollbar-track {
          display: none !important;
        }
        #chatbot-messages-container::-webkit-scrollbar-thumb {
          display: none !important;
        }
      `;
      document.head.appendChild(style);
      messagesContainerRef.current.id = 'chatbot-messages-container';
      
      return () => {
        const existingStyle = document.getElementById('chatbot-scrollbar-hide');
        if (existingStyle) {
          existingStyle.remove();
        }
      };
    }
  }, [isDesktop]);

  useEffect(() => {
    if (externalQuery && externalQuery !== previousQueryRef.current && !loading && !requestInProgress && !isGenerating) {
      // Don't clear conversation history for guest users - they should maintain their session
      previousQueryRef.current = externalQuery;
      handleSuggestionClick(externalQuery);
      // No need to populate input - handleSuggestionClick now auto-sends directly
      if (onQueryProcessed) {
        setTimeout(() => {
          onQueryProcessed();
        }, 200);
      }
    }
  }, [externalQuery, loading, requestInProgress, isGenerating, user, conversationHistory.length, handleSuggestionClick, onQueryProcessed]);

  // Send message to backend /chatbot endpoint
  const sendMessage = async (messageText?: string) => {
    // Reset inbuilt query flag for all messages (inbuilt queries now behave like normal messages)
    // Since inbuilt queries are no longer auto-sent, they're treated as normal messages
    isInbuiltQueryRef.current = false;
    
    // Use provided messageText or fall back to input state
    const messageToSend = messageText || input;
    
    console.log('=== SEND MESSAGE FUNCTION START ===');
    console.log('Input:', messageToSend);
    console.log('Loading:', loading);
    console.log('RequestInProgress:', requestInProgress);
    
    if (!messageToSend.trim() || loading || requestInProgress) {
      console.log('Early return - input empty or already processing');
      return; // Prevent sending if already loading or request in progress
    }
    
    // Check if there's an active session
    let activeSession = getActiveSession();
    
    // CRITICAL: If no active session, check URL for existing session ID first (for guest users)
    // This prevents creating a new session when one already exists in the URL/localStorage
    if (!activeSession && !user) {
      console.log('⚠️ No active session found - checking URL for existing session ID');
      
      // Check if there's a session ID in the URL
      const urlParams = new URLSearchParams(window.location.search);
      const urlSessionId = urlParams.get('session');
      
      if (urlSessionId) {
        console.log('🔍 Found session ID in URL:', urlSessionId);
        
        // Try to load guest sessions from localStorage to find the session
        try {
          const guestData = localStorage.getItem('guest_chat_sessions');
          if (guestData) {
            const parsed = JSON.parse(guestData);
            const guestSessions = parsed.sessions || [];
            const urlSession = guestSessions.find((s: { id: string; messages?: Array<{ sender: string; text: string }> }) => s.id === urlSessionId);
            
            if (urlSession) {
              console.log('✅ Found session in localStorage, using it:', urlSessionId, {
                messagesCount: urlSession.messages.length
              });
              
              // Session exists in localStorage - ensure it's set as active
              // The session should already be loaded, but let's make sure
              // Wait a bit for the session to be loaded by ChatHistoryProvider
              await new Promise(resolve => setTimeout(resolve, 300));
              activeSession = getActiveSession();
              
              if (activeSession && activeSession.id === urlSessionId) {
                console.log('✅ Session loaded successfully from localStorage');
              } else {
                console.log('⚠️ Session not yet loaded, will be handled by addMessage fallback');
              }
            } else {
              console.log('⚠️ Session ID in URL not found in localStorage - will create new session');
            }
          }
        } catch (error) {
          console.error('Error checking localStorage for session:', error);
        }
      }
      
      // Only create a new session if we still don't have one
      if (!activeSession) {
        console.log('⚠️ No active session found after checking URL - creating one for guest user');
        try {
          // Create a new session for guest users
          await createNewSession();
          // Wait a bit longer for session to be fully created and saved
          await new Promise(resolve => setTimeout(resolve, 200));
          // Get the newly created session - retry a few times if needed
          let retries = 0;
          while (!activeSession && retries < 5) {
            activeSession = getActiveSession();
            if (!activeSession) {
              await new Promise(resolve => setTimeout(resolve, 100));
              retries++;
            }
          }
          if (activeSession) {
            console.log('✅ Session created successfully:', activeSession.id);
          } else {
            console.error('⚠️ Session creation completed but still no active session after retries');
            // Try one more time to get session
            activeSession = getActiveSession();
          }
        } catch (error) {
          console.error('Error creating session:', error);
          // Try to get session one more time
          activeSession = getActiveSession();
        }
      }
    } else if (!activeSession && user) {
      // For logged-in users, create a new session if none exists
      console.log('⚠️ No active session found - creating one for logged-in user');
      try {
        await createNewSession();
        await new Promise(resolve => setTimeout(resolve, 200));
        let retries = 0;
        while (!activeSession && retries < 5) {
          activeSession = getActiveSession();
          if (!activeSession) {
            await new Promise(resolve => setTimeout(resolve, 100));
            retries++;
          }
        }
        if (activeSession) {
          console.log('✅ Session created successfully:', activeSession.id);
        } else {
          activeSession = getActiveSession();
        }
      } catch (error) {
        console.error('Error creating session:', error);
        activeSession = getActiveSession();
      }
    }
    
    // If still no session, log error but continue (message will be shown but not saved)
    if (!activeSession) {
      console.error('❌ No active session available - message will not be saved to history');
    }
    
    console.log('Proceeding with message sending...', {
      hasActiveSession: !!activeSession,
      sessionId: activeSession?.id
    });
    const userMsg: Message = { sender: 'user', text: messageToSend };
    
    // CRITICAL: For inbuilt queries, add user message to state FIRST (like normal messages)
    // This ensures proper message order: user message appears first, then bot response
    // We still preserve scroll position to prevent unwanted scrolling
    if (isInbuiltQueryRef.current && messagesContainerRef.current) {
      const savedScrollPosition = messagesContainerRef.current.scrollTop;
      // Add user message to state immediately (like normal messages) to ensure proper order
      console.log('📝 Inbuilt query - adding user message to state first (like normal messages)');
      setMessages((msgs) => [...msgs, userMsg]);
      
      // CRITICAL: Restore scroll position to prevent any scrolling
      // Use multiple attempts to ensure scroll position is preserved
      requestAnimationFrame(() => {
        if (messagesContainerRef.current && savedScrollPosition > 0) {
          messagesContainerRef.current.scrollTop = savedScrollPosition;
        }
      });
      setTimeout(() => {
        if (messagesContainerRef.current && savedScrollPosition > 0) {
          messagesContainerRef.current.scrollTop = savedScrollPosition;
        }
      }, 0);
      setTimeout(() => {
        if (messagesContainerRef.current && savedScrollPosition > 0) {
          messagesContainerRef.current.scrollTop = savedScrollPosition;
        }
      }, 50);
      setTimeout(() => {
        if (messagesContainerRef.current && savedScrollPosition > 0) {
          messagesContainerRef.current.scrollTop = savedScrollPosition;
        }
      }, 100);
    } else {
      // Normal query - append at bottom immediately
      setMessages((msgs) => [...msgs, userMsg]);
    }
    
    
    // Add user message to chat history and wait for it to complete
    console.log('=== USER MESSAGE START ===');
    console.log('Adding user message to chat history...');
    console.log('User message text:', messageToSend);
    console.log('Active session:', activeSession ? { id: activeSession.id, messagesCount: activeSession.messages.length } : 'null');
    
    try {
      // Add message to chat history if we have an active session
      if (activeSession) {
        await addMessage({
          sender: 'user',
          text: messageToSend,
        });
        console.log('✅ User message added to chat history successfully');
        
        // Wait a bit for session to be updated in localStorage
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // Get fresh session after adding message to ensure we have the latest
        activeSession = getActiveSession();
      } else {
        console.error('❌ No active session available for adding message - message will not be persisted');
      }
    } catch (error) {
      console.error('❌ Error adding user message to chat history:', error);
    }
    
    console.log('=== USER MESSAGE END ===');
    
    // CRITICAL: Build conversation history from active session messages, not from state
    // This ensures we always have the complete, up-to-date history
    let conversationHistoryFromSession: Array<{role: string, content: string}> = [];
    if (activeSession && activeSession.messages.length > 0) {
      // Build history from session messages (most reliable source)
      // The session should now include the user message we just added
      conversationHistoryFromSession = activeSession.messages.map(msg => ({
        role: msg.sender === 'bot' ? 'assistant' : msg.sender,
        content: msg.text,
      }));
      console.log('📋 Building conversation history from session:', {
        sessionId: activeSession.id,
        messagesCount: activeSession.messages.length,
        historyLength: conversationHistoryFromSession.length,
        lastMessage: activeSession.messages[activeSession.messages.length - 1]?.text?.substring(0, 50) + '...'
      });
    } else {
      // Fallback to state if no session messages yet, and manually add user message
      conversationHistoryFromSession = conversationHistory;
      console.log('⚠️ No session messages, using state history:', conversationHistoryFromSession.length);
    }
    
    // If we have session messages, use them directly (they already include the user message)
    // Otherwise, add user message to the history
    const newHistory = activeSession && activeSession.messages.length > 0 
      ? conversationHistoryFromSession  // Session already has the user message
      : [...conversationHistoryFromSession, { role: 'user', content: messageToSend }];  // Add it manually
    setConversationHistory(newHistory);
    
    console.log('📤 Sending request with conversation history:', {
      historyLength: newHistory.length,
      lastMessage: newHistory[newHistory.length - 1]?.content?.substring(0, 50) + '...',
      messageToSend: messageToSend.substring(0, 50) + '...'
    });
    
    // Clear input AFTER building request data to ensure message is included
    setInput('');
    // Reset textarea height after clearing input
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.style.height = '50px';
      }
    }, 0);
    setLoading(true);
    setRequestInProgress(true);
    setIsGenerating(true);
    setDisplayedBotText('');
    setIsTyping(false);
    // Reset response started typing flag for new query
    responseStartedTypingRef.current = false;
    // Track when loading starts for minimum display duration
    loadingStartTimeRef.current = Date.now();
    setShowTypingAnimation(true);
    
    // Create abort controller for this request
    const controller = new AbortController();
    setAbortController(controller);
    
    // Show immediate loading feedback
    setTimeout(() => {
      if (loading) {
        setDisplayedBotText('Searching...');
        setIsTyping(true);
        setTypingAnimationKey(prev => prev + 1); // Retrigger animation
        setShouldAnimate(false); // Reset animation - start with blue
        // Delay to ensure DOM is ready, then trigger animation
        requestAnimationFrame(() => {
          setTimeout(() => setShouldAnimate(true), 50); // Trigger animation after a brief delay
        });
      }
    }, 100);
    
    try {
      // Check browser cache for web crawler data before making API call
      const { getCachedWebData, setCachedWebData, extractWebDataFromResponse } = await import('@/utils/webCrawlerCache');
      const cachedWebData = getCachedWebData(messageToSend); // Use messageToSend, not input
      
      // CRITICAL: Use messageToSend (the parameter) instead of input state
      // This ensures the message is included even if input was cleared
      const requestData = { 
        message: messageToSend, // Use the parameter, not input state
        conversation_history: newHistory,
        user_id: user?.id || null,
        user_profile: profile || null,  // Pass the complete user profile including gender
        cached_web_data: cachedWebData || null  // Send cached web data to backend if available
      };
      
      console.log('Chatbot sending request data:', JSON.stringify(requestData, null, 2));
      if (cachedWebData) {
        console.log('[Chatbot] 📦 Using cached web data from browser (fast response)');
      }
      
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        signal: controller.signal,
      });
      const data = await res.json();
      
      // After receiving response, cache web data if present
      const extractedWebData = extractWebDataFromResponse(input, data.response || '');
      if (extractedWebData) {
        setCachedWebData(input, extractedWebData);
      }
      
      // Check for structured responses with type field
      if (data.type === 'calendar' && data.response && data.response.url) {
        // Calculate delay to ensure minimum display duration for typing animation
        const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
        const elapsed = loadingStartTimeRef.current ? Date.now() - loadingStartTimeRef.current : 0;
        const delayBeforeShowing = Math.max(0, minDisplayDuration - elapsed);
        
        // Wait for minimum duration before showing the response
        await new Promise(resolve => setTimeout(resolve, delayBeforeShowing));
        
        const botMsg = { sender: 'bot' as const, type: 'calendar' as const, url: data.response.url };
        // For inbuilt queries, preserve scroll position when adding bot message
        if (isInbuiltQueryRef.current && messagesContainerRef.current) {
          const savedScrollPosition = messagesContainerRef.current.scrollTop;
          setMessages((msgs) => [...msgs, botMsg]);
          // Restore scroll position immediately after adding message
          requestAnimationFrame(() => {
            if (messagesContainerRef.current && savedScrollPosition > 0) {
              messagesContainerRef.current.scrollTop = savedScrollPosition;
            }
          });
        } else {
          setMessages((msgs) => [...msgs, botMsg]);
        }
        console.log('Adding bot calendar message to chat history...');
        await addMessage({
          sender: 'bot',
          text: data.response.url,
          type: 'calendar',
          url: data.response.url,
        });
        console.log('Bot calendar message added to chat history');
        setIsTyping(false);
        // Note: responseStartedTypingRef will be set inside hideTypingAnimationWithMinDuration after minimum duration
        hideTypingAnimationWithMinDuration();
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      } else if (data.type === 'map' && data.response && data.response.url) {
        // Calculate delay to ensure minimum display duration for typing animation
        const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
        const elapsed = loadingStartTimeRef.current ? Date.now() - loadingStartTimeRef.current : 0;
        const delayBeforeShowing = Math.max(0, minDisplayDuration - elapsed);
        
        // Wait for minimum duration before showing the response
        await new Promise(resolve => setTimeout(resolve, delayBeforeShowing));
        
        const botMsg = { sender: 'bot' as const, type: 'map' as const, url: data.response.url };
        // For inbuilt queries, preserve scroll position when adding bot message
        if (isInbuiltQueryRef.current && messagesContainerRef.current) {
          const savedScrollPosition = messagesContainerRef.current.scrollTop;
          setMessages((msgs) => [...msgs, botMsg]);
          // Restore scroll position immediately after adding message
          requestAnimationFrame(() => {
            if (messagesContainerRef.current && savedScrollPosition > 0) {
              messagesContainerRef.current.scrollTop = savedScrollPosition;
            }
          });
        } else {
          setMessages((msgs) => [...msgs, botMsg]);
        }
        await addMessage({
          sender: 'bot',
          text: data.response.url,
          type: 'map',
          url: data.response.url,
        });
        setIsTyping(false);
        // Note: responseStartedTypingRef will be set inside hideTypingAnimationWithMinDuration after minimum duration
        hideTypingAnimationWithMinDuration();
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      } else if (data.type === 'mixed' && Array.isArray(data.response)) {
        // Calculate delay to ensure minimum display duration for typing animation
        const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
        const elapsed = loadingStartTimeRef.current ? Date.now() - loadingStartTimeRef.current : 0;
        const delayBeforeShowing = Math.max(0, minDisplayDuration - elapsed);
        
        // Wait for minimum duration before showing the response
        await new Promise(resolve => setTimeout(resolve, delayBeforeShowing));
        
        // Handle mixed responses (like location with map or videos)
        const messages_to_add = [{ sender: 'bot', text: data.response[0] } as Message];
        
        if (data.response[1]?.type === 'map') {
          messages_to_add.push({ sender: 'bot', type: 'map', url: data.response[1].url } as Message);
        } else if (data.response[1]?.type === 'videos') {
          messages_to_add.push({ sender: 'bot', type: 'videos', videos: data.response[1].videos } as Message);
        }
        
        // For inbuilt queries, preserve scroll position when adding bot messages
        if (isInbuiltQueryRef.current && messagesContainerRef.current) {
          const savedScrollPosition = messagesContainerRef.current.scrollTop;
          setMessages((msgs) => [...msgs, ...messages_to_add]);
          // Restore scroll position immediately after adding messages
          requestAnimationFrame(() => {
            if (messagesContainerRef.current && savedScrollPosition > 0) {
              messagesContainerRef.current.scrollTop = savedScrollPosition;
            }
          });
        } else {
          setMessages((msgs) => [...msgs, ...messages_to_add]);
        }
        setIsTyping(false);
        // Note: responseStartedTypingRef will be set inside hideTypingAnimationWithMinDuration after minimum duration
        hideTypingAnimationWithMinDuration();
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      } else if (data.type === 'videos' && data.response && data.response.videos) {
        // Calculate delay to ensure minimum display duration for typing animation
        const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
        const elapsed = loadingStartTimeRef.current ? Date.now() - loadingStartTimeRef.current : 0;
        const delayBeforeShowing = Math.max(0, minDisplayDuration - elapsed);
        
        // Wait for minimum duration before showing the response
        await new Promise(resolve => setTimeout(resolve, delayBeforeShowing));
        
        // Handle video responses
        const botMsg = { sender: 'bot' as const, type: 'videos' as const, videos: data.response.videos };
        // For inbuilt queries, preserve scroll position when adding bot message
        if (isInbuiltQueryRef.current && messagesContainerRef.current) {
          const savedScrollPosition = messagesContainerRef.current.scrollTop;
          setMessages((msgs) => [...msgs, botMsg]);
          // Restore scroll position immediately after adding message
          requestAnimationFrame(() => {
            if (messagesContainerRef.current && savedScrollPosition > 0) {
              messagesContainerRef.current.scrollTop = savedScrollPosition;
            }
          });
        } else {
          setMessages((msgs) => [...msgs, botMsg]);
        }
        await addMessage({
          sender: 'bot',
          text: JSON.stringify(data.response.videos),
          type: 'videos',
          videos: data.response.videos,
        });
        setIsTyping(false);
        // Note: responseStartedTypingRef will be set inside hideTypingAnimationWithMinDuration after minimum duration
        hideTypingAnimationWithMinDuration();
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      }
      
      // Handle regular text responses (including Markdown)
      const fullText = data.response;
      console.log('Frontend received response length:', fullText?.length);
      console.log('Frontend received response:', fullText);
      console.log('About to start word-by-word typing animation...');
      
      // Add bot response to conversation history
      setConversationHistory(prev => [...prev, { role: 'assistant', content: fullText }]);
      
      // Calculate delay to ensure minimum display duration for typing animation
      const minDisplayDuration = 3500; // 3.5 seconds (middle of 3-4 range)
      const elapsed = loadingStartTimeRef.current ? Date.now() - loadingStartTimeRef.current : 0;
      const delayBeforeTyping = Math.max(0, minDisplayDuration - elapsed);
      
      // Wait for minimum duration before starting to type
      await new Promise(resolve => setTimeout(resolve, delayBeforeTyping));
      
      // Now start typing the response (paragraph by paragraph)
      const paragraphs = fullText.split('\n\n').filter((p: string) => p.trim());
      console.log('Paragraphs array created:', paragraphs);
      console.log('Total paragraphs to type:', paragraphs.length);
      let paragraphIdx = 0;
      setIsTyping(true);
      // Hide typing animation when response starts typing, but respect minimum duration
      // Note: responseStartedTypingRef will be set inside hideTypingAnimationWithMinDuration after minimum duration
      hideTypingAnimationWithMinDuration();
      setTypingAnimationKey(prev => prev + 1); // Retrigger animation
      setShouldAnimate(false); // Reset animation - start with blue
      // Delay to ensure DOM is ready, then trigger animation
      requestAnimationFrame(() => {
        setTimeout(() => setShouldAnimate(true), 50); // Trigger animation after a brief delay
      });

      // Start the paragraph-by-paragraph typing animation
      async function typeParagraph() {
        // Show text up to the end of the current paragraph
        const textUpToParagraph = paragraphs.slice(0, paragraphIdx + 1).join('\n\n');
        console.log(`Typing paragraph ${paragraphIdx + 1}/${paragraphs.length}: "${textUpToParagraph.substring(0, 50)}..."`);
        setDisplayedBotText(textUpToParagraph);
        if (paragraphIdx < paragraphs.length - 1) {
          paragraphIdx++;
          setTimeout(typeParagraph, 800); // faster speed - 800ms per paragraph
        } else {
          console.log('Typing animation completed');
          setIsTyping(false);

          // Now add the complete bot message to the messages array
          const botMsg: Message = { sender: 'bot', text: fullText };

          if (isInbuiltQueryRef.current && messagesContainerRef.current) {
            const savedScrollPosition = messagesContainerRef.current.scrollTop;
            // Append bot message after user message (correct order)
            setMessages((msgs) => [...msgs, botMsg]);
            // Restore scroll position immediately after adding message
            requestAnimationFrame(() => {
              if (messagesContainerRef.current && savedScrollPosition > 0) {
                messagesContainerRef.current.scrollTop = savedScrollPosition;
              }
            });
            setTimeout(() => {
              if (messagesContainerRef.current && savedScrollPosition > 0) {
                messagesContainerRef.current.scrollTop = savedScrollPosition;
              }
            }, 0);
            setTimeout(() => {
              if (messagesContainerRef.current && savedScrollPosition > 0) {
                messagesContainerRef.current.scrollTop = savedScrollPosition;
              }
            }, 50);
          } else {
            setMessages((msgs) => [...msgs, botMsg]);
          }

          // Add to chat history
          console.log('=== BOT MESSAGE START ===');
          console.log('Adding bot text message to chat history...');
          console.log('Bot message text:', fullText.substring(0, 50) + '...');

          await addMessage({
            sender: 'bot',
            text: fullText,
          });

          console.log('✅ Bot text message added to chat history and saved to localStorage');
          console.log('=== BOT MESSAGE END ===');

          // CRITICAL: Force a small delay to ensure localStorage is updated, then trigger sync
          // This ensures the useEffect picks up the new message count
          await new Promise(resolve => setTimeout(resolve, 100));

          // Get fresh session to verify message was saved
          const freshSession = getActiveSession();
          if (freshSession) {
            console.log('✅ Verified bot message in session:', {
              sessionId: freshSession.id,
              messagesCount: freshSession.messages.length,
              lastMessage: freshSession.messages[freshSession.messages.length - 1]?.text?.substring(0, 50) + '...'
            });
          }

          // Mark that we've had the first response
          setHasFirstResponse(true);

          // Clear the displayed bot text since the message is now in the messages array
          setDisplayedBotText('');
        }
      }

      // Start the typing animation
      typeParagraph();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Request was aborted, don't add error message
        console.log('Request aborted by user');
      } else {
        setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Error: Could not get response.' }]);
        setHasFirstResponse(true);
      }
    } finally {
      setLoadingWithMinDuration();
      setRequestInProgress(false);
      setIsGenerating(false);
      setAbortController(null);
    }
  };

  // Keep sendMessage ref updated - update immediately after sendMessage is defined
  // This ensures the ref is always available when handleSuggestionClick needs it
  sendMessageRef.current = sendMessage;

  // Auto-resize textarea based on content
  const adjustTextareaHeight = useCallback(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      const scrollHeight = inputRef.current.scrollHeight;
      const minHeight = 50;
      const maxHeight = 200; // Increased from 120px for better expansion
      const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
      inputRef.current.style.height = `${newHeight}px`;
      
      // Enable scrolling if content exceeds maxHeight
      if (scrollHeight > maxHeight) {
        inputRef.current.style.overflowY = 'auto';
      } else {
        inputRef.current.style.overflowY = 'hidden';
      }
    }
  }, []);

  // Adjust textarea height when input changes
  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  // Handle Enter + Shift for newline, Enter for send
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      console.log('=== HANDLE KEY DOWN ===');
      console.log('isGenerating:', isGenerating);
      console.log('isTyping:', isTyping);
      console.log('loading:', loading);
      console.log('requestInProgress:', requestInProgress);
      
      if (isGenerating || isTyping) {
        console.log('Stopping generation...');
        stopGeneration();
      } else if (!loading && !requestInProgress) {
        console.log('Calling sendMessage...');
        sendMessage();
      } else {
        console.log('Not calling sendMessage - loading or request in progress');
      }
    }
    // Adjust height on Enter key as well (for Shift+Enter)
    setTimeout(() => adjustTextareaHeight(), 0);
  };

  // Auto-scroll to bottom when messages change or when typing
  // CRITICAL: For inbuilt queries, NEVER scroll - just add message at bottom
  // Only scroll for manual messages if user is near bottom
  useEffect(() => {
    // CRITICAL: If this is an inbuilt query, NEVER scroll - preserve user's current view
    // Check the ref at the start AND before any scroll operations
    if (isInbuiltQueryRef.current || isInbuiltQueryActive) {
      console.log('🚫 Auto-scroll blocked - inbuilt query in progress');
      // If user was at bottom, keep them at bottom
      if (messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;
        const scrollTop = container.scrollTop;
        // If user is near bottom (within 100px), keep them at bottom
        if (scrollHeight - scrollTop - clientHeight < 100) {
          container.scrollTop = scrollHeight;
        }
      }
      return; // Exit early - don't scroll at all for inbuilt queries
    }
    
    const shouldScroll = () => {
      // Double-check inbuilt query flag before scrolling
      if (isInbuiltQueryRef.current || isInbuiltQueryActive) {
        console.log('🚫 Should scroll check blocked - inbuilt query in progress');
        return false;
      }
      
      // Always scroll if there are few messages (new conversation)
      if (messages.length < 10) {
        return true;
      }
      
      // Check if user is near bottom of scroll container
      if (messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        const scrollTop = container.scrollTop;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
        
        // Only scroll if user is within 200px of bottom (already viewing recent messages)
        return distanceFromBottom < 200;
      }
      
      // Default to scrolling if container ref not available
      return true;
    };
    
    // Final check before any scroll operations
    if (isInbuiltQueryRef.current || isInbuiltQueryActive) {
      console.log('🚫 Scroll operation blocked - inbuilt query in progress');
      // If user was at bottom, keep them at bottom
      if (messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;
        const scrollTop = container.scrollTop;
        // If user is near bottom (within 100px), keep them at bottom
        if (scrollHeight - scrollTop - clientHeight < 100) {
          container.scrollTop = scrollHeight;
        }
      }
      return;
    }
    
    if (isTyping && typingRef.current) {
      // Only scroll to typing text if user is near bottom
      if (shouldScroll()) {
        setTimeout(() => {
          // Check again before scrolling
          if (!isInbuiltQueryRef.current) {
            typingRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }
        }, 50);
      }
    } else if (shouldScroll()) {
      // Scroll to bottom for regular messages only if should scroll
      // Check again before scrolling
      if (!isInbuiltQueryRef.current) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [messages, loading, isTyping, displayedBotText, isInbuiltQueryActive]);

  // Auto-focus textarea when messages change, unless user clicked elsewhere
  // BUT: Don't interfere if input has value (preserve inbuilt query input)
  // CRITICAL: Don't focus when inbuilt query is active (prevents scrolling)
  useEffect(() => {
    // Skip if inbuilt query is active
    if (isInbuiltQueryRef.current) {
      return;
    }
    
    // Only focus if the active element is not an input, textarea, or contenteditable
    const active = document.activeElement;
    if (
      inputRef.current &&
      (!active || (
        active.tagName !== 'TEXTAREA' &&
        active.tagName !== 'INPUT' &&
        !(active instanceof HTMLElement && active.isContentEditable)
      ))
    ) {
      // Don't focus if input has value (preserve inbuilt query input)
      // Only focus if input is empty
      if (!inputRef.current.value && !input) {
        inputRef.current.focus({ preventScroll: true });
      }
    }
  }, [messages, input]);

  // Track last loaded session ID to prevent unnecessary reloads
  const lastLoadedSessionIdRef = useRef<string | null>(null);
  
  // Load messages from active session (optimized to prevent blinking)
  useEffect(() => {
    // Skip if still loading to prevent blinking
    if (chatHistoryLoading) {
      return;
    }
    
    // CRITICAL: For inbuilt queries, we need to handle sync differently
    // Don't skip entirely - we need to load existing messages, but prevent replacement
    // The actual append logic is handled in the sync block below
    
    // CRITICAL: Check for active session using getActiveSession() first (uses refs, always up-to-date)
    // Don't rely solely on activeSessionId state which might be null due to timing issues
    const activeSession = getActiveSession();
    
    console.log('🔄 useEffect triggered - loading messages from active session', {
      activeSessionId,
      activeSessionFromGet: activeSession?.id,
      isGuest: !user,
      chatHistoryLoading,
      messagesCount: messages.length
    });
    
    console.log('📋 Active session:', activeSession ? {
      id: activeSession.id,
      messagesCount: activeSession.messages.length,
      messages: activeSession.messages.map(m => ({ sender: m.sender, text: m.text.substring(0, 50) + '...' }))
    } : 'null');
    
    // CRITICAL: If we have an active session (from refs), load messages even if state is null
    // This fixes the issue where state is null but ref has the correct value
    if (!activeSession) {
      // CRITICAL: On page refresh, wait a bit for session to load from localStorage
      // Don't clear messages immediately - session might still be loading
      if (lastLoadedSessionIdRef.current !== null) {
        // We had a session before, but now it's gone - might be loading
        // Wait a bit and check again before clearing
        console.log('⚠️ No active session found - waiting for session to load...');
        setTimeout(() => {
          const retrySession = getActiveSession();
          if (!retrySession && lastLoadedSessionIdRef.current !== null) {
            console.log('❌ No active session after retry - clearing messages');
            lastLoadedSessionIdRef.current = null;
            setMessages([]);
            setConversationHistory([]);
            setHasFirstResponse(false);
          }
        }, 500);
      }
      return;
    }
    
    // Use requestAnimationFrame to batch state updates and prevent blinking
    // activeSession is guaranteed to exist here (we checked above)
    requestAnimationFrame(() => {
      if (activeSession) {
        const sessionMessages: Message[] = activeSession.messages.map(msg => ({
          sender: msg.sender,
          text: msg.text,
          ...(msg.type && { type: msg.type }),
          ...(msg.url && { url: msg.url }),
          ...(msg.videos && { videos: msg.videos }),
        }));
        console.log('📝 Checking session messages:', sessionMessages.length, 'messages', {
          sessionId: activeSession.id,
          isGuest: !user,
          currentMessagesCount: messages.length,
          lastLoadedSessionId: lastLoadedSessionIdRef.current,
          activeSessionMessageCount,
          sessionHasMessages: sessionMessages.length > 0,
          currentIsEmpty: messages.length === 0
        });
        
        // CRITICAL: Check if this is an inbuilt query FIRST
        // This ensures we always append instead of replace for inbuilt queries
        const isInbuiltQuery = isInbuiltQueryRef.current;
        
        // CRITICAL: Only update messages if:
        // 1. This is the first load (lastLoadedSessionIdRef is null) - BUT skip for inbuilt queries
        // 2. Session ID changed (switched to different session)
        // 3. Session has more messages than current state (session was updated - new messages added)
        // 4. Session message count changed (activeSessionMessageCount dependency triggered this)
        // 5. Session has messages but UI is empty (page refresh scenario) - MOST IMPORTANT FOR GUEST USERS
        // This prevents overwriting messages that are being added in real-time via setMessages
        const isFirstLoad = lastLoadedSessionIdRef.current === null;
        const isSessionChanged = lastLoadedSessionIdRef.current !== activeSession.id;
        const hasMoreMessages = sessionMessages.length > messages.length;
        const sessionCountChanged = sessionMessages.length !== messages.length; // Session count is different from UI count
        const isEmptyButSessionHasMessages = messages.length === 0 && sessionMessages.length > 0; // Page refresh - load from session
        // CRITICAL: Always sync if session has messages and UI is empty (page refresh scenario)
        // This ensures messages are loaded on refresh even if other conditions aren't met
        // BUT: For inbuilt queries, we'll handle it differently (append instead of replace)
        // Exclude inbuilt queries from sync conditions that would cause replacement
        const shouldSyncFromSession = (!isInbuiltQuery && isFirstLoad) || 
                                      (!isInbuiltQuery && isSessionChanged) || 
                                      (!isInbuiltQuery && hasMoreMessages && messages.length === 0) || // Only sync if no messages exist
                                      (isInbuiltQuery && messages.length === 0 && sessionMessages.length > 0) || // Allow initial load for inbuilt
                                      (!isInbuiltQuery && sessionCountChanged) || 
                                      isEmptyButSessionHasMessages || 
                                      (!isInbuiltQuery && sessionMessages.length > 0 && messages.length === 0);
        
        console.log('🔍 Sync decision:', {
          isInbuiltQuery,
          isFirstLoad,
          isSessionChanged,
          hasMoreMessages,
          sessionCountChanged,
          isEmptyButSessionHasMessages,
          shouldSyncFromSession,
          sessionMessagesCount: sessionMessages.length,
          currentMessagesCount: messages.length
        });
        
        if (shouldSyncFromSession) {
          console.log('✅ Syncing messages from session to state', {
            reason: isFirstLoad ? 'first load' : isSessionChanged ? 'session changed' : hasMoreMessages ? 'session has more messages' : isEmptyButSessionHasMessages ? 'page refresh - loading from session' : 'session count changed',
            sessionMessagesCount: sessionMessages.length,
            currentMessagesCount: messages.length,
            activeSessionMessageCount
          });
          
          // CRITICAL: For inbuilt queries, ALWAYS append new messages instead of replacing all
          // This prevents messages from appearing at the top - they stay at the bottom
          // Check isInbuiltQuery FIRST (we already checked it above, but check ref again to be sure)
          const isInbuiltQueryNow = isInbuiltQueryRef.current;
          if (isInbuiltQuery || isInbuiltQueryNow) {
            console.log('📝 Inbuilt query detected - appending new messages instead of replacing', {
              isInbuiltQuery,
              isInbuiltQueryNow,
              messagesCount: messages.length,
              sessionMessagesCount: sessionMessages.length
            });
            
            // CRITICAL: Always append new messages, never replace
            // For inbuilt queries, we need to be careful:
            // - If state has messages, append new ones from session
            // - If state is empty but session has messages, it means we just added a message
            //   and the state update hasn't propagated yet, OR the session has old messages
            //   In this case, we should use session messages (they're the source of truth)
            //   but we need to ensure we don't lose any messages that were just added
            if (messages.length > 0) {
              // Find messages that are in session but not in current state
              // Compare by text content, sender, and type to identify new messages
              // Use a more robust comparison that handles message order
              const currentMessageKeys = new Set(
                messages.map((m) => {
                  const text = 'text' in m ? (m.text || '').substring(0, 200) : '';
                  const type = 'type' in m ? (m.type || '') : '';
                  const url = 'url' in m ? (m.url || '').substring(0, 100) : '';
                  // Create a unique key for each message
                  return `${m.sender}-${text}-${type}-${url}`;
                })
              );
              
              // Find messages in session that don't exist in current state
              const newMessages = sessionMessages.filter((msg) => {
                const text = 'text' in msg ? (msg.text || '').substring(0, 200) : '';
                const type = 'type' in msg ? (msg.type || '') : '';
                const url = 'url' in msg ? (msg.url || '').substring(0, 100) : '';
                const msgKey = `${msg.sender}-${text}-${type}-${url}`;
                const isNew = !currentMessageKeys.has(msgKey);
                if (isNew) {
                  console.log('📝 Found new message to append:', {
                    sender: msg.sender,
                    textPreview: text.substring(0, 50),
                    type
                  });
                }
                return isNew;
              });
              
              if (newMessages.length > 0) {
                console.log('📝 Appending', newMessages.length, 'new messages at bottom (inbuilt query)');
                // CRITICAL: For inbuilt queries, user message is already in state
                // Only append bot messages that aren't already in state
                // Filter out user messages since they're already added
                const botMessagesOnly = newMessages.filter(msg => msg.sender === 'bot');
                
                if (botMessagesOnly.length > 0) {
                  // Save scroll position before updating messages
                  const savedScrollPosition = messagesContainerRef.current?.scrollTop || 0;
                  
                  // CRITICAL: Temporarily disable auto-scroll by ensuring flag is set
                  // This prevents the auto-scroll useEffect from running
                  const wasInbuiltQuery = isInbuiltQueryRef.current;
                  if (!wasInbuiltQuery) {
                    isInbuiltQueryRef.current = true;
                  }
                  
                  // Append only bot messages at the bottom - user message is already in state
                  setMessages((msgs) => {
                    const combined = [...msgs, ...botMessagesOnly];
                    console.log('📝 Combined messages (inbuilt query - bot only):', {
                      previousCount: msgs.length,
                      newCount: combined.length,
                      appended: botMessagesOnly.length
                    });
                    return combined;
                  });
                  
                  // CRITICAL: Restore scroll position after messages are added
                  // Use multiple attempts with increasing delays to ensure scroll position is preserved
                  // This handles React's render cycle and DOM updates
                  const restoreScroll = () => {
                    if (messagesContainerRef.current && savedScrollPosition > 0) {
                      messagesContainerRef.current.scrollTop = savedScrollPosition;
                      console.log('📍 Restored scroll position:', savedScrollPosition);
                    }
                  };
                  
                  // Immediate restoration
                  requestAnimationFrame(restoreScroll);
                  // After render
                  setTimeout(restoreScroll, 0);
                  // After layout
                  setTimeout(restoreScroll, 10);
                  setTimeout(restoreScroll, 50);
                  setTimeout(restoreScroll, 100);
                  setTimeout(restoreScroll, 200);
                  
                  // Restore flag if it wasn't set before
                  if (!wasInbuiltQuery) {
                    // Keep it set for a bit longer to prevent any delayed scrolls
                    setTimeout(() => {
                      isInbuiltQueryRef.current = false;
                    }, 500);
                  }
                } else {
                  console.log('📝 No new bot messages to append (inbuilt query - user message already in state)');
                }
              } else {
                console.log('📝 No new messages to append (inbuilt query)');
              }
            } else {
              // No existing messages in state
              // This could mean:
              // 1. State is truly empty (first load)
              // 2. State update hasn't propagated yet (race condition)
              // For inbuilt queries, if state is empty but session has messages,
              // we should use session messages (they're the source of truth)
              // The session already includes the user message we just added
              console.log('📝 No messages in state for inbuilt query - loading from session:', {
                sessionMessagesCount: sessionMessages.length,
                currentMessagesCount: messages.length,
                note: 'Session is source of truth, includes user message just added'
              });
              
              // Save scroll position before loading messages
              const savedScrollPosition = messagesContainerRef.current?.scrollTop || 0;
              
              // CRITICAL: Ensure inbuilt query flag is set to prevent auto-scroll
              const wasInbuiltQuery = isInbuiltQueryRef.current;
              if (!wasInbuiltQuery) {
                isInbuiltQueryRef.current = true;
              }
              
              // Use session messages - they're the authoritative source
              // The session already has the user message that was just added
              if (sessionMessages.length > 0) {
                console.log('📝 Setting messages from session (inbuilt query, empty state):', sessionMessages.length);
                setMessages(sessionMessages);
                
                // CRITICAL: Restore scroll position after messages are loaded
                // Use multiple attempts with increasing delays to ensure scroll position is preserved
                const restoreScroll = () => {
                  if (messagesContainerRef.current && savedScrollPosition > 0) {
                    messagesContainerRef.current.scrollTop = savedScrollPosition;
                    console.log('📍 Restored scroll position (empty state):', savedScrollPosition);
                  }
                };
                
                // Immediate restoration
                requestAnimationFrame(restoreScroll);
                // After render
                setTimeout(restoreScroll, 0);
                // After layout
                setTimeout(restoreScroll, 10);
                setTimeout(restoreScroll, 50);
                setTimeout(restoreScroll, 100);
                setTimeout(restoreScroll, 200);
                
                // Restore flag if it wasn't set before
                if (!wasInbuiltQuery) {
                  // Keep it set for a bit longer to prevent any delayed scrolls
                  setTimeout(() => {
                    isInbuiltQueryRef.current = false;
                  }, 500);
                }
              }
              // Mark that we've loaded so we don't replace again
              lastLoadedSessionIdRef.current = activeSession.id;
            }
            
            // Update ref to track loaded session
            lastLoadedSessionIdRef.current = activeSession.id;
            return; // Exit early - don't replace all messages
          }
          
          // CRITICAL: Always use session messages as source of truth (same as logged-in users)
          // Session messages are the authoritative source - they're saved to localStorage immediately
          // NEVER replace messages - always use session messages to ensure persistence
          // This prevents messages from being replaced when state is out of sync
          const messagesToSet = sessionMessages;
          
          console.log('📋 Setting messages from session (source of truth):', {
            sessionMessagesCount: sessionMessages.length,
            currentMessagesCount: messages.length,
            willSync: true
          });
          
          // Update ref to track loaded session BEFORE state updates
          lastLoadedSessionIdRef.current = activeSession.id;
          
          // Batch all state updates together to prevent intermediate renders
          setMessages(messagesToSet);
          
          // Check if there are any bot messages to set hasFirstResponse
          const hasBotMessages = messagesToSet.some(msg => msg.sender === 'bot');
          setHasFirstResponse(hasBotMessages);
          
          // Update conversation history for API calls - use merged messages
          // Only include messages that have text content (exclude calendar, map, videos)
          const history = messagesToSet
            .filter((msg): msg is { sender: 'user' | 'bot'; text: string } => 'text' in msg)
            .map(msg => ({
              role: msg.sender === 'bot' ? 'assistant' : msg.sender,
              content: msg.text,
            }));
          setConversationHistory(history);
          
          // Scroll to bottom on initial load/refresh (when loading messages from session)
          // Only if this is a fresh load (first time loading this session)
          if (isFirstLoad || isEmptyButSessionHasMessages) {
            // Use setTimeout to ensure DOM is updated before scrolling
            setTimeout(() => {
              if (messagesEndRef.current) {
                messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
              }
            }, 100);
          }
        } else {
          console.log('⏭️ Skipping sync - messages are up to date or being updated in real-time', {
            sessionMessagesCount: sessionMessages.length,
            currentMessagesCount: messages.length,
            sessionId: activeSession.id,
            lastLoadedSessionId: lastLoadedSessionIdRef.current,
            isFirstLoad,
            isSessionChanged,
            hasMoreMessages,
            sessionCountChanged,
            isEmptyButSessionHasMessages
          });
          // Still update the ref to track that we've seen this session (if it changed)
          if (isSessionChanged) {
            lastLoadedSessionIdRef.current = activeSession.id;
          }
        }
      }
    });
  }, [activeSessionId, getActiveSession, chatHistoryLoading, user, activeSessionMessageCount, messages]); // Include activeSessionMessageCount to detect when session messages are added

  // Listen for custom refresh event
  useEffect(() => {
    const handleRefreshEvent = () => {
      console.log('🔄 Custom refresh event received - refreshing chat components');
      refreshChatComponents();
    };

    window.addEventListener('refreshChatComponents', handleRefreshEvent);
    return () => window.removeEventListener('refreshChatComponents', handleRefreshEvent);
  }, [refreshChatComponents]);

  // For copy feedback per message
  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1200);
  };

  // Clear chat function
  const handleClearChat = useCallback(() => {
    // Stop any ongoing generation
    if (abortController) {
      abortController.abort();
    }
    setMessages([]);
    setInput('');
    setLoadingWithMinDuration(true); // Immediate when clearing
    setRequestInProgress(false);
    setIsGenerating(false);
    setAbortController(null);
    setListening(false);
    setDisplayedBotText('');
    setIsTyping(false);
    setShouldAnimate(false);
    setCopiedIdx(null);
    setHasFirstResponse(false);
    
    // Clear conversation history
    setConversationHistory([]);
    
    // Clear active session in chat history
    clearActiveSession();
    
    // Generate a new random welcome message
    setWelcomeMessage(getRandomWelcomeMessage());
    
    // Show cleared message briefly
    setShowClearedMessage(true);
    setTimeout(() => setShowClearedMessage(false), 2000);
    
    // Call parent clearChat function if provided
    if (clearChat) {
      clearChat();
    }
  }, [clearChat, getRandomWelcomeMessage, clearActiveSession, abortController, setCopiedIdx]);


  // Expose clearChat function to parent
  React.useImperativeHandle(ref, () => ({
    clearChat: handleClearChat
  }), [handleClearChat]);

  // Prevent blinking by only showing loading state on the very first app load, not on user changes
  const [hasShownInitialLoad, setHasShownInitialLoad] = useState(false);
  const previousUserRef = useRef<string | null>(null);
  
  // Clear messages when user logs out or changes
  useEffect(() => {
    const currentUserId = user?.id || null;
    const previousUserId = previousUserRef.current;
    
    // If user changed (login/logout), clear messages and reset everything
    if (currentUserId !== previousUserId) {
      // If user logged out (had a user, now no user), clear everything immediately
      if (previousUserId && !currentUserId) {
        console.log('🚪 User logged out - clearing chat messages');
        // Stop any ongoing generation
        if (abortController) {
          abortController.abort();
        }
        // Clear all messages and state
        setMessages([]);
        setInput('');
        setLoadingWithMinDuration(true); // Immediate when clearing
        setRequestInProgress(false);
        setIsGenerating(false);
        setAbortController(null);
        setListening(false);
        setDisplayedBotText('');
        setIsTyping(false);
        setCopiedIdx(null);
        setHasFirstResponse(false);
        setConversationHistory([]);
        // Generate a new random welcome message
        setWelcomeMessage(getRandomWelcomeMessage());
      }
      
      // If user logged in (new user or different user), clear messages to prevent showing old chat
      // Note: User's saved sessions from Supabase will be loaded automatically by ChatHistoryProvider
      if (currentUserId && currentUserId !== previousUserId) {
        console.log('🚪 User logged in - clearing UI state (will load saved sessions from Supabase)');
        setMessages([]);
        setConversationHistory([]);
        setInput('');
        setDisplayedBotText('');
        setIsTyping(false);
        // Generate a new random welcome message
        setWelcomeMessage(getRandomWelcomeMessage());
      }
      
      previousUserRef.current = currentUserId;
      // Reset last loaded session ID when user changes
      lastLoadedSessionIdRef.current = null;
    }
    
    // Mark that we've completed initial load once
    if (!chatHistoryLoading && !hasShownInitialLoad) {
      setHasShownInitialLoad(true);
    }
  }, [chatHistoryLoading, hasShownInitialLoad, user?.id, abortController, getRandomWelcomeMessage, setCopiedIdx]);
  
  // Only show loading opacity on the very first app load, never again (even on login/logout)
  // CRITICAL: Don't show loading opacity when inbuilt query is active (prevents blinking)
  // Always use full opacity if inbuilt query ref is set (even before state updates)
  const shouldShowLoading = chatHistoryLoading && !hasShownInitialLoad && !isInbuiltQueryActive && !isInbuiltQueryRef.current;
  const containerClassName = shouldShowLoading ? 'opacity-40 scale-[0.98]' : 'opacity-100 scale-100';
  
  // Check if we have an active session with messages to prevent welcome screen from showing
  const activeSession = getActiveSession();
  const hasActiveSessionWithMessages = activeSession?.messages && activeSession.messages.length > 0;
  
  return (
    <div 
      ref={mainContainerRef}
      className={`flex flex-col h-full w-full bg-transparent mx-auto ${isInbuiltQueryActive || isInbuiltQueryRef.current ? 'chatbot-no-blink' : 'transition-all duration-200'} ${containerClassName}`}
      style={(isInbuiltQueryActive || isInbuiltQueryRef.current) ? { 
        opacity: 1, 
        transform: 'scale(1)', 
        transition: 'none',
      } : undefined}
    >
      {messages.length === 0 && !hasActiveSessionWithMessages ? (
        <>
          {/* Welcome Screen - Mobile Optimized Layout */}
          <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
            {/* Spacer at top - reduced for mobile */}
            <div className="flex-shrink-0 pt-10 sm:pt-14 md:pt-20"></div>
            
            {/* Centered Content: Logo and Message - Scrollable if needed */}
            <div className="flex-1 flex flex-col items-center justify-center px-3 sm:px-4 md:px-6 min-h-0 overflow-y-auto">
              {/* Logo - Smaller on mobile */}
              <div className="flex justify-center mb-3 sm:mb-4 md:mb-6 flex-shrink-0">
                <Image 
                  src="/prakriti_logo.webp" 
                  alt="Prakriti Visual" 
                  width={128}
                  height={128}
                  className="w-20 h-20 sm:w-24 sm:h-24 md:w-28 md:h-28 lg:w-32 lg:h-32 object-contain" 
                />
              </div>
              {/* Welcome Message - Smaller on mobile */}
              <div className="text-center px-2 sm:px-4 mb-3 sm:mb-4 md:mb-6 flex-shrink-0">
                <h2 className="text-lg sm:text-xl md:text-2xl lg:text-3xl xl:text-4xl font-normal leading-tight text-gray-600">
                  {welcomeMessage ? renderWelcomeMessage(welcomeMessage) : "Loading..."}
                </h2>
              </div>
            </div>
            
            {/* Input Area - Always visible at bottom with safe area for mobile navigation */}
            <div className="flex-shrink-0 w-full mx-auto px-3 sm:px-4 md:px-6 pb-20 sm:pb-4 md:pb-6 pt-2 sm:pt-3 bg-transparent" style={{ paddingBottom: 'max(5rem, calc(1rem + env(safe-area-inset-bottom, 0px)))' }}>
              <div className="relative w-full">
                <div className="relative">
                  <textarea
                    ref={inputRef}
                    className="w-full border rounded-[20px] px-3 sm:px-4 md:px-5 py-2.5 sm:py-3 pr-16 sm:pr-20 md:pr-24 bg-transparent focus:outline-none resize-none font-normal text-sm sm:text-base border-gray-300 text-gray-900 placeholder-gray-400 overflow-hidden"
                    style={{ minHeight: '50px', maxHeight: '200px' }}
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value);
                      setTimeout(() => adjustTextareaHeight(), 0);
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder={(isGenerating || isTyping) ? "Generating response... Press Enter to stop" : micPlaceholder}
                    disabled={loading}
                    aria-label="Chat input"
                    rows={1}
                  />
                  {/* Microphone button inside textarea */}
                  <button
                    className={`absolute right-12 sm:right-14 md:right-16 p-1.5 sm:p-2 rounded-full transition-all duration-200 ${listening ? 'animate-pulse' : ''} hover:bg-gray-200 hover:scale-105 flex items-center justify-center`}
                    style={{ 
                      backgroundColor: listening ? 'var(--brand-primary-50)' : 'transparent',
                      borderWidth: listening ? '2px' : '0px',
                      borderStyle: 'solid',
                      borderColor: listening ? 'var(--brand-primary)' : 'transparent',
                      zIndex: 10,
                      top: '50%',
                      transform: 'translateY(-50%)'
                    }}
                    onClick={handleMic}
                    disabled={loading || listening}
                    aria-label="Start voice input"
                    tabIndex={0}
                  >
                    {/* Heroicons solid mic icon */}
                    <svg viewBox="0 0 20 20" fill="currentColor" className={`w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 ${listening ? 'var(--brand-primary)' : '#6b7280'}`}><path fillRule="evenodd" d="M10 18a7 7 0 0 0 7-7h-1a6 6 0 0 1-12 0H3a7 7 0 0 0 7 7zm3-7a3 3 0 1 1-6 0V7a3 3 0 1 1 6 0v4z" clipRule="evenodd"/></svg>
                  </button>
                  {/* Send/Stop button as icon inside textarea */}
                  <button
                    className={`absolute right-2 sm:right-3 p-1.5 sm:p-2 rounded-full transition-all duration-200 disabled:opacity-50 flex items-center justify-center ${
                      (isGenerating || isTyping)
                        ? 'bg-gray-600 hover:bg-gray-700 shadow-lg animate-pulse' 
                        : 'hover:bg-gray-200'
                    }`}
                    onClick={(isGenerating || isTyping) ? stopGeneration : () => sendMessage()}
                    disabled={!(isGenerating || isTyping) && (loading || requestInProgress || !input.trim())}
                    aria-label={(isGenerating || isTyping) ? "Stop generation" : "Send message"}
                    tabIndex={0}
                    style={{ 
                      zIndex: 10, 
                      border: 'none',
                      top: '50%',
                      transform: 'translateY(-50%)'
                    }}
                  >
                  {(isGenerating || isTyping) ? (
                    /* Stop icon - more prominent */
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 text-white">
                      <path d="M6 6h12v12H6z" />
                    </svg>
                  ) : (
                    /* Send icon */
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 text-gray-500">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                  )}
                </button>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Chat Screen - Normal Layout */}
          {/* Show cleared message */}
          {showClearedMessage && (
            <div className="mb-4 text-center">
              <div className="inline-block bg-green-100 text-green-800 px-4 py-2 rounded-lg text-sm">
                ✨ Chat cleared! Starting fresh...
              </div>
            </div>
          )}
          <div 
            ref={messagesContainerRef} 
            className={`flex-1 overflow-y-auto overflow-x-hidden pt-4 sm:pt-6 mb-3 sm:mb-4 space-y-2 pl-1 sm:pl-2 md:pl-4 pr-4 lg:pr-6 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 hover:scrollbar-thumb-gray-400 relative ${isDesktop ? 'scrollbar-hide-desktop' : ''}`}
            style={{ 
              minHeight: 0,
              ...(isDesktop ? {
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
              } : {})
            }}
          >
        
        {messages.map((msg, idx) => (
          'type' in msg && msg.type === 'calendar' ? (
            <div key={idx} className="flex justify-start">
              <div className="max-w-[90%] sm:max-w-[85%] w-full bg-white rounded-lg p-2 mt-2 flex justify-center" style={{ borderColor: 'var(--brand-primary-200)' }}>
                <iframe
                  src={msg.url}
                  className="w-full max-w-sm sm:max-w-none"
                  style={{ border: 0, minHeight: '200px', height: 'auto' }}
                  title="Holiday Calendar"
                  allowFullScreen
                />
              </div>
            </div>
          ) : 'type' in msg && msg.type === 'map' ? (
            <div key={idx} className="flex justify-start">
              <div className="max-w-[90%] sm:max-w-[85%] w-full bg-white rounded-lg p-2 mt-2 flex justify-center" style={{ borderColor: 'var(--brand-primary-200)' }}>
                <iframe
                  src={msg.url}
                  className="w-full max-w-sm sm:max-w-none"
                  style={{ border: 0, minHeight: '200px', height: 'auto' }}
                  title="Prakriti School Location"
                  allowFullScreen
                />
              </div>
            </div>
          ) : 'type' in msg && msg.type === 'videos' ? (
            <div key={idx} className="flex justify-start">
              <div className="max-w-[90%] sm:max-w-[88%] w-full space-y-3 sm:space-y-4">
                {msg.videos.map((video, videoIdx) => (
                  <div key={videoIdx} className="bg-white border border-gray-200 rounded-lg p-3 sm:p-4 shadow-sm">
                    <div className="flex flex-col gap-3 sm:gap-4">
                      <div className="flex-shrink-0">
                        <Image
                          src={video.thumbnail_url}
                          alt={video.title}
                          width={400}
                          height={160}
                          className="w-full h-40 sm:h-32 object-cover rounded-lg"
                          unoptimized
                        />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-base sm:text-lg font-semibold mb-2 line-clamp-2 text-gray-900">{video.title}</h3>
                        <p className="text-xs sm:text-sm mb-2 line-clamp-2 text-gray-600">{video.description}</p>
                        <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs text-gray-500">
                          <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--brand-primary-100)', color: 'var(--brand-primary-800)' }}>{video.category}</span>
                          <span className="text-xs">{video.duration}</span>
                        </div>
                        <div className="mt-3">
                          <a
                            href={`https://www.youtube.com/watch?v=${video.video_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-3 py-2 bg-red-600 text-white text-xs sm:text-sm font-medium rounded-lg hover:bg-red-700 transition-colors w-full sm:w-auto justify-center"
                          >
                            <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                            </svg>
                            Watch on YouTube
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div
              key={idx}
              className={`flex ${'text' in msg && msg.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4 sm:mb-5`}
            >
              {'text' in msg && msg.sender === 'user' ? (
              <div
              className="max-w-[95%] sm:max-w-[85%] md:max-w-[80%] break-words text-white rounded-2xl rounded-tr-sm px-3 sm:px-4 md:px-5 py-2.5 sm:py-3 shadow-sm"
              style={{ backgroundColor: 'var(--brand-primary)' }}
              >
                {'text' in msg && (
                  <div className="markdown-content text-sm sm:text-base leading-relaxed">
                    <div className="whitespace-pre-wrap text-white font-bold">{msg.text}</div>
                  </div>
                )}
              </div>
              ) : (
              <div className="max-w-[95%] sm:max-w-[85%] md:max-w-[80%] break-words text-gray-900">
                {'text' in msg && (
                  <div className="markdown-content text-sm sm:text-base leading-relaxed text-gray-900">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        // Custom styling for Markdown elements
                        h1: ({...props}) => <h1 className="text-xl font-bold mb-2 text-gray-900" {...props} />,
                        h2: ({...props}) => <h2 className="text-lg font-bold mb-2 text-gray-900" {...props} />,
                        h3: ({...props}) => <h3 className="text-base font-bold mb-2 text-gray-900" {...props} />,
                        p: ({...props}) => <p className="mb-2 leading-relaxed text-gray-800" {...props} />,
                        ul: ({...props}) => <ul className="list-disc list-inside mb-2 space-y-1 text-gray-800" {...props} />,
                        ol: ({...props}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-gray-800" {...props} />,
                        li: ({...props}) => <li className="mb-1 text-gray-800" {...props} />,
                        strong: ({...props}) => <strong className="font-bold text-gray-900" {...props} />,
                        em: ({...props}) => <em className="italic text-gray-800" {...props} />,
                        code: ({...props}) => <code className="px-1.5 py-0.5 rounded text-sm font-mono bg-gray-200 text-gray-900" {...props} />,
                        blockquote: ({...props}) => <blockquote className="border-l-4 pl-4 italic py-2 rounded-r text-gray-700 border-gray-400 bg-gray-50" {...props} />,
                        table: ({...props}) => <div className="overflow-x-auto mb-4"><table className="border-collapse w-full min-w-full text-sm border-gray-300" {...props} /></div>,
                        th: ({...props}) => <th className="border px-3 py-2 font-bold border-gray-300 bg-gray-200 text-gray-900 text-left" {...props} />,
                        td: ({...props}) => <td className="border px-3 py-2 border-gray-300 text-gray-800" {...props} />,
                        // Custom link component - blue color and opens in new tab
                        a: ({href, children, ...props}) => (
                          <a 
                            href={href} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-700 underline transition-colors font-medium"
                            {...props}
                          >
                            {children}
                          </a>
                        ),
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  </div>
                )}
                {'text' in msg && msg.sender === 'bot' && (
                  <div className="flex justify-start mt-2">
                    <button
                      onClick={() => handleCopy(msg.text, idx)}
                      className="p-1.5 rounded hover:bg-gray-100 focus:outline-none transition-colors"
                      title={copiedIdx === idx ? 'Copied!' : 'Copy'}
                      aria-label="Copy message"
                    >
                      <CopyIcon copied={copiedIdx === idx} />
                    </button>
                  </div>
                )}
              </div>
              )}
            </div>
          )
        ))}
        {isTyping && (
          <div className="flex justify-start mb-4 sm:mb-5" key={`typing-${typingAnimationKey}`}>
            <div 
              ref={typingRef}
              className="max-w-[85%] sm:max-w-[80%] text-gray-900 px-4 py-2.5 sm:px-5 sm:py-3 chatbot-typing-reveal"
              style={{
                opacity: shouldAnimate ? 1 : 0,
                transform: shouldAnimate ? 'translateY(0)' : 'translateY(10px)',
                transition: shouldAnimate 
                  ? 'opacity 2.5s cubic-bezier(0.4, 0, 0.2, 1), transform 2.5s cubic-bezier(0.4, 0, 0.2, 1)' 
                  : 'none'
              } as React.CSSProperties}
            >
              <div className="markdown-content text-sm sm:text-base leading-relaxed">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Custom styling for Markdown elements
                    h1: ({...props}) => <h1 className="text-xl font-bold mb-2 text-gray-900" {...props} />,
                    h2: ({...props}) => <h2 className="text-lg font-bold mb-2 text-gray-900" {...props} />,
                    h3: ({...props}) => <h3 className="text-base font-bold mb-2 text-gray-900" {...props} />,
                    p: ({...props}) => <p className="mb-2 leading-relaxed text-gray-800" {...props} />,
                    ul: ({...props}) => <ul className="list-disc list-inside mb-2 space-y-1 text-gray-800" {...props} />,
                    ol: ({...props}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-gray-800" {...props} />,
                    li: ({...props}) => <li className="mb-1 text-gray-800" {...props} />,
                    strong: ({...props}) => <strong className="font-bold text-gray-900" {...props} />,
                    em: ({...props}) => <em className="italic text-gray-800" {...props} />,
                    code: ({...props}) => <code className="px-1.5 py-0.5 rounded text-sm font-mono bg-gray-200 text-gray-900" {...props} />,
                    blockquote: ({...props}) => <blockquote className="border-l-4 pl-4 italic py-2 rounded-r text-gray-700 border-gray-400 bg-gray-50" {...props} />,
                    table: ({...props}) => <div className="overflow-x-auto mb-4"><table className="border-collapse w-full min-w-full text-sm border-gray-300" {...props} /></div>,
                    th: ({...props}) => <th className="border px-3 py-2 font-bold border-gray-300 bg-gray-200 text-gray-900 text-left" {...props} />,
                    td: ({...props}) => <td className="border px-3 py-2 border-gray-300 text-gray-800" {...props} />,
                    // Custom link component - blue color and opens in new tab
                    a: ({href, children, ...props}) => (
                      <a 
                        href={href} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-700 underline transition-colors font-medium"
                        {...props}
                      >
                        {children}
                      </a>
                    ),
                  }}
                >
                  {displayedBotText}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
        {showTypingAnimation && loading && !responseStartedTypingRef.current && (
          <div className="flex justify-start mb-4 sm:mb-5">
            <div className="max-w-[90%] sm:max-w-[85%] text-gray-900">
              <TypingAnimation />
            </div>
          </div>
        )}
            <div ref={messagesEndRef} />
          </div>

          <div className="relative w-full max-w-full mt-auto px-2 sm:px-4 pb-20 sm:pb-4 md:pb-6 mx-auto" style={{ paddingBottom: 'max(5rem, calc(1rem + env(safe-area-inset-bottom, 0px)))' }}>
            <div className="relative">
              <textarea
                ref={inputRef}
                className="w-full border rounded-[20px] px-3 sm:px-4 md:px-5 py-2.5 sm:py-3 pr-16 sm:pr-20 md:pr-24 bg-transparent focus:outline-none resize-none font-normal text-sm sm:text-base border-gray-300 text-gray-900 placeholder-gray-400 overflow-hidden"
                style={{ minHeight: '50px', maxHeight: '200px' }}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  setTimeout(() => adjustTextareaHeight(), 0);
                }}
                onKeyDown={handleKeyDown}
                placeholder={(isGenerating || isTyping) ? "Generating response... Press Enter to stop" : micPlaceholder}
                disabled={loading}
                aria-label="Chat input"
                rows={1}
              />
              {/* Microphone button inside textarea */}
              <button
                className={`absolute right-12 sm:right-14 md:right-16 p-1.5 sm:p-2 rounded-full transition-all duration-200 ${listening ? 'animate-pulse' : ''} hover:bg-gray-200 hover:scale-105 flex items-center justify-center`}
                style={{ 
                  backgroundColor: listening ? 'var(--brand-primary-50)' : 'transparent',
                  borderWidth: listening ? '2px' : '0px',
                  borderStyle: 'solid',
                  borderColor: listening ? 'var(--brand-primary)' : 'transparent',
                  zIndex: 10,
                  top: '50%',
                  transform: 'translateY(-50%)'
                }}
                onClick={handleMic}
                disabled={loading || listening}
                aria-label="Start voice input"
                tabIndex={0}
              >
                {/* Heroicons solid mic icon */}
                <svg viewBox="0 0 20 20" fill="currentColor" className={`w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 ${listening ? 'var(--brand-primary)' : '#6b7280'}`}><path fillRule="evenodd" d="M10 18a7 7 0 0 0 7-7h-1a6 6 0 0 1-12 0H3a7 7 0 0 0 7 7zm3-7a3 3 0 1 1-6 0V7a3 3 0 1 1 6 0v4z" clipRule="evenodd"/></svg>
              </button>
              {/* Send/Stop button as icon inside textarea */}
              <button
                className={`absolute right-2 sm:right-3 p-1.5 sm:p-2 rounded-full transition-all duration-200 disabled:opacity-50 flex items-center justify-center ${
                  (isGenerating || isTyping)
                    ? 'bg-gray-600 hover:bg-gray-700 shadow-lg animate-pulse' 
                    : 'hover:bg-gray-200'
                }`}
                onClick={(isGenerating || isTyping) ? stopGeneration : () => sendMessage()}
                disabled={!(isGenerating || isTyping) && (loading || requestInProgress || !input.trim())}
                aria-label={(isGenerating || isTyping) ? "Stop generation" : "Send message"}
                tabIndex={0}
                style={{ 
                  zIndex: 10, 
                  border: 'none',
                  top: '50%',
                  transform: 'translateY(-50%)'
                }}
              >
              {(isGenerating || isTyping) ? (
                /* Stop icon - more prominent */
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 text-white">
                  <path d="M6 6h12v12H6z" />
                </svg>
              ) : (
                /* Send icon */
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 text-gray-500">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              )}
            </button>
            </div>
          </div>
        </>
      )}

    </div>
  );
});

Chatbot.displayName = 'Chatbot';

export default Chatbot;