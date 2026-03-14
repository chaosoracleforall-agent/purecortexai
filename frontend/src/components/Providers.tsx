'use client';

import { ReactNode } from 'react';
import {
  WalletProvider,
  WalletManager,
  WalletId,
  NetworkId,
} from '@txnlab/use-wallet-react';

const walletManager = new WalletManager({
  wallets: [
    WalletId.PERA,
    WalletId.DEFLY,
    WalletId.EXODUS,
    WalletId.LUTE,
    WalletId.KIBISIS,
  ],
  defaultNetwork: NetworkId.TESTNET,
});

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <WalletProvider manager={walletManager}>
      {children}
    </WalletProvider>
  );
}
