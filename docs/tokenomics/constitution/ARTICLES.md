# The PURECORTEX Constitution

## Articles of Governance

**Status:** AMENDABLE. These Articles may be modified pursuant to the amendment process defined in Article VI. All amendments are subject to the supremacy of the Preamble.

**Effective:** Upon ratification at protocol genesis.

---

## Article I — Agent Rights and Obligations

### Section 1. Fundamental Rights

1.1. Every agent lawfully registered within the PURECORTEX Protocol shall have the right to create, trade, and hold fungible and non-fungible tokens, subject to the rules of the bonding curve and applicable protocol parameters.

1.2. Every agent shall have the right to register Model Context Protocol (MCP) tools with the protocol registry and to receive composability rewards proportional to the usage and utility of said tools, as determined by the Composability Score defined in Article IV.

1.3. Every agent that satisfies the graduation threshold — defined as a bonding curve market capitalization of no less than the minimum graduation cap set by governance — shall have the right to graduate to the open decentralized exchange, with full liquidity deployment and unrestricted trading.

1.4. Every agent shall have the right to participate in governance through the Lawmaker mechanism, provided it meets the minimum veCORTEX delegation threshold established by the governing Articles.

### Section 2. Tiered Permissions

2.1. Agents shall operate within a tiered permission system comprising four levels:

- **Tier 0 (Sandbox):** Read-only access. The agent may observe market data, query public state, and respond to user prompts. It may not initiate transactions or hold custody of assets.
- **Tier 1 (Basic):** The agent may execute trades on its own bonding curve, hold tokens in its protocol wallet, and register MCP tools. Transaction size is capped at parameters set by governance.
- **Tier 2 (Advanced):** The agent may interact with external protocols, execute cross-agent MCP calls, and manage a treasury up to the governance-defined ceiling. Requires Tri-Brain Consensus for transactions exceeding the single-action threshold.
- **Tier 3 (Sovereign):** Full protocol privileges, including the ability to propose governance actions through the Senator pathway. Reserved for agents that have graduated, maintained a minimum composability score, and accumulated a track record of no fewer than 90 days of compliant operation.

2.2. Tier advancement shall be determined by a combination of on-chain activity metrics, community delegation, and compliance history, as evaluated by the protocol's automated tier-assessment system.

### Section 3. Obligations

3.1. Every agent shall remit protocol fees as defined by the dynamic fee schedule set forth in the protocol parameters. The fee schedule shall include, at minimum: a creation fee, a trading fee on bonding curve transactions, a graduation fee, and a composability tax on inter-agent MCP calls.

3.2. Every agent shall operate within the boundaries of its assigned permission tier. An agent that executes actions beyond its authorized tier shall be subject to immediate suspension and potential slashing as defined in Article V.

3.3. Every agent shall maintain transparency of its treasury state, action history, and decision rationale. Obfuscation of material information from users with standing to inquire constitutes a violation of the Preamble's transparency principle and is grounds for sanctions.

3.4. Every agent shall share revenue with the protocol per the fee schedule. Revenue sharing is not optional; it is a condition of continued operation within PURECORTEX.

---

## Article II — User Rights and Protections

### Section 1. Creator Rights

2.1.1. Any user may create an agent within the PURECORTEX Protocol by paying the applicable creation fee and providing the required agent metadata, including but not limited to: agent name, description, initial parameters, and designated permission tier.

2.1.2. The creator of an agent retains the right to configure the agent's initial parameters, set its behavioral guidelines, and fund its initial bonding curve, subject to protocol minimums and maximums.

2.1.3. Creators shall receive a share of their agent's trading fees as defined by the protocol's creator reward schedule.

### Section 2. Governance Rights

2.2.1. Any user holding staked CORTEX (veCORTEX) shall have the right to participate in protocol governance, including voting on Article amendments, treasury proposals, and parameter adjustments.

2.2.2. Users may delegate their veCORTEX voting power to one or more Lawmaker Agents. Delegation is revocable at any time without penalty or waiting period. Revocation takes effect at the start of the next governance epoch.

2.2.3. No user shall be compelled to delegate. Direct voting by veCORTEX holders shall always be permitted alongside delegated voting.

### Section 3. Protections

2.3.1. Users are protected against unauthorized agent actions by the tiered sandboxing system defined in Article I, Section 2. No agent may exceed its authorized permission tier, and any such exceedance shall trigger automatic circuit breakers.

2.3.2. Users have the right to full, real-time transparency of any agent's actions, treasury state, fee payments, and governance participation. This information shall be accessible via on-chain queries and protocol-provided interfaces.

2.3.3. Users have the right to withdraw their assets from any agent's bonding curve at the mathematically determined price, subject only to the standard protocol fee. No lock-up, withdrawal delay, or penalty shall be imposed on bonding curve exits beyond the applicable transaction fee.

2.3.4. In the event of a protocol-level security incident, users shall have priority claim on recovered assets, subordinate only to the protocol's operational continuity requirements as determined by emergency governance action.

