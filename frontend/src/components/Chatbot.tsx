import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useState as useCopyState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/providers/AuthProvider';
import { useChatHistory } from '@/providers/ChatHistoryProvider';

type Message =
  | { sender: 'user' | 'bot'; text: string }
  | { sender: 'bot'; type: 'calendar'; url: string }
  | { sender: 'bot'; type: 'map'; url: string }
  | { sender: 'bot'; type: 'videos'; videos: Array<{video_id: string; title: string; description: string; category: string; duration: string; thumbnail_url: string}> };

// Typing dots animation component
const TypingDots: React.FC = () => (
  <span className="inline-flex space-x-1">
    <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--brand-primary)', animationDelay: '0s' }}></span>
    <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--brand-primary)', animationDelay: '0.2s' }}></span>
    <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--brand-primary)', animationDelay: '0.4s' }}></span>
  </span>
);

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
  const [displayedBotText, setDisplayedBotText] = useState<string>('');
  const [isTyping, setIsTyping] = useState(false);
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

  const [welcomeMessage, setWelcomeMessage] = useState<{ text: string; focusWord: string } | null>(null);

  // Initialize welcome message on client side only
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
      alert('Speech recognition is not supported in this browser.');
      return;
    }
    // @ts-expect-error - webkitSpeechRecognition is not in TypeScript types
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    setListening(true);
    setMicPlaceholder('Listening...');
    recognition.onresult = async (event: Event) => {
      const results = (event as unknown as { results: SpeechRecognitionResultList }).results;
      const transcript = results[0][0].transcript;
      setInput('');
      setListening(false);
      setMicPlaceholder('Ask me anything...');
      // Immediately send the recognized text as a user message
      if (transcript && transcript.trim()) {
        const userMsg: Message = { sender: 'user', text: transcript };
        setMessages((msgs) => [...msgs, userMsg]);
        
        
        setLoading(true);
        setDisplayedBotText('');
        setIsTyping(false);
        fetch('/api/chatbot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: transcript,
            user_id: user?.id || null
          }),
        })
          .then((res) => res.json())
          .then((data) => {
            // Check for structured responses with type field
            if (data.type === 'calendar' && data.response && data.response.url) {
              setMessages((msgs) => [...msgs, { sender: 'bot', type: 'calendar', url: data.response.url }]);
              setIsTyping(false);
              setDisplayedBotText('');
              return;
            } else if (data.type === 'map' && data.response && data.response.url) {
              setMessages((msgs) => [...msgs, { sender: 'bot', type: 'map', url: data.response.url }]);
              setIsTyping(false);
              setDisplayedBotText('');
              return;
            } else if (data.type === 'mixed' && Array.isArray(data.response)) {
              // Handle mixed responses (like location with map)
              setMessages((msgs) => [
                ...msgs,
                { sender: 'bot', text: data.response[0] },
                data.response[1]?.type === 'map' ? { sender: 'bot', type: 'map', url: data.response[1].url } : null
              ].filter(Boolean) as Message[]);
              setIsTyping(false);
              setDisplayedBotText('');
              return;
            }
            
            // Handle regular text responses
            const fullText = data.response;
            console.log('Frontend speech received response length:', fullText?.length);
            console.log('Frontend speech received response:', fullText);
            let idx = 0;
            setIsTyping(true);
            function typeChar() {
              setDisplayedBotText(fullText.slice(0, idx + 1));
              if (idx < fullText.length - 1) {
                idx++;
                setTimeout(typeChar, 8);
              } else {
                setIsTyping(false);
                setMessages((msgs) => [...msgs, { sender: 'bot', text: fullText }]);
                setHasFirstResponse(true);
              }
            }
            typeChar();
          })
          .catch(() => {
            setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Error: Could not get response.' }]);
            setHasFirstResponse(true);
          })
          .finally(() => {
            setLoading(false);
          });
      }
      inputRef.current?.focus();
    };
    recognition.onerror = () => {
      setListening(false);
      setMicPlaceholder('Ask me anything...');
    };
    recognition.onend = () => {
      setListening(false);
      setMicPlaceholder('Ask me anything...');
    };
    recognition.start();
  };

  // Stop current generation
  const stopGeneration = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setIsGenerating(false);
    setLoading(false);
    setRequestInProgress(false);
    setIsTyping(false);
    setDisplayedBotText('');
  };

  // Handle suggestion button clicks with specific prompts
  const handleSuggestionClick = (suggestion: string) => {
    // Prevent clicking if already processing
    if (loading || requestInProgress || isGenerating) {
      return;
    }

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
    
    console.log('🎯 Suggestion clicked:', suggestion, '→ Sending prompt:', prompt);
    
    // CRITICAL: Don't set input state - pass prompt directly to sendMessage
    // Setting input and then clearing it causes the message field to be empty in the request
    // Pass prompt directly to sendMessage to ensure it's used
    
    // Focus the input field to ensure it's visible and scroll into view
    if (inputRef.current) {
      // Temporarily show the prompt in the input for visual feedback
      inputRef.current.value = prompt;
      inputRef.current.focus();
      // Scroll input into view if needed
      inputRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // Use requestAnimationFrame to ensure DOM updates are complete
    requestAnimationFrame(() => {
      // Use another requestAnimationFrame to ensure state is updated
      requestAnimationFrame(() => {
        // Use setTimeout to ensure the input is visible before sending
        // Give user a moment to see the query in the input field
        // Pass prompt directly to sendMessage to avoid closure issues
        setTimeout(() => {
          sendMessage(prompt);
          // Clear the input field after sending
          if (inputRef.current) {
            inputRef.current.value = '';
          }
          setInput('');
        }, 500);
      });
    });
  };

  // Handle external query from sidebar - using ref to avoid dependency issues
  const previousQueryRef = useRef<string>('');
  
  useEffect(() => {
    if (externalQuery && externalQuery !== previousQueryRef.current && !loading && !requestInProgress && !isGenerating) {
      // Don't clear conversation history for guest users - they should maintain their session
      previousQueryRef.current = externalQuery;
      handleSuggestionClick(externalQuery);
      if (onQueryProcessed) {
        setTimeout(() => {
          onQueryProcessed();
        }, 200);
      }
    }
  }, [externalQuery, loading, requestInProgress, isGenerating, user, conversationHistory.length]);

  // Send message to backend /chatbot endpoint
  const sendMessage = async (messageText?: string) => {
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
    
    // CRITICAL: If no active session (especially for guest users), create one immediately
    if (!activeSession) {
      console.log('⚠️ No active session found - creating one for guest user');
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
    
    // If still no session, log error but continue (message will be shown but not saved)
    if (!activeSession) {
      console.error('❌ No active session available - message will not be saved to history');
    }
    
    console.log('Proceeding with message sending...', {
      hasActiveSession: !!activeSession,
      sessionId: activeSession?.id
    });
    const userMsg: Message = { sender: 'user', text: messageToSend };
    setMessages((msgs) => [...msgs, userMsg]);
    
    
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
    
    // Create abort controller for this request
    const controller = new AbortController();
    setAbortController(controller);
    
    // Show immediate loading feedback
    setTimeout(() => {
      if (loading) {
        setDisplayedBotText('Thinking...');
        setIsTyping(true);
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
        const botMsg = { sender: 'bot' as const, type: 'calendar' as const, url: data.response.url };
        setMessages((msgs) => [...msgs, botMsg]);
        console.log('Adding bot calendar message to chat history...');
        await addMessage({
          sender: 'bot',
          text: data.response.url,
          type: 'calendar',
          url: data.response.url,
        });
        console.log('Bot calendar message added to chat history');
        setIsTyping(false);
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      } else if (data.type === 'map' && data.response && data.response.url) {
        const botMsg = { sender: 'bot' as const, type: 'map' as const, url: data.response.url };
        setMessages((msgs) => [...msgs, botMsg]);
        await addMessage({
          sender: 'bot',
          text: data.response.url,
          type: 'map',
          url: data.response.url,
        });
        setIsTyping(false);
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      } else if (data.type === 'mixed' && Array.isArray(data.response)) {
        // Handle mixed responses (like location with map or videos)
        const messages_to_add = [{ sender: 'bot', text: data.response[0] } as Message];
        
        if (data.response[1]?.type === 'map') {
          messages_to_add.push({ sender: 'bot', type: 'map', url: data.response[1].url } as Message);
        } else if (data.response[1]?.type === 'videos') {
          messages_to_add.push({ sender: 'bot', type: 'videos', videos: data.response[1].videos } as Message);
        }
        
        setMessages((msgs) => [...msgs, ...messages_to_add]);
        setIsTyping(false);
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      } else if (data.type === 'videos' && data.response && data.response.videos) {
        // Handle video responses
        const botMsg = { sender: 'bot' as const, type: 'videos' as const, videos: data.response.videos };
        setMessages((msgs) => [...msgs, botMsg]);
        await addMessage({
          sender: 'bot',
          text: JSON.stringify(data.response.videos),
          type: 'videos',
          videos: data.response.videos,
        });
        setIsTyping(false);
        setDisplayedBotText('');
        setHasFirstResponse(true);
        return;
      }
      
      // Handle regular text responses (including Markdown)
      const fullText = data.response;
      console.log('Frontend received response length:', fullText?.length);
      console.log('Frontend received response:', fullText);
      
      // Add bot response to conversation history
      setConversationHistory(prev => [...prev, { role: 'assistant', content: fullText }]);
      
      let idx = 0;
      setIsTyping(true);
      async function typeChar() {
        setDisplayedBotText(fullText.slice(0, idx + 1));
        if (idx < fullText.length - 1) {
          idx++;
          setTimeout(typeChar, 8); // speed of typing
        } else {
          setIsTyping(false);
          // Store the full Markdown text for rendering
          setMessages((msgs) => [...msgs, { sender: 'bot', text: fullText }]);
          
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
        }
      }
      await typeChar();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Request was aborted, don't add error message
        console.log('Request aborted by user');
      } else {
        setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Error: Could not get response.' }]);
        setHasFirstResponse(true);
      }
    } finally {
      setLoading(false);
      setRequestInProgress(false);
      setIsGenerating(false);
      setAbortController(null);
    }
  };

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
  useEffect(() => {
    if (isTyping && typingRef.current) {
      // Scroll to typing text when it's active with a small delay for smooth rendering
      setTimeout(() => {
        typingRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 50);
    } else {
      // Scroll to bottom for regular messages
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, isTyping, displayedBotText]);

  // Auto-focus textarea when messages change, unless user clicked elsewhere
  useEffect(() => {
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
      inputRef.current.focus();
    }
  }, [messages]);

  // Track last loaded session ID to prevent unnecessary reloads
  const lastLoadedSessionIdRef = useRef<string | null>(null);
  
  // Load messages from active session (optimized to prevent blinking)
  useEffect(() => {
    // Skip if still loading to prevent blinking
    if (chatHistoryLoading) {
      return;
    }
    
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
      // Only clear if we've previously loaded a session (not on first load)
      if (lastLoadedSessionIdRef.current !== null) {
        console.log('❌ No active session - clearing messages');
        lastLoadedSessionIdRef.current = null;
        setMessages([]);
        setConversationHistory([]);
        setHasFirstResponse(false);
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
          activeSessionMessageCount
        });
        
        // CRITICAL: Only update messages if:
        // 1. This is the first load (lastLoadedSessionIdRef is null)
        // 2. Session ID changed (switched to different session)
        // 3. Session has more messages than current state (session was updated - new messages added)
        // 4. Session message count changed (activeSessionMessageCount dependency triggered this)
        // 5. Session has messages but UI is empty (page refresh scenario)
        // This prevents overwriting messages that are being added in real-time via setMessages
        const isFirstLoad = lastLoadedSessionIdRef.current === null;
        const isSessionChanged = lastLoadedSessionIdRef.current !== activeSession.id;
        const hasMoreMessages = sessionMessages.length > messages.length;
        const sessionCountChanged = sessionMessages.length !== messages.length; // Session count is different from UI count
        const isEmptyButSessionHasMessages = messages.length === 0 && sessionMessages.length > 0; // Page refresh - load from session
        const shouldSyncFromSession = isFirstLoad || isSessionChanged || hasMoreMessages || sessionCountChanged || isEmptyButSessionHasMessages;
        
        if (shouldSyncFromSession) {
          console.log('✅ Syncing messages from session to state', {
            reason: isFirstLoad ? 'first load' : isSessionChanged ? 'session changed' : hasMoreMessages ? 'session has more messages' : isEmptyButSessionHasMessages ? 'page refresh - loading from session' : 'session count changed',
            sessionMessagesCount: sessionMessages.length,
            currentMessagesCount: messages.length,
            activeSessionMessageCount
          });
          
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
          const history = messagesToSet.map(msg => ({
            role: msg.sender === 'bot' ? 'assistant' : msg.sender,
            content: msg.text,
          }));
          setConversationHistory(history);
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
  }, [activeSessionId, getActiveSession, chatHistoryLoading, user, activeSessionMessageCount]); // Include activeSessionMessageCount to detect when session messages are added

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
    setLoading(false);
    setRequestInProgress(false);
    setIsGenerating(false);
    setAbortController(null);
    setListening(false);
    setDisplayedBotText('');
    setIsTyping(false);
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
  }, [clearChat, getRandomWelcomeMessage, clearActiveSession, abortController]);

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
        setLoading(false);
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
  }, [chatHistoryLoading, hasShownInitialLoad, user?.id, abortController]);
  
  // Only show loading opacity on the very first app load, never again (even on login/logout)
  const containerClassName = (chatHistoryLoading && !hasShownInitialLoad) ? 'opacity-40 scale-[0.98]' : 'opacity-100 scale-100';
  
  return (
    <div className={`flex flex-col h-full w-full bg-transparent mx-auto transition-all duration-200 ${containerClassName}`}>
      {messages.length === 0 ? (
        <>
          {/* Welcome Screen - Mobile Optimized Layout */}
          <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
            {/* Spacer at top - reduced for mobile */}
            <div className="flex-shrink-0 pt-10 sm:pt-14 md:pt-20"></div>
            
            {/* Centered Content: Logo and Message - Scrollable if needed */}
            <div className="flex-1 flex flex-col items-center justify-center px-3 sm:px-4 md:px-6 min-h-0 overflow-y-auto">
              {/* Logo - Smaller on mobile */}
              <div className="flex justify-center mb-3 sm:mb-4 md:mb-6 flex-shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img 
                  src="/prakriti_logo.webp" 
                  alt="Prakriti Visual" 
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
            <div className="flex-shrink-0 w-full mx-auto px-3 sm:px-4 md:px-6 pb-20 sm:pb-4 md:pb-6 pt-2 sm:pt-3 bg-white" style={{ paddingBottom: 'max(5rem, calc(1rem + env(safe-area-inset-bottom, 0px)))' }}>
              <div className="relative w-full">
                <div className="relative">
                  <textarea
                    ref={inputRef}
                    className="w-full border rounded-[20px] px-3 sm:px-4 md:px-5 py-2.5 sm:py-3 pr-16 sm:pr-20 md:pr-24 bg-white focus:outline-none resize-none font-normal text-sm sm:text-base border-gray-300 text-gray-900 placeholder-gray-400 overflow-hidden"
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
                      borderColor: listening ? 'var(--brand-primary)' : 'transparent',
                      zIndex: 10,
                      border: 'none',
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
                    onClick={(isGenerating || isTyping) ? stopGeneration : sendMessage}
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
          <div className="flex-1 overflow-y-auto pt-4 sm:pt-6 mb-3 sm:mb-4 space-y-2 px-1 sm:px-2 md:px-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 hover:scrollbar-thumb-gray-400" style={{ minHeight: 0 }}>
        
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
                        <img
                          src={video.thumbnail_url}
                          alt={video.title}
                          className="w-full h-40 sm:h-32 object-cover rounded-lg"
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
              className="max-w-[95%] sm:max-w-[85%] md:max-w-[80%] break-words bg-blue-600 text-white rounded-2xl rounded-tr-sm px-3 sm:px-4 md:px-5 py-2.5 sm:py-3 shadow-sm"
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
          <div className="flex justify-start mb-4 sm:mb-5">
            <div 
              ref={typingRef}
              className="max-w-[85%] sm:max-w-[80%] text-gray-900 px-4 py-2.5 sm:px-5 sm:py-3"
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
        {loading && !isTyping && (
          <div className="flex justify-start mb-4 sm:mb-5">
            <div className="max-w-[90%] sm:max-w-[85%] text-gray-900">
              <TypingDots />
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
                  borderColor: listening ? 'var(--brand-primary)' : 'transparent',
                  zIndex: 10,
                  border: 'none',
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
                onClick={(isGenerating || isTyping) ? stopGeneration : sendMessage}
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