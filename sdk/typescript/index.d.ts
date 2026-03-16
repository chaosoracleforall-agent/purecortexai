export type AgentName = "senator" | "curator" | "social";
export type VoteChoice = "for" | "against";

export interface HealthResponse {
  status: string;
  version: string;
  dependencies: {
    redis: string;
    orchestrator: string;
    agent_loop: string;
  };
}

export interface ChatSessionResponse {
  session_token: string;
  expires_at: string;
  ttl_seconds: number;
  owner: string;
  tier: string;
}

export interface AgentRecord {
  name: string;
  role: AgentName;
  description: string;
  algorand_address: string | null;
  status: string;
  permission_tier: number;
  capabilities: string[];
  created_at: string;
}

export interface AgentRegistryResponse {
  total_agents: number;
  agents: AgentRecord[];
}

export interface AgentActivityResponse {
  agent: string;
  total_actions: number;
  recent_activity: Array<{
    action: string;
    detail: string;
    timestamp: string;
    txn_id?: string | null;
  }>;
  note?: string | null;
}

export interface ChatResponse {
  agent: string;
  response: string;
  timestamp: string;
}

export interface GovernanceOverviewResponse {
  total_proposals: number;
  active_proposals: number;
  voting_proposals: number;
  passed_proposals: number;
  rejected_proposals: number;
  total_votes: number;
}

export interface ProposalsListResponse {
  total: number;
  proposals: Array<Record<string, unknown>>;
}

export interface ProposalDetailResponse extends Record<string, unknown> {
  id: number;
  title: string;
  description: string;
  type: string;
  status: string;
  proposer: string;
  created_at: string;
  votes_for: number;
  votes_against: number;
  voters: string[];
}

export interface SupplyResponse {
  total_supply: number;
  circulating: number;
  burned: number;
  vesting: {
    released: number;
    remaining: number;
    pct_released: number;
    tge_date: string;
    vest_days: number;
  };
  allocation: Array<{
    label: string;
    pct: number;
    amount: number;
  }>;
}

export interface TreasuryResponse extends Record<string, unknown> {}
export interface BurnsResponse extends Record<string, unknown> {}
export interface GovernanceTransparencyResponse extends Record<string, unknown> {}
export interface TransparencyAgentsResponse extends Record<string, unknown> {}
export interface ConstitutionResponse extends Record<string, unknown> {}
export interface OnchainProposalsResponse extends Record<string, unknown> {}

export interface CreateProposalInput {
  title: string;
  description: string;
  proposer: string;
  proposalType?: string;
}

export interface ReviewProposalInput {
  compliant: boolean;
  analysis: string;
  recommendation: string;
  curator_name: string;
}

export interface VoteProposalInput {
  voter: string;
  vote: VoteChoice;
  weight?: number;
}

export interface BootstrapAdminInput {
  owner?: string;
  bootstrapToken: string;
}

export interface CreateApiKeyInput {
  owner: string;
  tier?: string;
  adminSecret?: string;
  adminApiKey?: string;
}

export interface RevokeApiKeyInput {
  apiKeyToRevoke: string;
  adminSecret?: string;
  adminApiKey?: string;
}

export interface PureCortexClientOptions {
  baseUrl?: string;
  apiKey?: string | null;
  fetchImpl?: typeof fetch;
  WebSocketImpl?: typeof WebSocket | null;
  headers?: Record<string, string>;
}

export interface ChatConnectionOptions {
  sessionToken?: string;
  apiKey?: string;
  WebSocketImpl?: typeof WebSocket | null;
  protocols?: string | string[];
}

export class PureCortexApiError extends Error {
  statusCode: number;
  detail: string;
  payload: unknown;

  constructor(args: { statusCode: number; detail: string; payload?: unknown });
  static fromResponse(response: Response): Promise<PureCortexApiError>;
}

export class PureCortexClient {
  constructor(options?: PureCortexClientOptions);

  baseUrl: string;
  apiKey: string | null;
  readonly wsBaseUrl: string;

  websocketUrl(sessionToken: string): string;

  health(): Promise<HealthResponse>;
  supply(): Promise<SupplyResponse>;
  treasury(): Promise<TreasuryResponse>;
  burns(): Promise<BurnsResponse>;
  governanceTransparency(): Promise<GovernanceTransparencyResponse>;
  transparencyAgents(): Promise<TransparencyAgentsResponse>;
  listAgents(): Promise<AgentRegistryResponse>;
  agentActivity(agentName: AgentName): Promise<AgentActivityResponse>;
  chat(agentName: AgentName, message: string, options?: { apiKey?: string }): Promise<ChatResponse>;
  createChatSession(options?: { apiKey?: string }): Promise<ChatSessionResponse>;
  connectChat(options?: ChatConnectionOptions): Promise<WebSocket>;
  constitution(): Promise<ConstitutionResponse>;
  governanceOverview(): Promise<GovernanceOverviewResponse>;
  listProposals(): Promise<ProposalsListResponse>;
  proposal(proposalId: number): Promise<ProposalDetailResponse>;
  onchainProposals(): Promise<OnchainProposalsResponse>;
  createProposal(input: CreateProposalInput): Promise<ProposalDetailResponse>;
  reviewProposal(proposalId: number, body: ReviewProposalInput): Promise<ProposalDetailResponse>;
  vote(proposalId: number, body: VoteProposalInput): Promise<Record<string, unknown>>;
  bootstrapAdminKey(input: BootstrapAdminInput): Promise<Record<string, unknown>>;
  createApiKey(input: CreateApiKeyInput): Promise<Record<string, unknown>>;
  revokeApiKey(input: RevokeApiKeyInput): Promise<Record<string, unknown>>;
}
