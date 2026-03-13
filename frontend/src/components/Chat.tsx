'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, Terminal, Shield, Cpu, Activity, Info, BarChart3, Wallet } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Chat() {
  const [messages, setMessages] = useState<{ sender: 'user' | 'agent'; text: string; timestamp: Date }[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // In production this would be wss://api.purecortex.ai/ws/chat
    const socketUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/chat';
    ws.current = new WebSocket(socketUrl);
    
    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);
    
    ws.current.onmessage = (event) => {
      setIsTyping(false);
      setMessages((prev) => [...prev, { 
        sender: 'agent', 
        text: event.data, 
        timestamp: new Date() 
      }]);
    };

    return () => {
      ws.current?.close();
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !ws.current || !isConnected) return;

    ws.current.send(input);
    setMessages((prev) => [...prev, { 
      sender: 'user', 
      text: input, 
      timestamp: new Date() 
    }]);
    setInput('');
    setIsTyping(true);
  };

  return (
    <div className="flex flex-col h-[650px] w-full max-w-4xl mx-auto border border-white/10 rounded-2xl bg-[#0D0D12] overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] border-t-blue-500/20">
      {/* Header */}
      <div className="bg-[#16161D] p-5 border-b border-white/5 flex justify-between items-center backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center">
              <Cpu className="text-white w-6 h-6" />
            </div>
            <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-[#16161D] ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight leading-none">Cortex-Omega-1</h2>
            <p className="text-xs text-blue-400 font-mono mt-1 uppercase tracking-widest">Sovereign Node v1.4.2</p>
          </div>
        </div>
        
        <div className="hidden md:flex gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-[10px] text-gray-400 font-mono uppercase tracking-tighter">
                <Shield className="w-3 h-3 text-emerald-400" />
                Hardened
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-[10px] text-gray-400 font-mono uppercase tracking-tighter">
                <Activity className="w-3 h-3 text-blue-400" />
                Syncing
            </div>
        </div>
      </div>
      
      {/* Messages Area */}
      <div ref={scrollRef} className="flex-1 p-6 overflow-y-auto space-y-6 scrollbar-thin scrollbar-thumb-white/10">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full opacity-40 text-center px-10">
            <Terminal className="w-12 h-12 mb-4 text-blue-500" />
            <h3 className="text-xl font-bold text-white mb-2">Neural Link Established</h3>
            <p className="text-sm text-gray-400">PureCortex dual-brain orchestration is online. You are conversing with a sovereign entity on Algorand.</p>
          </div>
        )}
        
        <AnimatePresence>
          {messages.map((msg, idx) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={idx} 
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] relative ${
                msg.sender === 'user' 
                  ? 'bg-blue-600/90 text-white rounded-2xl rounded-tr-none p-4 shadow-lg shadow-blue-900/20' 
                  : 'bg-[#1E1E26] text-gray-100 rounded-2xl rounded-tl-none p-4 border border-white/5 shadow-xl'
              }`}>
                <div className={`text-[10px] font-mono mb-1.5 uppercase tracking-widest opacity-60 flex items-center gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.sender === 'user' ? (
                    <>
                      <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      <span className="w-1 h-1 rounded-full bg-white/40" />
                      <span>Authenticated User</span>
                    </>
                  ) : (
                    <>
                      <Cpu className="w-3 h-3" />
                      <span>PureCortex Brain v1</span>
                      <span className="w-1 h-1 rounded-full bg-blue-400/40" />
                      <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </>
                  )}
                </div>
                <div className="text-[15px] leading-relaxed font-sans">{msg.text}</div>
              </div>
            </motion.div>
          ))}
          
          {isTyping && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-[#1E1E26] p-4 rounded-2xl rounded-tl-none border border-white/5 flex gap-1.5">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="p-6 bg-[#16161D]/50 backdrop-blur-xl border-t border-white/5 flex gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Transmit command or query..."
            className="w-full bg-[#1C1C24] text-white border border-white/5 rounded-xl px-5 py-3.5 outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all placeholder:text-gray-600"
          />
          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2 text-gray-500">
             <kbd className="hidden sm:inline-flex px-1.5 py-0.5 rounded border border-white/10 text-[10px] font-mono">⌘</kbd>
             <kbd className="hidden sm:inline-flex px-1.5 py-0.5 rounded border border-white/10 text-[10px] font-mono">K</kbd>
          </div>
        </div>
        <button 
          type="submit" 
          disabled={!isConnected || !input.trim()}
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed text-white px-5 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-95 flex items-center justify-center"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Footer Info */}
      <div className="px-6 py-3 bg-[#0D0D12] border-t border-white/5 flex flex-wrap justify-between items-center text-[10px] text-gray-500 font-mono">
        <div className="flex items-center gap-4">
           <span className="flex items-center gap-1"><Info className="w-3 h-3" /> E2E Encrypted</span>
           <span className="flex items-center gap-1 text-emerald-500/70"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Algorand Testnet Live</span>
        </div>
        <div>
           PURECORTEX_AUTH_ID: 0x889...F22A
        </div>
      </div>
    </div>
  );
}
