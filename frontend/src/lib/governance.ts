export const SIGNED_VOTE_CONTEXT = 'PURECORTEX_GOVERNANCE_VOTE_V1';

export interface GovernanceVotePower {
  proposal_id: number;
  voter: string;
  direct_weight: number;
  delegated_weight: number;
  effective_weight: number;
}

export interface StakingOverview {
  app_id: number;
  cortex_asset_id: number;
  total_staked: number;
  reward_pool: number;
  min_lock_days: number;
  max_lock_days: number;
  max_boost_bps: number;
  current_round: number;
}

export interface StakingAccount {
  address: string;
  has_active_stake: boolean;
  amount: number;
  unlock_round: number | null;
  current_round: number;
  lock_days_remaining: number;
  ve_power: number;
  boost_bps: number;
  delegate: string | null;
  delegated_power_received: number;
  delegated_amount_received: number;
  delegator_count: number;
}

export function buildSignedVoteMessage({
  proposalId,
  voter,
  vote,
  issuedAt,
  nonce,
}: {
  proposalId: number;
  voter: string;
  vote: 'for' | 'against';
  issuedAt: string;
  nonce: string;
}): string {
  return [
    SIGNED_VOTE_CONTEXT,
    `proposal_id:${proposalId}`,
    `vote:${vote}`,
    `voter:${voter}`,
    `issued_at:${issuedAt}`,
    `nonce:${nonce}`,
  ].join('\n');
}

export function bytesToBase64(value: Uint8Array): string {
  let binary = '';
  for (const byte of value) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}
