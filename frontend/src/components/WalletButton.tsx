'use client';

import { PeraWalletConnect } from "@perawallet/connect";
import { useState, useEffect } from "react";
import { Wallet, LogOut, ChevronDown } from "lucide-react";

const peraWallet = new PeraWalletConnect();

export default function WalletButton() {
  const [accountAddress, setAccountAddress] = useState<string | null>(null);

  useEffect(() => {
    // Reconnect to the session when the component is mounted
    peraWallet.reconnectSession().then((accounts) => {
      if (accounts.length) {
        setAccountAddress(accounts[0]);
      }
    });
  }, []);

  function handleConnectWalletClick() {
    peraWallet.connect().then((newAccounts) => {
      setAccountAddress(newAccounts[0]);
    });
  }

  function handleDisconnectWalletClick() {
    peraWallet.disconnect();
    setAccountAddress(null);
  }

  return (
    <div>
      {!accountAddress ? (
        <button
          onClick={handleConnectWalletClick}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-95"
        >
          <Wallet className="w-4 h-4" />
          Connect Wallet
        </button>
      ) : (
        <div className="flex items-center gap-2 bg-[#16161D] border border-white/5 pl-4 pr-2 py-1.5 rounded-xl">
           <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
           <span className="text-sm font-mono text-gray-300">
             {accountAddress.substring(0, 6)}...{accountAddress.substring(accountAddress.length - 4)}
           </span>
           <button 
             onClick={handleDisconnectWalletClick}
             className="p-2 hover:bg-white/5 rounded-lg text-gray-500 hover:text-rose-400 transition-colors"
           >
             <LogOut className="w-4 h-4" />
           </button>
        </div>
      )}
    </div>
  );
}
