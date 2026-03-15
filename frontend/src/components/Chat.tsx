'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Terminal, Shield, Cpu, Activity, KeyRound, RefreshCw, AlertTriangle, LogOut } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { AtomicNeuron } from './Logo';
import { fetchJson, getWsUrl } from '@/lib/api';

const MAX_MESSAGES = 200;
const MAX_RECONNECT_ATTEMPTS = 6;
const API_KEY_STORAGE_KEY = 'purecortex.chat.api_key';

type ChatMessage = {
  sender: 'user' | 'agent';
  text: string;
  timestamp: Date;
};

type ConnectionState = 'locked' | 'bootstrapping' | 'connecting' | 'connected' | 'reconnecting' | 'error';

type ConnectMode = 'manual' | 'restore' | 'reconnect';

interface ChatSessionResponse {
  session_token: string;
  expires_at: string;
  ttl_seconds: number;
  owner: string;
  tier: string;
}

function readStoredApiKey(): string {
  if (typeof window === 'undefined') {
    return '';
  }

  try {
    return window.sessionStorage.getItem(API_KEY_STORAGE_KEY) ?? '';
  } catch {
    return '';
  }
}

function persistApiKey(apiKey: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.sessionStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
}

function clearStoredApiKey(): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.sessionStorage.removeItem(API_KEY_STORAGE_KEY);
}

function getStatusClasses(state: ConnectionState): string {
  switch (state) {
    case 'connected':
      return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10';
    case 'reconnecting':
    case 'connecting':
    case 'bootstrapping':
      return 'text-[#007AFF] border-[#007AFF]/20 bg-[#007AFF]/10';
    case 'error':
      return 'text-red-400 border-red-500/20 bg-red-500/10';
    default:
      return 'text-yellow-400 border-yellow-500/20 bg-yellow-500/10';
  }
}

function getStatusLabel(state: ConnectionState): string {
  switch (state) {
    case 'bootstrapping':
      return 'Authenticating';
    case 'connecting':
      return 'Connecting';
    case 'connected':
      return 'Connected';
    case 'reconnecting':
      return 'Reconnecting';
    case 'error':
      return 'Unavailable';
    default:
      return 'Locked';
  }
}

