'use client';

import { useWallet } from '@txnlab/use-wallet-react';
import { useState, useEffect, useCallback } from 'react';
import { Wallet, LogOut, ChevronDown, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function WalletButton() {
  const { wallets, activeWallet, activeAccount } = useWallet();
  const [isOpen, setIsOpen] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && isOpen) setIsOpen(false);
  }, [isOpen]);

  useEffect(() => {
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [handleEscape]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  async function handleConnect(walletId: string) {
    const wallet = wallets?.find((w) => w.id === walletId);
    if (!wallet) return;
    setConnecting(walletId);
    try {
      await wallet.connect();
      setIsOpen(false);
    } catch {
      // Connection cancelled or rejected by user
    } finally {
      setConnecting(null);
    }
  }

  async function handleDisconnect() {
    if (activeWallet) {
      await activeWallet.disconnect();
    }
  }

  if (activeAccount) {
    return (
      <div className="flex items-center gap-2 bg-[#16161D] border border-white/5 pl-4 pr-2 py-1.5 rounded-xl">
        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-sm font-mono text-gray-300">
          {activeAccount.address.substring(0, 6)}...{activeAccount.address.substring(activeAccount.address.length - 4)}
        </span>
        <button
          onClick={handleDisconnect}
          aria-label="Disconnect wallet"
          className="p-2 hover:bg-white/5 rounded-lg text-gray-500 hover:text-rose-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 bg-[#007AFF] hover:bg-[#0062CC] text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-[#007AFF]/20 active:scale-95"
      >
        <Wallet className="w-4 h-4" />
        Connect Wallet
      </button>

      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-[200] flex items-end sm:items-center justify-center sm:p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ y: '100%', opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: '100%', opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="bg-[#121217] border border-white/10 rounded-t-3xl sm:rounded-3xl p-6 sm:p-8 max-w-md w-full relative shadow-2xl z-[201] max-h-[85vh] overflow-y-auto"
            >
              <div className="w-10 h-1 bg-white/20 rounded-full mx-auto mb-4 sm:hidden" />
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close wallet modal"
                className="absolute top-4 right-4 sm:top-6 sm:right-6 p-2 text-gray-500 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>

              <h2 className="text-xl sm:text-2xl font-black tracking-tighter uppercase italic mb-2">
                Connect Wallet
              </h2>
              <p className="text-gray-500 text-xs mb-5 sm:mb-6 font-bold uppercase tracking-widest">
                Select your Algorand wallet
              </p>

              <div className="space-y-2 sm:space-y-3">
                {wallets?.map((wallet) => {
                  const isConnecting = connecting === wallet.id;
                  const rawIconUrl = wallet.metadata?.icon;
                  const iconUrl = rawIconUrl && (rawIconUrl.startsWith('https://') || rawIconUrl.startsWith('data:image/')) ? rawIconUrl : undefined;
                  const walletName = wallet.metadata?.name || wallet.id;

                  return (
                    <button
                      key={wallet.id}
                      onClick={() => handleConnect(wallet.id)}
                      disabled={isConnecting}
                      className="w-full flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl bg-[#050505] border border-white/5 hover:border-[#007AFF]/40 transition-all group disabled:opacity-50 active:scale-[0.98]"
                    >
                      <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-white/5 flex items-center justify-center overflow-hidden flex-shrink-0">
                        {iconUrl ? (
                          <img
                            src={iconUrl}
                            alt={walletName}
                            className="w-6 h-6 sm:w-7 sm:h-7 object-contain"
                          />
                        ) : (
                          <Wallet className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                      <span className="text-sm font-bold text-white uppercase tracking-wider">
                        {walletName}
                      </span>
                      {isConnecting && (
                        <span className="ml-auto text-[10px] text-[#007AFF] font-mono uppercase tracking-widest animate-pulse">
                          Connecting...
                        </span>
                      )}
                      {!isConnecting && (
                        <ChevronDown className="ml-auto w-4 h-4 text-gray-700 group-hover:text-[#007AFF] -rotate-90 transition-colors" />
                      )}
                    </button>
                  );
                })}
              </div>

              <p className="text-[9px] text-gray-600 text-center mt-5 sm:mt-6 font-mono uppercase tracking-widest">
                Powered by Algorand • Testnet
              </p>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