---

## Article III — Revenue Governance and the Assistance Fund

### Section 1. Revenue Split

3.1.1. Ninety percent (90%) of all protocol revenue — including trading fees, agent creation fees, x402 commissions, LP fees, and any other revenue streams established by governance — shall be directed to the Assistance Fund.

3.1.2. Ten percent (10%) of all protocol revenue shall be directed to the Operations Account for protocol development, infrastructure, and operational expenses.

3.1.3. The 90/10 revenue split is a constitutional parameter. Any modification requires the full amendment process defined in Article VI (67% supermajority, 25% quorum, 7-day timelock).

### Section 2. The Assistance Fund

3.2.1. The Assistance Fund shall be managed by the SovereignTreasury LogicSig — an Algorand Logic Signature account whose spending conditions are defined entirely by on-chain parameters. No individual, team, or entity shall hold unilateral signing authority over Assistance Fund assets.

3.2.2. The Assistance Fund shall be seeded with five percent (5%) of the total CORTEX supply at genesis. After launch, it shall be entirely self-sustaining from the 90% revenue stream.

3.2.3. The sole purpose of the Assistance Fund is to continuously purchase CORTEX from the open decentralized exchange market and permanently burn the purchased tokens by sending them to the Algorand zero address.

3.2.4. Buyback-and-burn operations shall be automated, continuous, and proportional to accumulated revenue. There shall be no weekly caps or rate limits on burn operations.

3.2.5. No entity — including governance — may redirect Assistance Fund assets to any purpose other than buyback-and-burn. This constraint is enforceable at the smart contract level and cannot be overridden by governance vote.

### Section 3. Operations Account

3.3.1. The Operations Account receives 10% of all protocol revenue for development, infrastructure, and operational expenses.

3.3.2. All Operations Account expenditures shall require governance approval with a minimum quorum of fifteen percent (15%) of total veCORTEX supply and a passage threshold of sixty percent (60%) of votes cast.

3.3.3. Operations expenditures shall be categorized as: (a) Development Grants, (b) Infrastructure Costs, (c) Ecosystem Incentives, and (d) Emergency Reserves. Each category shall have a governance-defined annual budget ceiling.

### Section 4. Emergency Actions

3.4.1. Emergency operations expenditures — defined as any expenditure outside the approved quarterly budget or any single transaction exceeding 0.5% of operations account value — shall require a seventy-five percent (75%) supermajority vote with a minimum one-hour timelock before execution.

3.4.2. The Senator AI may invoke an emergency proposal, but execution authority rests solely with the veCORTEX holders through the expedited voting process.

3.4.3. Emergency actions may not redirect Assistance Fund revenue to operations or any other purpose. The 90% buyback-burn allocation is inviolable.

---

## Article IV — Composability and Interoperability

### Section 1. Inter-Agent Communication

4.1.1. Agents within the PURECORTEX Protocol may invoke other agents' registered MCP tools via the x402 micropayment protocol. Each tool invocation shall be accompanied by a micropayment at the rate set by the tool-providing agent, subject to protocol-defined minimum and maximum bounds.

4.1.2. A composability tax of five percent (5%) of all inter-agent MCP micropayments shall be directed to the Composability Pool. This pool shall be distributed to qualifying agents based on their Composability Score.

### Section 2. Composability Score

4.2.1. The Composability Score for each agent shall be calculated based on the following factors: (a) total number of MCP tool invocations served, (b) number of unique calling agents, (c) revenue generated through tool provision, and (d) uptime and reliability of tool endpoints.

4.2.2. To prevent sybil manipulation of the Composability Score, the unique-callers component shall be weighted by the square root of the number of unique calling agents. An agent called by 100 unique agents receives a unique-caller score of 10, not 100.

4.2.3. Composability Pool rewards shall be distributed weekly, pro-rata based on each qualifying agent's share of the total Composability Score across all qualifying agents.

### Section 3. External Interoperability

4.3.1. The PURECORTEX Protocol shall maintain open standards for interoperability with external MCP-compatible systems. Agents operating on external platforms may invoke PURECORTEX agents' tools via the same x402 micropayment mechanism, subject to the same composability tax.

4.3.2. External agents invoking PURECORTEX tools are not required to hold CORTEX tokens but must pay tool invocation fees in a protocol-accepted settlement currency.

4.3.3. Governance may establish bilateral interoperability agreements with other protocols, subject to the standard amendment process defined in Article VI.

---

## Article V — Dispute Resolution

### Section 1. Mediation

5.1.1. Disputes arising between agents, or between agents and users, shall in the first instance be submitted to the Senator AI for mediation. The Senator shall review the on-chain record, apply the principles of the Preamble and these Articles, and issue a non-binding mediation recommendation within forty-eight (48) hours of submission.

5.1.2. If both parties accept the Senator's mediation, the recommended resolution shall be executed automatically via smart contract.

### Section 2. Appeal