function formatExpiry(value: string | null): string {
  if (!value) {
    return 'Short-lived session';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Short-lived session';
  }

  return `Expires ${parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [apiKeyInput, setApiKeyInput] = useState<string>(() => readStoredApiKey());
  const [apiKey, setApiKey] = useState<string>(() => readStoredApiKey());
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>(() => readStoredApiKey() ? 'bootstrapping' : 'locked');
  const [statusMessage, setStatusMessage] = useState(() => readStoredApiKey() ? 'Restoring saved chat session...' : 'Paste an API key to start a chat session.');
  const [authError, setAuthError] = useState<string | null>(null);
  const [sessionExpiresAt, setSessionExpiresAt] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const autoConnectAttempted = useRef(false);
  const userDisconnected = useRef(false);

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => {
      const next = [...prev, msg];
      return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next;
    });
  }, []);

  const connectWebSocket = useCallback(async (key: string, mode: ConnectMode = 'manual') => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (ws.current) {
      ws.current.onclose = null;
      ws.current.onerror = null;
      ws.current.close(1000, 'Refreshing chat session');
      ws.current = null;
    }

    userDisconnected.current = false;
    setAuthError(null);
    setIsConnected(false);
    setIsTyping(false);
    setConnectionState(mode === 'reconnect' ? 'reconnecting' : 'bootstrapping');
    setStatusMessage(
      mode === 'restore'
        ? 'Restoring saved chat session...'
        : mode === 'reconnect'
          ? 'Refreshing short-lived chat session...'
          : 'Authenticating API key...'
    );

    try {
      const session = await fetchJson<ChatSessionResponse>('/api/chat/session', {
        method: 'POST',
        headers: {
          'X-API-Key': key,
        },
      });

      setApiKey(key);
      setApiKeyInput(key);
      setSessionExpiresAt(session.expires_at);
      persistApiKey(key);
      setConnectionState('connecting');
      setStatusMessage('Opening secure websocket...');

      const socketUrl = `${getWsUrl('/ws/chat')}?session=${encodeURIComponent(session.session_token)}`;
      const socket = new WebSocket(socketUrl);

      socket.onopen = () => {
        reconnectAttempts.current = 0;
        setIsConnected(true);
        setConnectionState('connected');
        setStatusMessage('Secure chat session active.');
      };

      socket.onclose = (event) => {
        ws.current = null;
        setIsConnected(false);
        setIsTyping(false);

        if (userDisconnected.current) {
          return;
        }

        if (event.code === 4001) {
          setConnectionState('error');
          setStatusMessage('Chat authentication failed.');
          setAuthError(event.reason || 'Invalid or expired chat session.');
          return;
        }

        if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
          setConnectionState('error');
          setStatusMessage('Reconnect limit reached.');
          setAuthError(event.reason || 'Unable to reconnect to PURECORTEX chat.');
          return;
        }

        const nextAttempt = reconnectAttempts.current + 1;
        reconnectAttempts.current = nextAttempt;
        const delay = Math.min(1000 * Math.pow(2, nextAttempt - 1), 15000);
        setConnectionState('reconnecting');
        setStatusMessage(`Connection lost. Reconnecting in ${Math.ceil(delay / 1000)}s...`);
        reconnectTimeout.current = setTimeout(() => {
          void connectWebSocket(key, 'reconnect');
        }, delay);
      };

      socket.onerror = () => {
        socket.close();
      };

      socket.onmessage = (event) => {
        setIsTyping(false);
        addMessage({ sender: 'agent', text: event.data, timestamp: new Date() });
      };

      ws.current = socket;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create chat session.';
      const authFailure = /401|api key required|invalid|revoked/i.test(message);

      setConnectionState(authFailure ? 'locked' : 'error');
      setStatusMessage(authFailure ? 'API key required to open chat.' : 'Unable to start chat session.');
      setAuthError(message);
      setSessionExpiresAt(null);

      if (authFailure) {
        clearStoredApiKey();
        setApiKey('');
      }
    }
  }, [addMessage]);

  useEffect(() => {
    if (apiKey && !autoConnectAttempted.current) {
      autoConnectAttempted.current = true;
      void connectWebSocket(apiKey, 'restore');
    }
  }, [apiKey, connectWebSocket]);

  useEffect(() => {
    return () => {
      userDisconnected.current = true;
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      ws.current?.close();
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = apiKeyInput.trim();
    if (!trimmed) {
      setAuthError('Paste a valid API key first.');
      return;
    }

    autoConnectAttempted.current = true;
    void connectWebSocket(trimmed, 'manual');
  };

  const handleDisconnect = useCallback(() => {
    userDisconnected.current = true;
    reconnectAttempts.current = 0;

    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (ws.current) {
      ws.current.onclose = null;
      ws.current.onerror = null;
      ws.current.close(1000, 'Client disconnected');
      ws.current = null;
    }

    clearStoredApiKey();
    setApiKey('');
    setApiKeyInput('');
    setIsConnected(false);
    setIsTyping(false);
    setSessionExpiresAt(null);
    setConnectionState('locked');
    setStatusMessage('Paste an API key to start a chat session.');
    setAuthError(null);
  }, []);

  const retryConnection = useCallback(() => {
    const key = apiKeyInput.trim() || apiKey;
    if (!key) {
      return;
    }
    autoConnectAttempted.current = true;
    void connectWebSocket(key, 'manual');
  }, [apiKey, apiKeyInput, connectWebSocket]);

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !ws.current || !isConnected) return;

    ws.current.send(input);
    addMessage({ sender: 'user', text: input, timestamp: new Date() });
    setInput('');
    setIsTyping(true);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] sm:h-[650px] w-full max-w-4xl mx-auto border border-white/5 rounded-2xl bg-[#050505] overflow-hidden shadow-2xl border-t-[#007AFF]/30">
      {/* Header */}
      <div className="bg-[#1A1A1A] p-3 sm:p-5 border-b border-white/5 flex justify-between items-center backdrop-blur-md">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="relative flex-shrink-0">
            <AtomicNeuron className="w-8 h-8 sm:w-10 sm:h-10" />
            <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 sm:w-3.5 sm:h-3.5 rounded-full border-2 border-[#1A1A1A] ${isConnected ? 'bg-[#10B981]' : 'bg-[#EF4444]'}`} />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm sm:text-lg font-bold text-white tracking-tight leading-none uppercase truncate">Cortex-Omega-1</h2>
            <p className="text-[9px] sm:text-[10px] text-[#007AFF] font-mono mt-1 uppercase tracking-[0.15em] sm:tracking-[0.2em]">Neural Node Active</p>
          </div>
        </div>

        <div className="flex gap-3 items-center">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-mono uppercase tracking-tighter ${getStatusClasses(connectionState)}`}>
            <Shield className={`w-3 h-3 ${isConnected ? 'text-[#10B981]' : 'text-current'}`} />
            {getStatusLabel(connectionState)}
          </div>
          {apiKey && (
            <button
              onClick={handleDisconnect}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-[10px] text-gray-400 font-mono uppercase tracking-tighter hover:text-white hover:border-[#007AFF]/30 transition-all"
            >
              <LogOut className="w-3 h-3" />
              Disconnect
            </button>
          )}
        </div>
      </div>
      
      {/* Messages Area */}
      <div ref={scrollRef} className="flex-1 p-3 sm:p-6 overflow-y-auto space-y-4 sm:space-y-6 scrollbar-thin scrollbar-thumb-white/10">
        {authError && (
          <div className="flex items-start gap-3 p-4 rounded-2xl border border-red-500/20 bg-red-500/10">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="text-sm font-bold text-red-300 uppercase tracking-wider">Chat Issue</div>
              <p className="text-sm text-red-100/80">{authError}</p>
            </div>
          </div>
        )}

        {!apiKey ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 sm:px-10">
            <div className="w-full max-w-xl bg-[#1A1A1A] border border-[#007AFF]/20 rounded-2xl p-6 sm:p-8 space-y-6">
              <div className="space-y-3">
                <div className="w-14 h-14 rounded-2xl bg-[#007AFF]/10 border border-[#007AFF]/20 flex items-center justify-center mx-auto">
                  <KeyRound className="w-7 h-7 text-[#007AFF]" />
                </div>
                <h3 className="text-2xl font-bold text-white uppercase tracking-tighter italic">Unlock Neural Link</h3>
                <p className="text-sm text-gray-400">
                  Paste a PURECORTEX API key to mint a short-lived chat session. The websocket uses the temporary session token, not your raw API key.
                </p>
              </div>

              <form onSubmit={handleUnlock} className="space-y-4">
                <input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder="ctx_..."
                  autoComplete="off"
                  className="w-full bg-[#050505] text-white border border-white/5 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-[#007AFF]/50 focus:border-[#007AFF]/50 transition-all placeholder:text-gray-700 font-mono text-sm"
                />
                <button
                  type="submit"
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#007AFF] text-white text-sm font-black uppercase tracking-wider hover:bg-[#0062CC] transition-all"
                >
                  <Shield className="w-4 h-4" />
                  Start Secure Session
                </button>
              </form>

              <div className="text-[11px] text-gray-500">
                Keys are stored in browser `sessionStorage` only and are cleared when you disconnect or close the session.
              </div>
            </div>
          </div>
        ) : messages.length === 0 && connectionState !== 'connected' ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 sm:px-10">
            <div className="w-full max-w-xl bg-[#1A1A1A] border border-white/5 rounded-2xl p-6 sm:p-8 space-y-5">
              <div className="w-14 h-14 rounded-2xl bg-[#007AFF]/10 border border-[#007AFF]/20 flex items-center justify-center mx-auto">
                <RefreshCw className={`w-7 h-7 text-[#007AFF] ${connectionState !== 'error' ? 'animate-spin' : ''}`} />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-white uppercase tracking-tighter italic">{getStatusLabel(connectionState)}</h3>
                <p className="text-sm text-gray-400">{statusMessage}</p>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={retryConnection}
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#007AFF] text-white text-sm font-black uppercase tracking-wider hover:bg-[#0062CC] transition-all"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
                <button
                  onClick={handleDisconnect}
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-white/10 text-gray-300 text-sm font-bold uppercase tracking-wider hover:border-white/20 hover:text-white transition-all"
                >
                  <LogOut className="w-4 h-4" />
                  Change Key
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full opacity-40 text-center px-10">
                <Terminal className="w-12 h-12 mb-4 text-[#007AFF]" />
                <h3 className="text-xl font-bold text-white mb-2 uppercase tracking-tighter italic">Neural Link Established</h3>
                <p className="text-sm text-gray-400 font-medium">Tri-Brain orchestration is online. PURECORTEX intelligence waiting for transmission.</p>
              </div>
            )}

            <AnimatePresence>
              {messages.map((msg, idx) => (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={`${msg.sender}-${msg.timestamp.getTime()}-${idx}`}
                  className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] relative ${
                    msg.sender === 'user'
                      ? 'bg-[#007AFF] text-white rounded-2xl rounded-tr-none p-4 shadow-lg shadow-[#007AFF]/20'
                      : 'bg-[#1A1A1A] text-gray-100 rounded-2xl rounded-tl-none p-4 border border-white/5 shadow-xl'
                  }`}>
                    <div className={`text-[9px] font-mono mb-1.5 uppercase tracking-widest opacity-60 flex items-center gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                      {msg.sender === 'user' ? (
                        <>
                          <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          <span className="w-1 h-1 rounded-full bg-white/40" />
                          <span>Authenticated Controller</span>
                        </>
                      ) : (
                        <>
                          <Cpu className="w-3 h-3 text-[#007AFF]" />
                          <span>PURECORTEX Brain</span>
                          <span className="w-1 h-1 rounded-full bg-[#007AFF]/40" />
                          <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </>
                      )}
                    </div>
                    <div className="text-[14px] leading-relaxed font-sans font-medium">{msg.text}</div>
                  </div>
                </motion.div>
              ))}

              {isTyping && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="bg-[#1A1A1A] p-4 rounded-2xl rounded-tl-none border border-white/5 flex gap-1.5">
                    <span className="w-2 h-2 bg-[#007AFF] rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-2 h-2 bg-[#007AFF] rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-2 h-2 bg-[#007AFF] rounded-full animate-bounce" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="p-3 sm:p-6 bg-[#1A1A1A]/50 backdrop-blur-xl border-t border-white/5 flex gap-2 sm:gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={4096}
            aria-label="Chat message"
            placeholder={isConnected ? 'Transmit command...' : 'Authenticate to begin chatting...'}
            disabled={!isConnected}
            className="w-full bg-[#050505] text-white text-sm sm:text-base border border-white/5 rounded-xl px-3 sm:px-5 py-3 sm:py-3.5 outline-none focus:ring-2 focus:ring-[#007AFF]/50 focus:border-[#007AFF]/50 transition-all placeholder:text-gray-700 font-medium disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={!isConnected || !input.trim()}
          aria-label="Send message"
          className="bg-[#007AFF] hover:bg-[#0062CC] disabled:opacity-30 disabled:cursor-not-allowed text-white px-4 sm:px-6 rounded-xl font-black uppercase tracking-tighter transition-all shadow-lg shadow-[#007AFF]/20 active:scale-95 flex items-center justify-center flex-shrink-0"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Footer Info */}
      <div className="px-3 sm:px-6 py-2 sm:py-3 bg-[#050505] border-t border-white/5 flex flex-wrap justify-between items-center text-[8px] sm:text-[9px] text-gray-600 font-mono uppercase tracking-wider sm:tracking-widest gap-1">
        <div className="flex items-center gap-3 sm:gap-4">
           <span className="flex items-center gap-1 text-[#007AFF]"><Shield className="w-3 h-3" /> Hardened Link</span>
           <span className="hidden sm:flex items-center gap-1 text-[#10B981]"><Activity className="w-3 h-3" /> Algorand Testnet</span>
        </div>
        <div className="flex items-center gap-3 sm:gap-4">
          <span>{formatExpiry(sessionExpiresAt)}</span>
          {reconnectAttempts.current > 0 && <span>Retry {reconnectAttempts.current}/{MAX_RECONNECT_ATTEMPTS}</span>}
        </div>
      </div>
    </div>
  );
}
