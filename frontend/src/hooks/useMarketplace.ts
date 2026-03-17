'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchAgents, fetchMarketplaceConfig, AgentData, MarketplaceConfig } from '@/lib/marketplace';

const POLL_INTERVAL = 30_000; // 30 seconds

export function useMarketplace() {
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [config, setConfig] = useState<MarketplaceConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [marketplaceConfig, data] = await Promise.all([
        fetchMarketplaceConfig(),
        fetchAgents(),
      ]);
      setConfig(marketplaceConfig);
      setAgents(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refresh]);

  return { agents, config, loading, error, refresh };
}
