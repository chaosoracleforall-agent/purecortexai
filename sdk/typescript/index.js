const DEFAULT_BASE_URL = "https://purecortex.ai";

export class PureCortexApiError extends Error {
  constructor({ statusCode, detail, payload = null }) {
    super(`PURECORTEX API error ${statusCode}: ${detail}`);
    this.name = "PureCortexApiError";
    this.statusCode = statusCode;
    this.detail = detail;
    this.payload = payload;
  }

  static async fromResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    let payload = null;
    let detail = await response.text();

    if (contentType.includes("application/json")) {
      try {
        payload = JSON.parse(detail || "{}");
        if (payload && typeof payload === "object") {
          detail = payload.detail || payload.error || detail;
        }
      } catch {
        payload = null;
      }
    }

    return new PureCortexApiError({
      statusCode: response.status,
      detail,
      payload,
    });
  }
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
}

function toWebSocketBaseUrl(baseUrl) {
  const url = new URL(normalizeBaseUrl(baseUrl));
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "";
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/+$/, "");
}

export class PureCortexClient {
  constructor(options = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl || DEFAULT_BASE_URL);
    this.apiKey = options.apiKey ?? null;
    this.fetchImpl = options.fetchImpl || globalThis.fetch?.bind(globalThis);
    this.WebSocketImpl = options.WebSocketImpl || globalThis.WebSocket || null;
    this.defaultHeaders = { ...(options.headers || {}) };

    if (!this.fetchImpl) {
      throw new Error(
        "A fetch implementation is required. Pass fetchImpl when global fetch is unavailable."
      );
    }
  }

  get wsBaseUrl() {
    return toWebSocketBaseUrl(this.baseUrl);
  }

  websocketUrl(sessionToken) {
    const query = new URLSearchParams({ session: sessionToken });
    return `${this.wsBaseUrl}/ws/chat?${query.toString()}`;
  }

  health() {
    return this.#request("GET", "/health");
  }

  supply() {
    return this.#request("GET", "/api/transparency/supply");
  }

  treasury() {
    return this.#request("GET", "/api/transparency/treasury");
  }

  burns() {
    return this.#request("GET", "/api/transparency/burns");
  }

  governanceTransparency() {
    return this.#request("GET", "/api/transparency/governance");
  }

  transparencyAgents() {
    return this.#request("GET", "/api/transparency/agents");
  }

  listAgents() {
    return this.#request("GET", "/api/agents/registry");
  }

  agentActivity(agentName) {
    return this.#request("GET", `/api/agents/${agentName}/activity`);
  }

  chat(agentName, message, options = {}) {
    return this.#request("POST", `/api/agents/${agentName}/chat`, {
      requireApiKey: true,
      apiKey: options.apiKey,
      body: { message },
    });
  }

  createChatSession(options = {}) {
    return this.#request("POST", "/api/chat/session", {
      requireApiKey: true,
      apiKey: options.apiKey,
    });
  }

  async connectChat(options = {}) {
    const sessionToken =
      options.sessionToken ||
      (await this.createChatSession({ apiKey: options.apiKey })).session_token;

    const WebSocketCtor = options.WebSocketImpl || this.WebSocketImpl;
    if (!WebSocketCtor) {
      throw new Error(
        "A WebSocket implementation is required. Pass WebSocketImpl when global WebSocket is unavailable."
      );
    }

    return new WebSocketCtor(this.websocketUrl(sessionToken), options.protocols);
  }

  constitution() {
    return this.#request("GET", "/api/governance/constitution");
  }

  governanceOverview() {
    return this.#request("GET", "/api/governance/overview");
  }

  listProposals() {
    return this.#request("GET", "/api/governance/proposals");
  }

  proposal(proposalId) {
    return this.#request("GET", `/api/governance/proposals/${proposalId}`);
  }

  onchainProposals() {
    return this.#request("GET", "/api/governance/onchain");
  }

  createProposal({ title, description, proposer, proposalType = "general" }) {
    return this.#request("POST", "/api/governance/proposals", {
      body: {
        title,
        description,
        proposer,
        type: proposalType,
      },
    });
  }

  reviewProposal(proposalId, body) {
    return this.#request("POST", `/api/governance/proposals/${proposalId}/review`, {
      body,
    });
  }

  vote(proposalId, body) {
    return this.#request("POST", `/api/governance/proposals/${proposalId}/vote`, {
      body,
    });
  }

  bootstrapAdminKey({ owner = "bootstrap-admin", bootstrapToken }) {
    return this.#request("POST", "/api/admin/bootstrap", {
      headers: { "X-Bootstrap-Token": bootstrapToken },
      body: { owner },
    });
  }

  createApiKey({ owner, tier = "free", adminSecret, adminApiKey }) {
    const headers = {};
    if (adminSecret) {
      headers["X-Admin-Secret"] = adminSecret;
    }
    return this.#request("POST", "/api/admin/keys", {
      headers,
      apiKey: adminApiKey,
      body: { owner, tier },
    });
  }

  revokeApiKey({ apiKeyToRevoke, adminSecret, adminApiKey }) {
    const headers = {};
    if (adminSecret) {
      headers["X-Admin-Secret"] = adminSecret;
    }
    return this.#request("POST", "/api/admin/keys/revoke", {
      headers,
      apiKey: adminApiKey,
      body: { api_key: apiKeyToRevoke },
    });
  }

  async #request(method, path, options = {}) {
    const headers = this.#headers(options);
    const url = new URL(path, `${this.baseUrl}/`);

    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        if (value === undefined || value === null) {
          continue;
        }
        url.searchParams.set(key, String(value));
      }
    }

    const response = await this.fetchImpl(url, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      throw await PureCortexApiError.fromResponse(response);
    }

    return response.json();
  }

  #headers(options = {}) {
    const headers = {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...this.defaultHeaders,
      ...(options.headers || {}),
    };

    const apiKey = options.apiKey || this.apiKey;
    if (options.requireApiKey && !apiKey) {
      throw new Error("PURECORTEX API key is required for this operation.");
    }
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    return headers;
  }
}
