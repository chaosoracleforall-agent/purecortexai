'use client';

import { useWallet } from '@txnlab/use-wallet-react';
import { useState } from 'react';
import { Wallet, LogOut, ChevronDown, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const WALLET_META: Record<string, { name: string; icon: string }> = {
  pera: { name: 'Pera Wallet', icon: '🟢' },
  defly: { name: 'Defly', icon: '🦅' },
  exodus: { name: 'Exodus', icon: '🌀' },
  lute: { name: 'Lute', icon: '🎸' },
  kibisis: { name: 'Kibisis', icon: '🔑' },
  walletconnect: { name: 'WalletConnect', icon: '🔗' },
};

export default function WalletButton() {
  const { wallets, activeWallet, activeAccount } = useWallet();
  const [isOpen, setIsOpen] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);

  async function handleConnect(walletId: string) {
    const wallet = wallets?.find((w) => w.id === walletId);
    if (!wallet) return;
    setConnecting(walletId);
    try {
      await wallet.connect();
      setIsOpen(false);
    } catch (err) {
      console.error(`Failed to connect ${walletId}:`, err);
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
          <div className="fixed inset-0 z-[200] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="bg-[#121217] border border-white/10 rounded-[32px] p-8 max-w-md w-full relative shadow-2xl z-[201]"
            >
              <button
                onClick={() => setIsOpen(false)}
                className="absolute top-6 right-6 p-2 text-gray-500 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>

              <h2 className="text-2xl font-black tracking-tighter uppercase italic mb-2">
                Connect Wallet
              </h2>
              <p className="text-gray-500 text-xs mb-6 font-bold uppercase tracking-widest">
                Select your Algorand wallet
              </p>

              <div className="space-y-3">
                {wallets?.map((wallet) => {
                  const meta = WALLET_META[wallet.id] || {
                    name: wallet.id,
                    icon: '💳',
                  };
                  const isConnecting = connecting === wallet.id;

                  return (
                    <button
                      key={wallet.id}
                      onClick={() => handleConnect(wallet.id)}
                      disabled={isConnecting}
                      className="w-full flex items-center gap-4 p-4 rounded-xl bg-[#050505] border border-white/5 hover:border-[#007AFF]/40 transition-all group disabled:opacity-50"
                    >
                      <span className="text-2xl">{meta.icon}</span>
                      <span className="text-sm font-bold text-white uppercase tracking-wider">
                        {meta.name}
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

              <p className="text-[9px] text-gray-600 text-center mt-6 font-mono uppercase tracking-widest">
                Powered by Algorand
              </p>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