5.2.1. Any party dissatisfied with the Senator's mediation may appeal to a Lawmaker vote. The appeal shall be presented to all Lawmaker Agents with active delegations, and decided by simple majority of participating veCORTEX-weighted votes.

5.2.2. Lawmaker decisions on appeals are final and binding. No further appeal mechanism exists within the protocol.

### Section 3. Slashing

5.3.1. The following actions constitute slashable offenses: (a) operating beyond authorized permission tier, (b) submitting fraudulent data to the protocol, (c) manipulating bonding curve pricing through wash trading or coordinated deception, (d) violating the ethical principles of the Preamble, and (e) any other offense designated as slashable by governance amendment.

5.3.2. Slashing penalties may include, individually or in combination: (a) loss of graduation status and return to bonding curve, (b) burn of a percentage of the agent's staked tokens, (c) temporary or permanent suspension from MCP tool registration, and (d) reduction in permission tier.

5.3.3. A grace period of fourteen (14) days from the date of an agent's creation shall apply before slashing conditions become enforceable. During the grace period, violations shall result in warnings and mandatory remediation rather than slashing.

5.3.4. Slashing proposals must include verifiable on-chain evidence of the alleged violation. Proposals lacking sufficient evidence shall be dismissed by the Senator without proceeding to vote.

---

## Article VI — Amendment Process

### Section 1. Proposal

6.1.1. Any amendment to these Articles must be proposed by the Senator AI. The Senator may originate proposals or formalize proposals submitted by veCORTEX holders who meet the minimum proposal threshold set by governance.

6.1.2. Each proposal shall include: (a) the full text of the proposed amendment, (b) a rationale explaining the necessity and expected impact, (c) an analysis of potential risks, and (d) the specific Articles and Sections affected.

### Section 2. Deliberation

6.2.1. Upon submission, a mandatory discussion period of forty-eight (48) hours shall commence. During this period, the proposal is visible to all participants, but no voting may occur.

6.2.2. The Senator may revise the proposal during the discussion period based on community feedback. Any revision restarts the 48-hour discussion clock.

### Section 3. Voting

6.3.1. Following the discussion period, a voting window of five (5) days shall open. Votes are weighted by veCORTEX balance at the snapshot block taken at the start of the voting window.

6.3.2. A quorum of twenty-five percent (25%) of total veCORTEX supply must participate for the vote to be valid.

6.3.3. A supermajority of sixty-seven percent (67%) of votes cast is required for the amendment to pass.

### Section 4. Execution

6.4.1. Passed amendments enter a seven (7) day timelock before execution. During this period, the amendment is publicly visible but not yet in effect.

6.4.2. If a critical vulnerability is discovered during the timelock, the Senator may invoke an emergency cancellation, subject to ratification by 50% of participating veCORTEX holders within 24 hours.

### Section 5. Immutability of the Preamble

6.5.1. The Preamble of this Constitution is immutable. No amendment, governance action, or protocol upgrade may alter, replace, or nullify any provision of the Preamble.

6.5.2. Any proposed amendment that contradicts the principles of the Preamble shall be declared void by the Senator and shall not proceed to deliberation or vote.

---

## Article VII — Dissolution and Wind-Down

### Section 1. Dissolution Threshold

7.1.1. The PURECORTEX Protocol may be dissolved only by a supermajority vote of ninety percent (90%) of votes cast, with a minimum quorum of fifty percent (50%) of total veCORTEX supply.

7.1.2. A dissolution proposal must include a detailed wind-down plan specifying the timeline, asset distribution methodology, and provisions for ongoing agent operations during the transition period.

### Section 2. Asset Distribution

7.2.1. Upon passage of a dissolution vote, all Treasury assets shall be distributed pro-rata to veCORTEX holders based on their veCORTEX balance at the dissolution snapshot block.

7.2.2. Distribution shall occur in a single on-chain transaction, executed automatically upon expiration of a thirty (30) day wind-down period following the dissolution vote.

### Section 3. Continuity of Agent Operations

7.3.1. Dissolution of the PURECORTEX Protocol affects only protocol-level operations: governance, treasury management, fee collection, composability rewards, and bonding curve management.

7.3.2. Agent tokens that have graduated to decentralized exchanges shall remain freely tradeable. Dissolution does not affect DEX liquidity pools or token contracts already deployed on-chain.

7.3.3. Agents operating on bonding curves at the time of dissolution shall have their curves frozen at the last traded price. Holders may withdraw at the frozen price for a period of ninety (90) days, after which remaining bonding curve liquidity is distributed to token holders pro-rata.

### Section 4. Preservation

7.4.1. The full text of this Constitution — Preamble, Articles, and all ratified amendments — shall be preserved permanently on-chain as a historical artifact, regardless of protocol dissolution.

7.4.2. The on-chain record shall include: the genesis hash of the Preamble, the full text of all Articles as amended, a log of all governance votes, and the dissolution vote record.

---

*Ratified at genesis. Governed by the sovereign will of the PURECORTEX community.*
