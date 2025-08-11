import React, { useState, useRef, useEffect } from 'react';
import { useState as useCopyState } from 'react';

type Message =
  | { sender: 'user' | 'bot'; text: string }
  | { sender: 'bot'; type: 'calendar'; url: string }
  | { sender: 'bot'; type: 'map'; url: string };

// Typing dots animation component
const TypingDots: React.FC = () => (
  <span className="inline-flex space-x-1">
    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></span>
    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
  </span>
);

// Simple copy icon SVG
const CopyIcon = ({ copied }: { copied: boolean }) => (
  copied ? (
    <svg className="w-5 h-5 text-green-500 ml-2" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
  ) : (
    <svg className="w-5 h-5 text-gray-400 hover:text-blue-500 ml-2 cursor-pointer" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>
  )
);

const Chatbot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [micPlaceholder, setMicPlaceholder] = useState<string>('Ask me anything...');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [displayedBotText, setDisplayedBotText] = useState<string>('');
  const [isTyping, setIsTyping] = useState(false);
  // For copy feedback per message
  const [copiedIdx, setCopiedIdx] = useCopyState<number | null>(null);

  // Speech-to-text logic
  const handleMic = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    setListening(true);
    setMicPlaceholder('Listening...');
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
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
          body: JSON.stringify({ message: transcript }),
        })
          .then((res) => res.json())
          .then((data) => {
            if (data && typeof data === 'object' && data.type === 'calendar' && data.url) {
              setMessages((msgs) => [...msgs, { sender: 'bot', type: 'calendar', url: data.url }]);
              setIsTyping(false);
              setDisplayedBotText('');
            } else {
              const fullText = data.response;
              let idx = 0;
              setIsTyping(true);
              function typeChar() {
                setDisplayedBotText(fullText.slice(0, idx + 1));
                if (idx < fullText.length - 1) {
                  idx++;
                  setTimeout(typeChar, 18);
                } else {
                  setIsTyping(false);
                  setMessages((msgs) => [...msgs, { sender: 'bot', text: fullText }]);
                }
              }
              typeChar();
            }
          })
          .catch(() => {
            setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Error: Could not get response.' }]);
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

  // Send message to backend /chatbot endpoint
  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { sender: 'user', text: input };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');
    setLoading(true);
    setDisplayedBotText('');
    setIsTyping(false);
    try {
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });
      const data = await res.json();
      // If backend returns an array (AI text + map), handle both
      if (Array.isArray(data)) {
        // First element: AI text, Second: map object
        setMessages((msgs) => [
          ...msgs,
          { sender: 'bot', text: data[0] },
          data[1]?.type === 'map' ? { sender: 'bot', type: 'map', url: data[1].url } : null
        ].filter(Boolean) as Message[]);
        setIsTyping(false);
        setDisplayedBotText('');
      } else if (data && typeof data === 'object' && data.type === 'calendar' && data.url) {
        setMessages((msgs) => [...msgs, { sender: 'bot', type: 'calendar', url: data.url }]);
        setIsTyping(false);
        setDisplayedBotText('');
      } else if (data && typeof data === 'object' && data.type === 'map' && data.url) {
        setMessages((msgs) => [...msgs, { sender: 'bot', type: 'map', url: data.url }]);
        setIsTyping(false);
        setDisplayedBotText('');
      } else {
        // Typing effect for bot response
        const fullText = data.response;
        let idx = 0;
        setIsTyping(true);
        function typeChar() {
          setDisplayedBotText(fullText.slice(0, idx + 1));
          if (idx < fullText.length - 1) {
            idx++;
            setTimeout(typeChar, 18); // speed of typing
          } else {
            setIsTyping(false);
            setMessages((msgs) => [...msgs, { sender: 'bot', text: fullText }]);
          }
        }
        typeChar();
      }
    } catch (err) {
      setMessages((msgs) => [...msgs, { sender: 'bot', text: 'Error: Could not get response.' }]);
    } finally {
      setLoading(false);
    }
  };

  // Handle Enter + Shift for newline, Enter for send
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

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

  // For copy feedback per message
  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1200);
  };

  return (
    <div className="flex flex-col h-[70vh] w-full max-w-xl mx-auto bg-transparent p-0">
      {messages.length === 0 && (
        <>
          {/* Image above heading */}
          <div className="flex justify-center">
            <img src="/prakriti_logo.webp" alt="Prakriti Visual" style={{ maxWidth: '150px', height: 'auto', marginBottom: '1rem' }} />
          </div>
          {/* Heading */}
          <div className="mb-6 text-center">
            <h2 className="text-3xl font-normal text-gray-700 mb-2">What whispers are you following today?</h2>
          </div>
        </>
      )}
      <div className="flex-1 overflow-y-auto mb-4 space-y-2 pr-4" style={{ minHeight: 0 }}>
        {messages.map((msg, idx) => (
          'type' in msg && msg.type === 'calendar' ? (
            <div key={idx} className="flex justify-start">
              <div className="max-w-[80%] w-full bg-white border border-blue-200 rounded-lg p-2 mt-2 flex justify-center">
                <iframe
                  src={msg.url}
                  style={{ border: 0, width: '350px', minHeight: 250 }}
                  title="Holiday Calendar"
                  allowFullScreen
                />
              </div>
            </div>
          ) : 'type' in msg && msg.type === 'map' ? (
            <div key={idx} className="flex justify-start">
              <div className="max-w-[80%] w-full bg-white border border-blue-200 rounded-lg p-2 mt-2 flex justify-center">
                <iframe
                  src={msg.url}
                  style={{ border: 0, width: '350px', minHeight: 250 }}
                  title="Prakriti School Location"
                  allowFullScreen
                />
              </div>
            </div>
          ) : (
            <div
              key={idx}
              className={`flex ${'text' in msg && msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] break-words ${
                  'text' in msg && msg.sender === 'user'
                    ? 'text-blue-900 text-right justify-end'
                    : 'text-gray-900 text-left'
                }`}
                style={{ background: 'none', padding: '0.75rem 0', borderRadius: 0 }}
              >
                {'text' in msg && <span>{msg.text}</span>}
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
            <div className="max-w-[80%] break-words text-gray-900 text-left" style={{ background: 'none', padding: '0.75rem 0', borderRadius: 0 }}>
              {displayedBotText}
            </div>
          </div>
        )}
        {loading && !isTyping && (
          <div className="flex justify-start">
            <div className="max-w-[80%] break-words text-gray-900 text-left" style={{ background: 'none', padding: '0.75rem 0', borderRadius: 0 }}>
              <TypingDots />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="relative flex items-end w-full mt-auto">
        <textarea
          ref={inputRef}
          className="w-full border border-gray-300 rounded-[20px] px-5 py-3 pr-24 bg-gray-50 text-gray-900 placeholder-gray-400 focus:outline-none resize-none font-normal"
          style={{ height: 100 }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={micPlaceholder}
          disabled={loading}
          aria-label="Chat input"
          rows={1}
        />
        {/* Microphone button inside textarea */}
        <button
          className={`absolute right-14 bottom-2 p-2 rounded-full hover:bg-blue-50 transition ${listening ? 'animate-pulse border-blue-500' : ''}`}
          onClick={handleMic}
          disabled={loading || listening}
          aria-label="Start voice input"
          tabIndex={0}
          style={{ zIndex: 2, background: 'transparent', border: 'none' }}
        >
          {/* Heroicons solid mic icon */}
          <svg viewBox="0 0 20 20" fill="currentColor" className={`w-6 h-6 ${listening ? 'text-blue-600' : 'text-gray-500'}`}><path fillRule="evenodd" d="M10 18a7 7 0 0 0 7-7h-1a6 6 0 0 1-12 0H3a7 7 0 0 0 7 7zm3-7a3 3 0 1 1-6 0V7a3 3 0 1 1 6 0v4z" clipRule="evenodd"/></svg>
        </button>
        {/* Send button as icon inside textarea */}
        <button
          className="absolute right-2 bottom-2 p-2 rounded-full hover:bg-gray-200 transition disabled:opacity-50"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          aria-label="Send message"
          tabIndex={0}
          style={{ zIndex: 2, background: 'transparent', border: 'none' }}
        >
          {/* Telegram-style paper-plane icon */}
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7 text-gray-500">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default Chatbot; 