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
}

const Chatbot = React.forwardRef<{ clearChat: () => void }, ChatbotProps>(({ clearChat }, ref) => {
  const { user, profile } = useAuth();
  const { 
    getActiveSession, 
    addMessage, 
    clearActiveSession, 
    createNewSession,
    isLoading: chatHistoryLoading,
    isGuestMode
  } = useChatHistory();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [requestInProgress, setRequestInProgress] = useState(false);
  const [listening, setListening] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [hasFirstResponse, setHasFirstResponse] = useState(false);
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
    
    // Set the input and automatically send the message
    setInput(prompt);
    
    // Use setTimeout to ensure the input is set before sending
    setTimeout(() => {
      sendMessage();
    }, 100);
  };

  // Send message to backend /chatbot endpoint
  const sendMessage = async () => {
    console.log('=== SEND MESSAGE FUNCTION START ===');
    console.log('Input:', input);
    console.log('Loading:', loading);
    console.log('RequestInProgress:', requestInProgress);
    
    if (!input.trim() || loading || requestInProgress) {
      console.log('Early return - input empty or already processing');
      return; // Prevent sending if already loading or request in progress
    }
    
    // Check if there's an active session for authenticated users only
    const activeSession = getActiveSession();
    if (!activeSession && user && !isGuestMode) {
      console.log('No active session - authenticated user must click "New Chat" first');
      alert('Please click "New Chat" to start a conversation first.');
      return;
    }
    
    console.log('Proceeding with message sending...');
    const userMsg: Message = { sender: 'user', text: input };
    setMessages((msgs) => [...msgs, userMsg]);
    
    
    // Add user message to chat history and wait for it to complete
    console.log('=== USER MESSAGE START ===');
    console.log('Adding user message to chat history...');
    console.log('User message text:', input);
    
    try {
      await addMessage({
        sender: 'user',
        text: input,
      });
      console.log('User message added to chat history successfully');
    } catch (error) {
      console.error('Error adding user message to chat history:', error);
    }
    
    console.log('=== USER MESSAGE END ===');
    
    // Add user message to conversation history
    const newHistory = [...conversationHistory, { role: 'user', content: input }];
    setConversationHistory(newHistory);
    
    setInput('');
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
      const requestData = { 
        message: input,
        conversation_history: newHistory,
        user_id: user?.id || null,
        user_profile: profile || null  // Pass the complete user profile including gender
      };
      
      console.log('Chatbot sending request data:', JSON.stringify(requestData, null, 2));
      
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        signal: controller.signal,
      });
      const data = await res.json();
      
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
          
          console.log('Bot text message added to chat history');
          console.log('=== BOT MESSAGE END ===');
          
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

  // Load messages from active session
  useEffect(() => {
    console.log('🔄 useEffect triggered - loading messages from active session');
    const activeSession = getActiveSession();
    console.log('📋 Active session:', activeSession ? {
      id: activeSession.id,
      messagesCount: activeSession.messages.length,
      messages: activeSession.messages.map(m => ({ sender: m.sender, text: m.text.substring(0, 50) + '...' }))
    } : 'null');
    
    if (activeSession) {
      const sessionMessages: Message[] = activeSession.messages.map(msg => ({
        sender: msg.sender,
        text: msg.text,
        ...(msg.type && { type: msg.type }),
        ...(msg.url && { url: msg.url }),
        ...(msg.videos && { videos: msg.videos }),
      }));
      console.log('📝 Setting messages from session:', sessionMessages.length, 'messages');
      setMessages(sessionMessages);
      
      // Check if there are any bot messages to set hasFirstResponse
      const hasBotMessages = sessionMessages.some(msg => msg.sender === 'bot');
      setHasFirstResponse(hasBotMessages);
      
      // Update conversation history for API calls
      const history = activeSession.messages.map(msg => ({
        role: msg.sender === 'bot' ? 'assistant' : msg.sender,
        content: msg.text,
      }));
      setConversationHistory(history);
    } else {
      console.log('❌ No active session - clearing messages');
      setMessages([]);
      setConversationHistory([]);
      setHasFirstResponse(false);
    }
  }, [getActiveSession]);

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
  }, [clearChat, getRandomWelcomeMessage, clearActiveSession, abortController, setCopiedIdx]);

  // Expose clearChat function to parent
  React.useImperativeHandle(ref, () => ({
    clearChat: handleClearChat
  }), [handleClearChat]);

  return (
    <div className="flex flex-col h-[70vh] sm:h-[80vh] w-full max-w-xl mx-auto bg-transparent p-2 sm:p-0">
      {messages.length === 0 ? (
        <>
          {/* Welcome Screen - Centered Layout */}
          <div className="flex-1 flex flex-col justify-center items-center">
            {/* Image above heading */}
            <div className="flex justify-center mb-4 sm:mb-6">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src="/prakriti_logo.webp" 
                alt="Prakriti Visual" 
                className="w-20 h-20 sm:w-24 sm:h-24 md:w-32 md:h-32 object-contain" 
              />
            </div>
            {/* Heading */}
            <div className="mb-8 sm:mb-12 text-center px-2">
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-normal mb-2 leading-tight text-gray-500">
                {welcomeMessage ? renderWelcomeMessage(welcomeMessage) : "Loading..."}
              </h2>
            </div>
            
            {/* Input Area - Centered */}
            <div className="w-full max-w-lg">
              <div className="relative flex items-end w-full px-1 sm:px-0">
                <textarea
                  ref={inputRef}
                  className="w-full border rounded-[20px] px-4 sm:px-5 py-3 pr-20 sm:pr-24 bg-transparent focus:outline-none resize-none font-normal text-sm sm:text-base border-gray-300 text-gray-900 placeholder-gray-400"
                  style={{ height: 'auto', minHeight: '60px', maxHeight: '120px' }}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={(isGenerating || isTyping) ? "Generating response... Press Enter to stop" : micPlaceholder}
                  disabled={loading}
                  aria-label="Chat input"
                  rows={1}
                />
                {/* Microphone button inside textarea */}
                <button
                  className={`absolute right-12 sm:right-14 bottom-2 p-2 rounded-full transition-all duration-200 ${listening ? 'animate-pulse' : ''} hover:bg-gray-200 hover:scale-105`}
                  style={{ 
                    backgroundColor: listening ? 'var(--brand-primary-50)' : 'transparent',
                    borderColor: listening ? 'var(--brand-primary)' : 'transparent',
                    zIndex: 2,
                    border: 'none'
                  }}
                  onClick={handleMic}
                  disabled={loading || listening}
                  aria-label="Start voice input"
                  tabIndex={0}
                >
                  {/* Heroicons solid mic icon */}
                  <svg viewBox="0 0 20 20" fill="currentColor" className={`w-5 h-5 sm:w-6 sm:h-6 ${listening ? 'var(--brand-primary)' : '#6b7280'}`}><path fillRule="evenodd" d="M10 18a7 7 0 0 0 7-7h-1a6 6 0 0 1-12 0H3a7 7 0 0 0 7 7zm3-7a3 3 0 1 1-6 0V7a3 3 0 1 1 6 0v4z" clipRule="evenodd"/></svg>
                </button>
                {/* Send/Stop button as icon inside textarea */}
                <button
                  className={`absolute right-2 bottom-2 p-2 rounded-full transition-all duration-200 disabled:opacity-50 ${
                    (isGenerating || isTyping)
                      ? 'bg-gray-600 hover:bg-gray-700 shadow-lg animate-pulse' 
                      : 'hover:bg-gray-200'
                  }`}
                  onClick={(isGenerating || isTyping) ? stopGeneration : sendMessage}
                  disabled={!(isGenerating || isTyping) && (loading || requestInProgress || !input.trim())}
                  aria-label={(isGenerating || isTyping) ? "Stop generation" : "Send message"}
                  tabIndex={0}
                  style={{ zIndex: 2, border: 'none' }}
                >
                  {(isGenerating || isTyping) ? (
                    /* Stop icon - more prominent */
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 sm:w-6 sm:h-6 text-white">
                      <path d="M6 6h12v12H6z" />
                    </svg>
                  ) : (
                    /* Send icon */
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 sm:w-6 sm:h-6 text-gray-500">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                  )}
                </button>
              </div>
              
              {/* Chat Shortcuts - Centered - Only show before first response and when not loading */}
              {!hasFirstResponse && !chatHistoryLoading && (
                <div className="mt-4 px-1 sm:px-0">
                  <div className="flex flex-wrap gap-2 justify-center">
                  {[
                    "Help with homework",
                    "Explain a concept",
                    "Study tips",
                    "School schedule",
                    "Assignment help",
                    "Math problems",
                    "Science questions",
                    "History facts",
                    "Prakriti School info",
                    "Progressive education",
                    "Learning for happiness",
                    "IGCSE curriculum"
                  ].map((shortcut, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(shortcut)}
                      className="px-3 py-1.5 text-xs sm:text-sm bg-gray-100 text-gray-700 rounded-full transition-colors duration-200 border border-gray-200 hover:shadow-md hover:scale-105"
                      style={{
                        backgroundColor: 'var(--brand-primary-50)',
                        color: 'var(--brand-primary)',
                        borderColor: 'var(--brand-primary-200)'
                      }}
                      disabled={loading || requestInProgress || isGenerating}
                    >
                      {shortcut}
                    </button>
                  ))}
                  </div>
                </div>
              )}
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
          <div className="flex-1 overflow-y-auto mb-4 space-y-2 pr-2 sm:pr-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 hover:scrollbar-thumb-gray-400" style={{ minHeight: 0 }}>
        
        {messages.map((msg, idx) => (
          'type' in msg && msg.type === 'calendar' ? (
            <div key={idx} className="flex justify-start">
              <div className="max-w-[95%] sm:max-w-[80%] w-full bg-white rounded-lg p-2 mt-2 flex justify-center" style={{ borderColor: 'var(--brand-primary-200)' }}>
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
              <div className="max-w-[95%] sm:max-w-[80%] w-full bg-white rounded-lg p-2 mt-2 flex justify-center" style={{ borderColor: 'var(--brand-primary-200)' }}>
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
              <div className="max-w-[95%] sm:max-w-[90%] w-full space-y-3 sm:space-y-4">
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
              className={`flex ${'text' in msg && msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
              className={`max-w-[85%] sm:max-w-[80%] break-words ${
                'text' in msg && msg.sender === 'user'
                  ? 'text-blue-900 text-right justify-end'
                  : 'text-gray-900 text-left'
              }`}
                style={{ background: 'none', padding: '0.75rem 0', borderRadius: 0 }}
              >
                {'text' in msg && (
                  <div className="markdown-content">
                    {msg.sender === 'user' ? (
                      <div className="text-gray-800 whitespace-pre-wrap">{msg.text}</div>
                    ) : (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          // Custom styling for Markdown elements
                          h1: ({...props}) => <h1 className="text-xl font-bold mb-2 text-gray-800" {...props} />,
                          h2: ({...props}) => <h2 className="text-lg font-bold mb-2 text-gray-800" {...props} />,
                          h3: ({...props}) => <h3 className="text-base font-bold mb-2 text-gray-800" {...props} />,
                          p: ({...props}) => <p className="mb-2 leading-relaxed text-gray-700" {...props} />,
                          ul: ({...props}) => <ul className="list-disc list-inside mb-2 space-y-1 text-gray-700" {...props} />,
                          ol: ({...props}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-gray-700" {...props} />,
                          li: ({...props}) => <li className="mb-1 text-gray-700" {...props} />,
                          strong: ({...props}) => <strong className="font-bold text-gray-900" {...props} />,
                          em: ({...props}) => <em className="italic text-gray-700" {...props} />,
                          code: ({...props}) => <code className="px-1 py-0.5 rounded text-sm font-mono bg-gray-100 text-gray-800" {...props} />,
                          blockquote: ({...props}) => <blockquote className="border-l-4 pl-4 italic py-2 rounded-r text-gray-600 border-gray-300 bg-gray-50" style={{ borderLeftColor: 'var(--brand-primary-300)', backgroundColor: 'var(--brand-primary-50)' }} {...props} />,
                          table: ({...props}) => <table className="border-collapse w-full mb-2 text-sm border-gray-300" {...props} />,
                          th: ({...props}) => <th className="border px-2 py-1 font-bold border-gray-300 bg-gray-100 text-gray-800" {...props} />,
                          td: ({...props}) => <td className="border px-2 py-1 border-gray-300 text-gray-700" {...props} />,
                        }}
                      >
                        {msg.text}
                      </ReactMarkdown>
                    )}
                  </div>
                )}
                {'text' in msg && msg.sender === 'bot' && (
                  <div className="flex justify-start mt-2">
                    <button
                      onClick={() => handleCopy(msg.text, idx)}
                      className="p-1 rounded hover:bg-gray-100 focus:outline-none"
                      title={copiedIdx === idx ? 'Copied!' : 'Copy'}
                      aria-label="Copy message"
                    >
                      <CopyIcon copied={copiedIdx === idx} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div 
              ref={typingRef}
              className="max-w-[80%] break-words text-left text-gray-900" 
              style={{ background: 'none', padding: '0.75rem 0', borderRadius: 0 }}
            >
              <div className="markdown-content">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Custom styling for Markdown elements
                    h1: ({...props}) => <h1 className="text-xl font-bold mb-2 text-gray-800" {...props} />,
                    h2: ({...props}) => <h2 className="text-lg font-bold mb-2 text-gray-800" {...props} />,
                    h3: ({...props}) => <h3 className="text-base font-bold mb-2 text-gray-800" {...props} />,
                    p: ({...props}) => <p className="mb-2 leading-relaxed text-gray-700" {...props} />,
                    ul: ({...props}) => <ul className="list-disc list-inside mb-2 space-y-1 text-gray-700" {...props} />,
                    ol: ({...props}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-gray-700" {...props} />,
                    li: ({...props}) => <li className="mb-1 text-gray-700" {...props} />,
                    strong: ({...props}) => <strong className="font-bold text-gray-900" {...props} />,
                    em: ({...props}) => <em className="italic text-gray-700" {...props} />,
                    code: ({...props}) => <code className="px-1 py-0.5 rounded text-sm font-mono bg-gray-100 text-gray-800" {...props} />,
                    blockquote: ({...props}) => <blockquote className="border-l-4 pl-4 italic py-2 rounded-r text-gray-600 border-gray-300 bg-gray-50" style={{ borderLeftColor: 'var(--brand-primary-300)', backgroundColor: 'var(--brand-primary-50)' }} {...props} />,
                    table: ({...props}) => <table className="border-collapse w-full mb-2 text-sm border-gray-300" {...props} />,
                    th: ({...props}) => <th className="border px-2 py-1 font-bold border-gray-300 bg-gray-100 text-gray-800" {...props} />,
                    td: ({...props}) => <td className="border px-2 py-1 border-gray-300 text-gray-700" {...props} />,
                  }}
                >
                  {displayedBotText}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
        {loading && !isTyping && (
          <div className="flex justify-start">
            <div className="max-w-[80%] break-words text-left text-gray-900" style={{ background: 'none', padding: '0.75rem 0', borderRadius: 0 }}>
              <TypingDots />
            </div>
          </div>
        )}
            <div ref={messagesEndRef} />
          </div>

          <div className="relative flex items-end w-full mt-auto px-1 sm:px-0">
            <textarea
              ref={inputRef}
              className="w-full border rounded-[20px] px-4 sm:px-5 py-3 pr-20 sm:pr-24 bg-transparent focus:outline-none resize-none font-normal text-sm sm:text-base border-gray-300 text-gray-900 placeholder-gray-400"
              style={{ height: 'auto', minHeight: '60px', maxHeight: '120px' }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={(isGenerating || isTyping) ? "Generating response... Press Enter to stop" : micPlaceholder}
              disabled={loading}
              aria-label="Chat input"
              rows={1}
                />
                {/* Microphone button inside textarea */}
            <button
              className={`absolute right-12 sm:right-14 bottom-2 p-2 rounded-full transition-all duration-200 ${listening ? 'animate-pulse' : ''} hover:bg-gray-200 hover:scale-105`}
              style={{ 
                backgroundColor: listening ? 'var(--brand-primary-50)' : 'transparent',
                borderColor: listening ? 'var(--brand-primary)' : 'transparent',
                zIndex: 2,
                border: 'none'
              }}
              onClick={handleMic}
              disabled={loading || listening}
              aria-label="Start voice input"
              tabIndex={0}
            >
              {/* Heroicons solid mic icon */}
              <svg viewBox="0 0 20 20" fill="currentColor" className={`w-5 h-5 sm:w-6 sm:h-6 ${listening ? 'var(--brand-primary)' : '#6b7280'}`}><path fillRule="evenodd" d="M10 18a7 7 0 0 0 7-7h-1a6 6 0 0 1-12 0H3a7 7 0 0 0 7 7zm3-7a3 3 0 1 1-6 0V7a3 3 0 1 1 6 0v4z" clipRule="evenodd"/></svg>
            </button>
            {/* Send/Stop button as icon inside textarea */}
            <button
              className={`absolute right-2 bottom-2 p-2 rounded-full transition-all duration-200 disabled:opacity-50 ${
                (isGenerating || isTyping)
                  ? 'bg-gray-600 hover:bg-gray-700 shadow-lg animate-pulse' 
                  : 'hover:bg-gray-200'
              }`}
              onClick={(isGenerating || isTyping) ? stopGeneration : sendMessage}
              disabled={!(isGenerating || isTyping) && (loading || requestInProgress || !input.trim())}
              aria-label={(isGenerating || isTyping) ? "Stop generation" : "Send message"}
              tabIndex={0}
              style={{ zIndex: 2, border: 'none' }}
            >
              {(isGenerating || isTyping) ? (
                /* Stop icon - more prominent */
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 sm:w-6 sm:h-6 text-white">
                  <path d="M6 6h12v12H6z" />
                </svg>
              ) : (
                /* Send icon */
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 sm:w-6 sm:h-6 text-gray-500">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              )}
            </button>
          </div>
          
          {/* Chat Shortcuts - Only show before first response and when not loading */}
          {!hasFirstResponse && !chatHistoryLoading && (
            <div className="mt-3 px-1 sm:px-0">
              <div className="flex flex-wrap gap-2 justify-center">
              {[
                "Help with homework",
                "Explain a concept",
                "Study tips",
                "School schedule",
                "Assignment help",
                "Math problems",
                "Science questions",
                "History facts",
                "Prakriti School info",
                "Progressive education",
                "Learning for happiness",
                "IGCSE curriculum"
              ].map((shortcut, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(shortcut)}
                  className="px-3 py-1.5 text-xs sm:text-sm bg-gray-100 text-gray-700 rounded-full transition-colors duration-200 border border-gray-200 hover:shadow-md hover:scale-105"
                  style={{
                    backgroundColor: 'var(--brand-primary-50)',
                    color: 'var(--brand-primary)',
                    borderColor: 'var(--brand-primary-200)'
                  }}
                  disabled={loading || requestInProgress || isGenerating}
                >
                  {shortcut}
                </button>
              ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
});

Chatbot.displayName = 'Chatbot';

export default Chatbot; 