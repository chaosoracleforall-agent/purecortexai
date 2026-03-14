import React from 'react';

export const AtomicNeuron = ({ className = "w-8 h-8", glow = true }) => {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {glow && (
        <div className="absolute inset-0 bg-[#007AFF]/20 blur-xl rounded-full scale-125 animate-pulse" />
      )}
      <svg
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10"
      >
        <circle cx="100" cy="100" r="80" stroke="#007AFF" strokeWidth="2" opacity="0.3"/>
        <circle cx="100" cy="100" r="40" stroke="#007AFF" strokeWidth="4"/>
        <path d="M80 100 Q100 60 120 100 T160 100" stroke="#007AFF" strokeWidth="3" strokeLinecap="round"/>
        <circle cx="100" cy="100" r="5" fill="#007AFF"/>
      </svg>
    </div>
  );
};

export const PureCortexLogo = ({ className = "h-8" }) => {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="w-8 h-8 rounded-lg bg-[#007AFF] flex items-center justify-center shadow-[0_0_15px_rgba(0,122,255,0.4)]">
         <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
      </div>
      <span className="text-3xl font-black tracking-tight text-white font-sans uppercase">
        Pure<span className="text-[#007AFF]">Cortex</span>
      </span>
    </div>
  );
};
