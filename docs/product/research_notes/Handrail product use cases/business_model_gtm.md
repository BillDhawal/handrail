# Business models, pricing and go-to-market for UI automation / computer-use / "AI hands for legacy software" (as of October 2026)

Scope note. Researched 2026-10-31. Primary pricing pages were fetched directly where they exist; third-party trackers are flagged as such. Vendr figures are from Vendr's own anonymised transaction data and are not independently verified. Items marked UNVERIFIED came from a search summary whose underlying page was not fetched. The web-search budget ran out part-way through; the sections on Induced, Caddi, Magical, Nividous history, Sierra/Decagon/Hippocratic per-outcome prices, OpenAI app monetisation terms and credit-union deal sizes are therefore thinner than the rest.

## Q1. How do UiPath, Automation Anywhere, Power Automate, Zapier, Browserbase, Skyvern, Browser Use, TinyFish, Orby, Caddi, Induced price?

### Takeaway
Two pricing worlds coexist. Incumbent RPA sells annual licences per robot (roughly $8k-$10k list per unattended robot at UiPath, £8,000/yr per unattended runner package at Automation Anywhere, $150-$215/bot/month at Microsoft) and is now layering metered "units" for agents on top. The agent-era browser companies sell metered compute at commodity rates ($0.02-$0.12 per browser-hour) plus per-step or per-action agent fees ($0.006-$0.05 per step), and nearly all of them moved away from per-step toward monthly credit pools because per-step pricing punished reliability work.

### Cited Findings

UiPath
- Public plans: Community "free forever"; Basic "starting at $25 per month" with a 2-robot limit and up to 5 Basic / 5 Plus / 1 Pro user, EU-hosted only; Standard and Enterprise are "Contact Sales", with the footnote "Users and Robots may require additional license purchases". Test Cloud add-ons are priced publicly: Performance Testing $20K / 2,500 VUs, Screenplay $10K / 50K runs, Self-Healing $5K / 5K heals. — [UiPath pricing](https://www.uipath.com/pricing)
- Vendr transaction data: median UiPath contract $45,338/yr across 42 purchases, range $22,440-$223,821; list unattended robot $8,000-$10,000 per robot per year; attended $3,500-$5,000 per user per year; implementation services typically 50-150% of first-year licence; 5-10 robots $50K-$100K first year; 20-robot deal $150K-$300K/yr; 15-35% discounts for volume/multi-year; fiscal year ends Jan 31. — [Vendr UiPath](https://www.vendr.com/marketplace/uipath)
- Third-party estimates disagree widely: ~$1,680/robot/yr unattended and ~$420/user/yr attended ([Automation Atlas](https://automationatlas.io/answers/uipath-pricing-explained-2026/)); $6,000-$8,000/yr legacy per-robot ([Kaizen](https://www.kaizenautomation.com/blog/uipath-pricing)); $8,000-$15,000 list, $5,200-$9,750 negotiated ([Redress Compliance](https://redresscompliance.com/uipath-automation-negotiation-landing)); a flat "Unattended automation" plan at $1,380/month bundling one unattended plus one attended robot ([Capterra](https://www.capterra.com/p/135186/UiPath-Robotic-Process-Automation/pricing/)). Treat the Vendr figure as the best anchor.
- Two commercial frameworks: credit-based "Unified Pricing" (everything drawn from one Platform Unit pool) and licence-based "Flex" (separate Robot Units, AI Units, Apps Units, API Calls, Agent Units). — [Kaizen](https://www.kaizenautomation.com/blog/uipath-pricing)
- Agent Units are billed per LLM call in 64,000-input-token increments: premium model 2 units/call, standard 1, basic 0.8, custom model 1 per agent run; design/test runs are free. AI Units: Document Understanding 1 per page (2 with generative validation); GPU ML replica 20 units/hour. Autopilot ~0.2 Platform Units per action. Unit prices are not public. — [Nordflux](https://www.nordflux.de/en/insights/uipath-agentic-automation-what-autopilot-ai-center-and-agent-units-really-cost)

Automation Anywhere
- Official UK G-Cloud 15 list prices (GBP ex VAT, annual subscription, document dated 2026-01-29): Bot Creator £3,600; Control Room £11,500; Bot Runner Package (1 unattended runner + 1 creator) £8,000; Automation Co-Pilot Plus single user (1 attended runner + 1 Co-Pilot licence) £1,200; starter bundle of 2 Control Rooms + sandbox + 2 creators + 2 unattended runners + 10 Co-Pilot users £27,000; AAI Enterprise Platform with AI Agent Studio, 50K API tasks, 10 concurrent executions and 50K AI credits £99,500; AAI Enterprise Knowledge (240k credits/prompts) £99,500; Document Automation 50K pages £15,750; Document Automation Starter Pack £35,000. — [G-Cloud 15 pricing PDF](https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-15/documents/92299/835559348726219-pricing-document-2026-01-29-1523.pdf)
- Vendr: median $41,877/yr, range $11,378-$72,095; enterprise 50+ bot deployments cited at $500K to several million; 15-35% discounts; fiscal year ends April. — [Vendr Automation Anywhere](https://www.vendr.com/marketplace/automation-anywhere)
- The widely quoted "$750/month" is a 2020 starter-pack price (1 creator + 1 control room + 1 unattended runner), with extra unattended runners at $500/month and attended at $125/month; stale. Community Edition is free for organisations under 250 machines or under $5M revenue. — [eesel](https://www.eesel.ai/blog/automation-anywhere-pricing)

Microsoft Power Automate
- Premium $15/user/month (cloud flows + attended RPA); Process $150/bot/month (unattended RPA); Hosted Process $215/bot/month (adds a Microsoft-hosted VM); Process Mining add-on $5,000/tenant/month; Copilot Studio sold as prepaid Copilot Credit Commit Units with up to 20% discount for upfront purchase, pay-as-you-go overflow, Azure subscription required. — [Microsoft Power Automate pricing](https://www.microsoft.com/en-us/power-platform/products/power-automate/pricing)

Zapier
- A task is one successful action step; triggers and filters are free. Free 100 tasks; Pro 750 tasks $19.99/mo annual ($29.99 monthly); 2,000 tasks $49; 10,000 $129; 100,000 $489; 1M $2,199; 2M $3,389. Team starts at 2,000 tasks for $69. Overage at 1.25x base task rate on annual, 2.5x on monthly, hard stop at 3x. Zapier Agents is a separate add-on billed in "activities" (Pro ~$33.33/mo for 1,500 activities). — [Zapier pricing](https://zapier.com/pricing)

Browserbase
- Free $0: 3 concurrent, 1 browser hour, 15-minute session cap, 3 agent runs. Developer $20/mo: 25 concurrent, 100 hours, $0.12/hr overage, 1 GB proxy then $12/GB, 15 agent runs. Startup $99/mo: 100 concurrent, 500 hours, $0.10/hr, 5 GB then $10/GB, 50 agent runs. Scale: custom, 250+ concurrent, HIPAA BAA, DPA, SSO, SOC 2, private cloud/VPC, no on-prem. — [Browserbase pricing](https://www.browserbase.com/pricing)
- Developer plan was cut 49% to $20 in Q2 2025 while overage rates rose ([PricingSaaS](https://pricingsaas.com/companies/browserbase/diffs/2025Q2)); "agent runs" became a counted entitlement on every plan on 2026-09-11 ([UsagePricing](https://www.usagepricing.com/blueprint/activity/browserbase-2026-09-11-agent-runs-entitlement)).
- Funding: $40M Series B June 2025 at $300M post-money (Notable, CRV, Kleiner), $67.5M total; usage-based SaaS, margins "typical of IaaS", costs driven by compute and proxy bandwidth; Director no-code product targets ops teams; 1Password partnership aimed at regulated buyers. — [Sacra Browserbase](https://sacra.com/c/browserbase); [SiliconANGLE](https://siliconangle.com/2025/06/17/browserbase-reels-40m-browser-automation-tools/)
- UNVERIFIED (search summary only): revenue "crossed $3M with 1,000+ paying customers" by June 2025; ~37M monthly sessions across 10,000+ companies by March 2026.

Browser Use
- No subscription. Prepaid wallet from $5. Cloud browser $0.02 per browser-hour billed per minute (1,000 browser-hours = $20 plus traffic); managed residential proxy $5/GB; BYO-proxy egress $0.20/GB. Concurrency scales with cumulative spend: $100 paid = 50 sessions, $1,000 = 250, $5,000 = 500, $25,000 = 1,000. Hosted agents (API v4) billed at per-model token rates (default gpt-5.6-luna $0.24 in / $1.44 out per 1M); BYO model key = provider cost + 0.2x orchestration fee; API v3 hosted model = 1.2x provider rate; API v2 step-based = from $0.006/step + $0.01 per task init. Enterprise: negotiated annual credit pool, HIPAA, zero data retention, EU residency. — [Browser Use pricing](https://browser-use.com/pricing.md)
- "Browser Use Cloud is now free. Every project gets free browser sessions" (changelog 2026-03-04). — [Browser Use changelog](https://browser-use.com/changelog/3-4-2026)
- Library is MIT, 119.6k GitHub stars; $17M seed March 2025 led by Felicis; no Series A found as of mid-2026. — [GitHub browser-use](https://github.com/browser-use/browser-use); [Verdict](https://www.verdict.co.uk/browser-use-raises-17m/)

Skyvern
- Old model: $0.05 per step (previously 10c, cut 50% at an earlier launch week). New model: Free ~1,000 credits (~170 actions), 1 concurrent; Hobby $29/mo, 30,000 credits (~1,200 actions), 10 concurrent; Pro $149/mo, 150,000 credits (~6,200 actions), 25 concurrent; Enterprise custom, 100 concurrent, HIPAA, SOC 2 report, self-hosted, BAA, SSO. Stated reason for the change: steps were "an internal implementation detail", and per-step pricing "discouraged iteration" because adding retries and validation raised the bill. — [Skyvern launch-week pricing post](https://www.skyvern.com/blog/launch-week-day-5-simpler-pricing-model/); [Skyvern pricing](https://www.skyvern.com/md/pricing.md)
- Implied ~$0.024 per action on Hobby/Pro (my arithmetic: $29 / 1,200). A "run" is one workflow execution regardless of pages or steps. — [Skyvern pricing](https://www.skyvern.com/md/pricing.md)
- AGPL-3.0, 23.3k stars; anti-bot, proxy and CAPTCHA features are cloud-only. — [GitHub Skyvern](https://github.com/Skyvern-AI/skyvern)

TinyFish
- TinyAgent $0.016 per step (2 concurrent runs default); TinyBrowser $0.002 per minute ($0.12/hr) including proxies and anti-bot; TinySearch and TinyFetch free within rate limits; wallet minimum $10, no subscription; Enterprise adds ISO 27001, SSO, audit logs, VPC deployment, 99.99% SLA. — [TinyFish pricing](https://www.tinyfish.ai/pricing)
- $47M launch round led by ICONIQ, August 2025, "agents already run at Fortune 500 companies". — [BusinessWire](https://www.businesswire.com/news/home/20250820555825/en/TinyFish-launches-with-47-million-to-define-the-era-of-Enterprise-Web-Agents)

Orby, Caddi, Induced
- Orby AI was acquired by Uniphore (announced 2025-08-28, terms undisclosed) after a $30M Series A (NEA, Wing, WndrCo, June 2024); pricing had been quote-based. — [Uniphore press release](https://www.uniphore.com/press-releases/uniphore-announces-the-acquisitions-of-orby-ai-and-autonom8/); [SelectHub](https://www.selecthub.com/p/ai-agent-tools/orby/)
- Caddi (Seattle, not the Japanese manufacturing unicorn CADDi) raised a $5.0M seed in March 2025 for "Automation by Demonstration" aimed at professional services (legal, finance); it plans "expansion revenue from add-on agents and usage-based pricing"; no published prices. — [FinTech Global](https://fintech.global/?p=193541); [SaaSRise](https://www.saasrise.com/deals/caddi-raises-5m-seed-round-from-ubiquity-2b4bb0d7-8f79-403e-a53d-93be5a641ba1)
- Induced: no pricing or funding information surfaced in any search.

### Inferences
- The commodity price of "a browser for an agent" has converged on $0.02-$0.12/hour and is still falling (Browser Use at $0.02, Browserbase cut its entry plan 49%). Nobody will pay a premium for the browser; the margin lives in what runs inside it (agent steps, proxies, CAPTCHA, enterprise controls) and in enterprise compliance tiers.
- Every vendor that started with per-step pricing (Skyvern, Browser Use v2) has moved to pooled credits or per-run/per-execution pricing (n8n also bills per workflow execution). For Handrail, "per replayed run" or "per approved capability per month" is consistent with where the market settled; per-step would be a regression.
- Incumbent RPA's per-robot licence ($8k-$10k/yr unattended) is the price ceiling a buyer will compare a "capability" against: a single deterministic replayable capability that replaces one unattended bot is worth at most that, unless it bundles things RPA does not (evidence chain, approval gates, escalation).

### Gaps
- No official per-unit price for UiPath Platform Units or Agent Units (negotiated only).
- Induced pricing and funding not found. Caddi pricing not public.
- Browserbase revenue figures are unverified search snippets; Sacra's page gives funding but no ARR.

## Q2. What do AI-agent companies pay for browser infrastructure, and is there a gap between "a browser for your agent" and "a reviewed, replayable capability your agent can call"?

### Takeaway
At list price, 1,000 browser-hours a month costs $80-$150 across Kernel, Steel, Hyperbrowser and Browserbase, and proxies and model tokens usually cost more than the browser itself. No vendor in this set sells a reviewed, deterministic, replayable capability with evidence and approval gates; the closest moves are Browserbase's counted "agent runs", Skyvern's "human-in-the-loop" enterprise feature and Anchor/Kernel compliance tiers, which shows the gap exists but is being approached from the compute side.

### Cited Findings
- Steel: Launch $0 + usage with $30 one-time credits, $0.10/hr, 10 concurrent, $10/GB proxy, $3/1k CAPTCHA, 15-minute max session; Scale $250/mo with $100 credits, $0.08/hr, 100 concurrent, $6/GB, 1-hour sessions; Enterprise 1,000+ concurrency, 24-hour sessions, SLAs, SSO. — [Steel pricing](https://steel.dev/pricing)
- Hyperbrowser: Free 5,000 credits (~50 browser hours), 1 concurrent; Startup $30/mo for 30,000 credits, 25 concurrent; Scale $100/mo for 100,000 credits, 100 concurrent; browser time 100 credits/hour ($0.10/hr), proxy $10/GB; Enterprise 1,000+ concurrency, 180+ day retention. — [Hyperbrowser pricing](https://www.hyperbrowser.ai/pricing)
- Anchor Browser: Starter $50/mo (50 credits, 25 concurrent); Team $500/mo (500 credits, 50 concurrent); Growth $2,000/mo (2,000 credits, 200 concurrent, SOC 2 Type 2, ISO 27001); $1.00 per credit overage; calculator uses $0.09/browser-hour, $8/GB proxy, $0.01 per AI step, $0.01 per session init; Enterprise adds BAA/HIPAA, RBAC, ZDR, BYO cloud and on-prem. Calculator line items do not add up (flagged on the page extract). — [Anchor pricing](https://anchorbrowser.io/pricing)
- Kernel: Free $0 + usage with $5 credits (5 concurrent); Hobbyist $30 + usage with $10 credits (10 concurrent); Start-up $200 + usage with $50 credits (150 concurrent); usage $0.0000166667 per GB-second with "no charges for idle time or proxies"; Enterprise SOC 2, HIPAA/BAA, white-label, ZDR, 99.9% SLA; claims customers "often see 50-98% lower costs than prior providers". — [Kernel pricing](https://www.kernel.sh/pricing)
- Cloudflare Browser Run: Workers Paid includes 10 browser-hours/month and 10 concurrent browsers, then $0.09 per additional browser-hour and $2.00 per additional concurrent browser. — [Cloudflare pricing](https://developers.cloudflare.com/browser-rendering/pricing/)
- Worked comparison at 1,000 browser-hours/month (browser time only): Kernel Hobbyist headless ~$80, Steel Launch $100, Hyperbrowser $100, Browserbase Developer $128, Browserbase Startup $149, Browserless Starter $140. With 20 GB of residential proxy: Kernel $80, Browserless $242, Browserbase Startup $299, Steel Launch $300, Hyperbrowser $300. The author notes "model tokens, which usually cost more than the browser" are excluded, and that proxy traffic can cost more than browser time. — [ecorpit comparison](https://ecorpit.com/cloud-browsers-ai-agents-browserbase-steel-kernel-2026/)
- Steel's browser API is Apache 2.0 and self-hostable; Kernel's browser images are Apache 2.0; Anchor is closed-source managed-only; Hyperbrowser's HyperAgent is AGPL-3.0. — [Anchor vs Steel](https://llms.anchorbrowser.io/anchor-browser-vs-steel); [Steel vs Kernel](https://steel.dev/blog/steel-vs-kernel)
- Browserbase's Scale tier offers HIPAA BAA, DPA, SSO, SOC 2, VPC connectivity and data residency, but explicitly "no on-prem deployment". — [Browserbase pricing](https://www.browserbase.com/pricing)
- Skyvern Enterprise lists "custom code blocks and human-in-the-loop", Azure Key Vault and Bitwarden integrations, self-hosting and a BAA. — [Skyvern pricing](https://www.skyvern.com/md/pricing.md)
- TinyFish's own comparison derives $0.80 for a 50-step agent run and $0.02 for a 10-minute browser session, and lists the hidden costs buyers hit on Browserbase: separate proxy line, CAPTCHA only on paid tiers, model tokens at market rate, full-minute minimum billing, and no published overage for "agent runs". — [TinyFish on Browserbase pricing](https://www.tinyfish.ai/blog/browserbase-pricing)
- Browserbase's analyst profile positions "AI agents" as an expansion market via its MCP server but does not say agent startups are a major revenue segment; it frames enterprise parallel-session buyers as the usage-revenue driver. — [Sacra Browserbase](https://sacra.com/c/browserbase)

### Inferences
- The infrastructure layer is a price war with falling unit prices and thin IaaS-style margins. A one-person company cannot win it and should not try to; Handrail should buy browsers from these vendors (or run its own Playwright) and sell something priced on a different axis.
- The missing product in every pricing page is the one Handrail describes: a typed capability with a deterministic replay, an evidence chain and an approval gate. Vendors have started to count "agent runs" (Browserbase) and offer "human-in-the-loop" (Skyvern) but price them as compute entitlements, not as reviewed artefacts. That is the gap, and it is the thing a bank's vendor-risk reviewer actually asks about (see Q4).
- The natural B2B2B unit is "per approved capability per month" (like a UiPath robot licence, but scoped to one workflow) plus "per replayed run" at a rate well above $0.02/hour but far below a $0.05-per-step model-in-the-loop run, since a deterministic replay has near-zero model cost.

### Gaps
- No public data on what any specific AI-agent company actually spends on browser infra per month; only list-price arithmetic.
- No vendor publishes an "agent run" overage rate.

## Q3. MCP as a distribution channel in 2026: how many servers, which marketplaces, does anyone sell paid MCP tools?

### Takeaway
MCP is now enormous as a discovery surface (Glama indexes 113,141 servers; Smithery 27,365+) but almost nobody monetises the MCP server itself: 85% of MCP-capable tools ship a free tier and the analysts' read is that MCP is a free on-ramp to an underlying paid product. Payment rails for paid tools exist (Stripe + Cloudflare's PaidMcpAgent, Stripe's agentic-commerce and token-billing products) but are experimental and client-dependent.

### Cited Findings
- Glama directory: "113,141 servers" as of 2026-10-31; by hosting: Remote 44,361, Local 42,546, Hybrid 21,370; "Official" authors 7,424, "Claimed" 9,422; top categories Developer Tools 27,178, Search 15,888, AI & ML 8,235, App Automation 7,993, Autonomous Agents 7,872, Finance 7,622; it has a Browser Automation category. No monetisation mechanism for authors is described. — [Glama MCP servers](https://glama.ai/mcp/servers)
- Smithery lists "27,365+ MCPs", offers publishing, built-in auth and observability, and announced that its MCP Proxy and managed identity shut down on October 31 (2026). No author revenue-share is described; individual listings set their own paid tiers (e.g. DevMatch $129/mo). — [Smithery](https://smithery.ai/)
- Secondary counts vary: Glama "over 21,000" / "17,000+" / "close to 37,000", mcp.so ~17,000-19,700, Smithery 6,000-7,000+, in early-2026 roundups; the spread reflects timing and methodology. — [Towards AI roundup](https://pub.towardsai.net/8-best-mcp-marketplaces-to-discover-mcp-servers-fb6cb082efcb); [Codex registry guide](https://codex.danielvaughan.com/2026/05/27/codex-cli-mcp-server-discovery-registries-smithery-glama-official-registry/)
- Official MCP registry (registry.modelcontextprotocol.io) is "built in the open by MCP contributors"; its landing page shows no server count and states no policy on paid servers. — [MCP registry](https://registry.modelcontextprotocol.io/)
- Toolradar "State of MCP 2026" (snapshot 2026-08-04): 228 MCP-capable tools out of a 9,959-tool catalog, up from 2 in late 2025; 37% free, 47% freemium, 15% paid, so 85% have a free tier versus 54% of the whole catalog; the authors infer "MCP servers are free on-ramps, with revenue coming from the underlying product". — [Toolradar State of MCP 2026](https://toolradar.com/reports/state-of-mcp-2026)
- Anthropic's connectors directory launched 2025-07-14 at claude.ai/directory with one-click connect; named partners Notion, Canva, Stripe (remote) and Figma, Socket, Prisma (desktop); remote connectors are "available to paid plan users only"; no paid-tool or revenue-share mechanism is described. — [Claude connectors directory](https://claude.com/blog/connectors-directory)
- OpenAI Apps SDK: plugins are submitted to a public "ChatGPT Directory" under published guidelines; remote MCP servers and optional UI go through public review; there is a Checkout API and conversion specs (product checkout, reservations, local-services quotes) but the docs index states no developer fee, pricing or payout terms. — [OpenAI Apps SDK](https://developers.openai.com/apps-sdk)
- Stripe's agent page offers a Stripe MCP server, "Billing for LLM tokens" (usage-based billing for metered resources like LLM tokens or API calls), agentic commerce (sell through agents, accept payments from agents) and a "Stripe Directory" index of businesses that agents can search. — [Stripe agents docs](https://docs.stripe.com/agents)
- Stripe + Cloudflare paid MCP toolkit: `experimental_PaidMcpAgent` gates a tool behind a Stripe subscription; a call without a subscription returns an error containing a checkout link; identity is an email prop; author tested only with Claude Desktop via mcp-remote, as of May 2025. — [DEV Community hands-on](https://dev.to/hideokamoto/exploring-paid-mcp-servers-with-stripe-and-cloudflare-my-hands-on-experience-3le9)
- Claims of a dedicated paid-MCP marketplace ("MCPize", 85% revenue share) and per-call pricing examples (Ref at $0.009/credit) appear only in posts by people with a stake in those marketplaces; UNVERIFIED. — [Medium post](https://medium.com/mcp-server/the-rise-of-mcp-protocol-adoption-in-2026-and-emerging-monetization-models-cb03438e985c); [Godberry](https://godberrystudios.com/posts/how-to-monetize-mcp-servers-2026/)

### Inferences
- MCP is a distribution and integration standard, not a billing channel. Publishing Handrail's approved capabilities as MCP tools makes them callable from Claude, ChatGPT, Codex, n8n and every agent framework, which is the right technical interface for B2B2B, but revenue must come from a contract with the vendor or bank, not from a marketplace storefront.
- The "paid plan only" gate on remote connectors at Anthropic, and review gates at OpenAI, mean a serious buyer will treat an MCP server as an API with a vendor behind it. For a bank or vertical-SaaS vendor the question becomes "who is the vendor, what is their SOC 2, where does the data go", which pushes back to Q4.

### Gaps
- No count for Anthropic's directory or OpenAI's ChatGPT Directory.
- No example found of a company whose primary revenue is a paid MCP server.
- Smithery's and the official registry's pricing pages were not fetched.

## Q4. Sales cycles and ACV: banks/credit unions vs SMB vs selling to startups; SOC 2 as a gate

### Takeaway
Median B2B SaaS cycle is 84 days, but sub-$15K SMB deals close in 14-30 days while $100K+ enterprise deals take 90-180+ days and financial-services deals into credit unions and community banks run 6-18 months. The vendor-risk review adds 4-8 weeks per procurement and treats a SOC 2 Type II (or ISO 27001) as "the floor"; a first SOC 2 program costs roughly $20K-$65K and takes 6-12 months including a minimum 3-month observation window, so a one-person company without one is effectively locked out of direct bank sales for most of a year.

### Cited Findings
- Optifai Pipeline Study (939 B2B SaaS companies, Q2 2025-Q1 2026): median cycle 84 days; SMB (<$15K ACV) 14-30 days; $15K-$50K 30-60 days; $50K-$100K 60-90 days; Enterprise (>$100K) 90-180+ days (25th-75th percentile). — [Optifai benchmark](https://optif.ai/learn/questions/sales-cycle-length-benchmark/)
- By vertical (unsourced vendor table, directional only): FinTech 90-180 days at $40K-$150K ACV; Healthcare SaaS 90-210 days at $30K-$100K; DevTools 14-40 days at $5K-$30K. — [GrowthSpree](https://www.growthspreeofficial.com/blogs/b2b-saas-sales-cycle-length-benchmarks-2026-by-acv-vertical)
- Net revenue retention: 118% median for $100K+ ACV, 108% mid-market, 97% SMB; SMB annual logo churn 25-50% vs under 10% enterprise (vendor blogs citing Optifai). — [Prospeo](https://prospeo.io/s/saas-sales-conversion-rates)
- Financial services norm "six to eighteen months from first conversation to first close" for embedded fintech sold into credit unions and community banks (agency case study, self-reported). — [DanishLeadCo case study](https://danishleadco.io/case-studies/voila-insurance-cold-outbound-case-study)
- Credit union vendor risk management adds "4-8 weeks" to each procurement cycle; budgets are annual. — [FirstSales credit-union guide](https://firstsales.io/sales-guide/credit-union-account-based-selling/)
- NCUA Letter 07-CU-13 "Evaluating Third Party Relationships" (Dec 2007, active) sets the due-diligence framework; the NCUA has no direct authority over vendors, so the credit union bears full responsibility for due diligence, monitoring and contract oversight. — [NCUA letter](https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/evaluating-third-party-relationships); [Omni Online Strategies](https://omnionlinestrategies.com/blog/what-ncua-requires-vendor-risk-management-credit-unions)
- AI-vendor checklist used by credit unions: SOC 2 Type II or ISO 27001 is "the floor" for vendors handling regulated data; two years of audited financials; cyber-liability and tech E&O insurance certificates; DR/BCP with tested RTOs; data-flow diagram by jurisdiction; sub-processor list including foundation-model providers; bias testing and model validation reports; NIST AI RMF-aligned governance policy; five years of incident history; 72-hour breach notification; a 40-question questionnaire for high-risk vendors (anything touching member data, lending or core systems) with annual re-attestation. — [Multimodal AI vendor due diligence](https://www.multimodal.dev/post/ai-vendor-due-diligence-credit-unions)
- NAFCU: "in most cases, the SOC 2 Type 2 is the best report for assessing cybersecurity". — [NAFCU](https://nafcu.org/node/3803)
- Vanta (Vendr): median $20,000/yr across 377 purchases, range $7,500-$57,163; 1-50 employees pay $12K-$25K/yr for a single framework; separate auditor $8K-$25K+; first-year SOC 2 program ~$20K-$65K all-in. — [Vendr Vanta](https://www.vendr.com/marketplace/vanta)
- Drata (Vendr): mid-size SOC 2 Type II $20K-$45K/yr, median ~$24,934 (UNVERIFIED: search summary of [Vendr Drata](https://www.vendr.com/marketplace/Drata)).
- Timeline: SOC 2 "realistically takes six to twelve months from a standing start"; the shortest Type II observation window is 3 months and controls must run for the whole window. — [beancount.io guide](https://beancount.io/blog/2026/07/14/soc-2-type-ii-small-saas-audit-cost-guide)
- Reference customer in the target vertical: interface.ai serves "100+ Banks & Credit Unions", claims "tens of millions in annual recurring revenue", was bootstrapped until a $30M round (Oct 2024, $20M equity + $10M debt, Avataar), had 120 employees, and markets "performance-based pricing" where customers "pay only for successful outcomes" with implementation, maintenance and AI training included. — [TechCrunch](https://techcrunch.com/2024/10/22/interface-ai-raises-30m-to-help-banks-field-customer-requests); [Maginative](https://www.maginative.com/article/interface-ai-raises-30m-in-first-external-funding-round-to-expand-ai-banking-solutions/); [interface.ai solutions](https://interface.ai/ai/solutions)
- interface.ai customer claims: Great Lakes Credit Union's voice assistant handles 60%+ of inbound calls in business hours and 75% after hours (vs under 25% before); Bank of Guam saved ~300 hours/month in live chat. Later funding is reported inconsistently (Dealroom: $30M at $120M Dec 2025 and $20M at $150M Mar 2026; CB Insights $40M over 2 rounds; Caplight $63.5M total) — flag. — [interface.ai solutions](https://interface.ai/ai/solutions); [Dealroom](https://dealroom.co/companies/interface-1/)
- Other credit-union AI vendors (Posh "200+ financial institutions", Eltropy 600 customers, Glia 700+) publish customer counts and the AUM of signed credit unions but never contract values; all are quote-only. — [MyABT comparison](https://www.myabt.com/blog/credit-union-agentic-ai-platform-comparison); [Eltropy 600 customers](https://www.cuinsight.com/press-release/eltropy-celebrates-600-customer-milestone/)

### Inferences
- Direct-to-bank/CU (option a) means a 6-18 month cycle, a SOC 2 Type II that itself takes 6-12 months and ~$20K-$65K, cyber insurance, audited financials and a 40-question AI questionnaire; a solo founder with no customers cannot clear that gate in 2026. The sales motion would be "pilot inside someone else's paper", i.e. under a vendor who already passed review.
- Selling to AI-agent companies and vertical-SaaS vendors (option b) shifts the buyer to a 14-90 day cycle with technical evaluators, but inherits their compliance obligations: a vendor like interface.ai will need Handrail to be listed as a sub-processor and will ask for the same SOC 2, so the gate moves rather than disappears; it just stops being the first conversation.
- Vendors already in the CU channel price on outcomes and bundle implementation. A "hands" supplier to such a vendor will be squeezed to a cost-of-goods line; pricing should be per approved capability (predictable for the vendor's margin model) rather than per step.

### Gaps
- No credit-union-specific ACV or sales-cycle dataset (CUNA/NCUA level) was found; the 6-18 month figure is a single agency's claim.
- No published contract values for Posh, Eltropy, Glia or interface.ai.
- The NCUA supervisory letter enclosure (detailed checklist) was not retrieved, only the cover letter.

## Q5. What did Adept, Olive AI and other failed "AI does the UI work" companies get wrong commercially, and what did survivors (Infinitus, Tennr, Thoughtful AI, Nividous) do differently?

### Takeaway
Adept raised $414M to build a general "AI that uses software" model, found training costs ruinous, and ended in a reverse acqui-hire where Amazon paid ~$25M, wanted only the people, and left the enterprise-sales business behind; Olive raised $848M-$902M, pivoted 27 times, ran a venture arm and side businesses, and sold its parts to Waystar and Humata. The survivors each picked one narrow, high-volume, measurable workflow in one vertical (payer phone calls, fax-based referrals, RCM claims), sold before they built, priced on a hybrid of platform fee plus per-task/outcome usage, and expanded from one workflow to many inside each account.

### Cited Findings

Adept
- Investors put in ~$414M (Greylock, General Catalyst); last valued at $1B; Amazon hired most top researchers including co-founder David Luan in June 2024; Amazon paid Adept around $25M and investors were made roughly whole with no return; Adept had "three assets: its people, an enterprise sales business, and its AI models. Amazon only wanted the first"; stated constraint was "the skyrocketing costs of training AI models". — [Semafor](https://www.semafor.com/article/08/02/2024/investors-in-adept-ai-will-be-paid-back-after-amazon-hires-startups-top-talent)
- The remaining company said it would "shift its focus away from foundational model development to concentrate solely on advancing agentic AI solutions" for enterprise partners. — [Adept blog update](https://adept.ai/blog/adept-update); [Techleap note](https://finder.techleap.nl/news/note/adept-s-transition-founders-depart-for-amazon)
- The Information's read: "launching AI for enterprises is hard if you don't already have a lot of customers". — [The Information newsletter](https://feature.theinformation.com/newsletters/ai-agenda/with-adept-deal-amazon-copies-microsoft-do-businesses-really-need-gpt-5)
- Luan left Amazon in 2026, less than two years after the deal. — [GeekWire](https://www.geekwire.com/2026/head-of-amazons-agi-lab-is-leaving-in-latest-exit-from-high-profile-adept-deal/)
- The FTC sought details on the deal structure. — [Seeking Alpha](https://seekingalpha.com/news/4124647-amazon-deal-with-ai-startup-adept-under-ftc-scrutiny-report)

Olive AI
- Raised $848M since 2013; $400M round at $4B valuation in 2021; shut down Oct 31, 2023, selling the clearinghouse and patient-access units to Waystar and prior authorization to Humata; reported 950 hospital clients at peak (Becker's) versus "over 600 hospitals" (Coverager). — [Becker's timeline](https://www.beckershospitalreview.com/finance/the-rise-and-fall-of-olive-ai-a-timeline.html); [Coverager](https://coverager.com/?p=185249)
- CEO Sean Lane had told TechCrunch (June 2022) that Olive "pivoted 27 times" on the way to $4B; the company ran a venture arm (Olive Ventures) and divested Population Health and 340B lines in 2023; commentators attribute the failure to lack of focus, culture and easy capital (opinion). Total raised cited there as $902M. — [FixHealth / Sergei AI analysis](https://www.fixhealth.ai/p/the-death-of-olive-ai)
- Fierce Healthcare reported the wind-down and a 450-person layoff. — [Fierce Healthcare](https://www.fiercehealthcare.com/health-tech/once-high-flying-unicorn-olive-ai-sells-two-key-businesses-winds-down-operations)
- Olive was described by HIStalk as a "healthcare robotic process automation vendor" and by Dealroom as "AI-as-a-Service ... to automate high-volume, repetitive administrative and clinical tasks". — [HIStalk](https://histalk2.com/2023/10/31/news-11-1-23/); [Dealroom](https://app.dealroom.co/companies/olive_1)

Infinitus (payer/pharmacy phone calls)
- Pricing: "annual platform and license fees combined with usage (i.e. per task or minute) as well as a subscription model"; discounted task rates for multi-year contracts with monthly minimums; ROI inputs include 1.2 calls per successful task. — [Infinitus pricing](https://infinitus.ai/pricing)
- Founders validated by asking prospects "whether they would pay and how much"; first test was a recorded AI voice calling UnitedHealthcare; after the first pilot they built the web app, APIs and docs in 2-3 weeks; lesson "sell and then build". — [Infinitus 5-year retrospective](https://www.infinitus.ai/blog/looking-back-on-5-years-of-infinitus/)
- $51.5M Series C led by a16z (Oct/Nov 2024), ~$103M total raised. — [Healthcare IT Today](https://www.healthcareittoday.com/2024/11/25/infinitus-systems-raises-51-5-million-series-c-funding-on-the-strength-of-ai-guardrails/)

Tennr (fax-driven patient referrals)
- $101M Series C led by IVP at a $605M valuation (June 2025), new investors GV and ICONIQ, insiders a16z and Lightspeed; ~$157M-$160M total. — [VC News Daily](https://vcnewsdaily.com/tennr/venture-capital-funding/wpbltjxntr); [FundedIQ](https://fundediq.co/tennr-tennr-com-funding/)
- Series B (Sept 2024, Lightspeed) valued it above $200M. — [Trusted Insight](https://www.thetrustedinsight.com/investment-news/healthcare-ai-startup-tennr-is-raising-cash-from-lightspeed-venture-partners-20240924693)
- Headcount ~323 (Mar 2026) from 41 in 2023 (third-party estimate). — [Revelio Labs](https://www.reveliolabs.com/companies/tennr/employees)
- Product: classify and route patient data from fax/portal, collect missing documentation, check eligibility, investigate benefits by phone, submit prior auths, "control tower" of stuck patients; sold to DME, infusion, fertility, physician groups, specialty pharmacies; case studies "Takes referrals 75% faster with 4X the volume" (Home Medix), "3-week backlog to same-day intake" (NEB Medical); pricing not public, demo-only. — [Tennr](https://www.tennr.com/)

Thoughtful AI (RCM agents)
- $20M Series A led by Drive Capital (July 2024); role-based agents CAM, EVA, PHIL for claims, eligibility, payment posting; claims 5x-9x ROI, >300% net revenue retention, customers expanding "from one to 30 AI Agents", 220%+ YoY growth; named customers Allegiance Mobile Health, Signature Dental Partners. — [Pulse 2.0](https://pulse2.com/thoughtful-ai/amp/)
- In 2025 New Mountain Capital combined Thoughtful.ai with SmarterDx and Access Healthcare into "Smarter Technologies"; thoughtful.ai now redirects to accesshealthcare.com, an RCM outsourcer selling "technology as a service" and claiming "60% reduction in cost to collect". — [PE Hub](https://www.pehub.com/new-mountain-backs-health-tech-firm-thoughtful-ai/); [Access Healthcare](https://www.accesshealthcare.com/)
- Third-party directories give inconsistent pricing ("from ~$99 per provider/month", "performance-based", "contact for pricing"); UNVERIFIED.

Nividous
- Platform plus full-lifecycle professional services (discovery, implementation, support, CoE); "Quick Start Guarantee" delivers a governed agent in 3-4 weeks at a fixed price; "90+ enterprise deployments"; verticals finance and banking, insurance, healthcare, manufacturing, life sciences; case studies claim 75-90% reduction in manual RCM effort. — [Nividous about](https://nividous.com/about-us); [MedHelp case](https://nividous.com/news/nividous-helped-medhelpinc-to-achieve-over-75-percent-reduction-in-manual-efforts-automating-its-claim-submissions/)

### Inferences
- Adept's failure mode is the one Handrail's design already avoids: betting on a general model that must stay in the loop. Handrail takes the model out of the loop after one run, so its cost of goods does not scale with model prices and it has no reason to train models. Its commercial lesson from Adept is the other one: without an existing customer base, a general "AI uses software" pitch does not land; a specific workflow for a specific buyer does.
- Olive's failure was scope and capital discipline inside a vertical, not the vertical itself: the survivors are all in healthcare administration. The transferable rule is one workflow, one buyer type, measurable throughput (calls completed, referrals processed, claims posted), then expand per account.
- Every survivor's pricing is a platform/licence fee plus a metered unit the buyer already counts (task, minute, claim). None price per model step. Land-and-expand from one agent to thirty inside an account (Thoughtful) is the mechanism behind >100% NRR, and it maps directly onto "one capability, then the next".
- Two of four survivors ended up owned by or merged into services/outsourcing platforms (Thoughtful into Access Healthcare; Orby into Uniphore). Exit paths for a "hands" company run through the vendors that own the customer relationship, which supports option (b).

### Gaps
- No primary Adept revenue or customer figures (The Information is paywalled).
- No Olive pricing model or revenue figures.
- Tennr and Thoughtful pricing units are not public.

## Q6. Open-core and developer-led conversion in adjacent spaces (Browser Use, Stagehand, Skyvern, Playwright ecosystem, n8n, Temporal)

### Takeaway
The pattern that works is "free, permissively licensed engine; paid hosted control plane with the things you cannot self-host well" (anti-bot, proxies, SLAs, SSO, retention). n8n reached ~$100M ARR by April 2026 and Temporal a $250M+ run-rate by selling the hosted version of a free core; Browser Use and Skyvern are earlier but follow the same shape, with Skyvern explicitly keeping anti-bot features cloud-only.

### Cited Findings
- n8n: ARR ~$100M in April 2026, from $70M at end of 2025 and $40M in July 2025; Series C $180M (Oct 2025) at $2.5B; SAP invested €60M+ in May 2026 at a $5.2B valuation; 1.7M monthly active builders on the Community Edition; >80% of workflows involve AI agents; Community Edition is free under the "Sustainable Use License" which restricts external-facing and white-label use; cloud from €20/month for 2,500 executions, priced per complete workflow execution regardless of node count; embed/OEM uses annual execution-volume commitments. — [Sacra n8n](https://sacra.com/c/n8n/)
- Secondary: n8n revenue mix ~55% cloud, 30% enterprise licences, 15% embedded partnerships (single secondary source, UNVERIFIED). — [ValueAdd VC](https://valueaddvc.com/blog/n8n-valuation-2026-5-2b-40m-arr-and-how-it-compares-to-zapier-and-make)
- Temporal: annualised run-rate above $250M, $550M round at $12.55B; open-source installs surpassed 43M (up 134% since Jan 2026); Temporal Cloud processed 1.9T+ actions in August, 4,300+ paying customers; core is MIT. An older profile cites 2,500+ customers and 184% NDR; figures conflict by date. — [ARR Club](https://www.arr.club/temporal/temporal-arr-hit-250m-with-200-yoy-growth-raised-550m-); [AI Insider](https://theaiinsider.tech/?p=51676)
- Browser Use: MIT library at 119.6k stars; monetisation is Browser Use Cloud ($0.02/browser-hour) plus hosted model inference at provider cost + 0.2x orchestration fee or 1.2x provider rate. — [GitHub browser-use](https://github.com/browser-use/browser-use); [Browser Use pricing](https://browser-use.com/pricing.md)
- Skyvern: AGPL-3.0, 23.3k stars; "anti-bot measures are available only in the managed cloud and not in the open-source code". — [GitHub Skyvern](https://github.com/Skyvern-AI/skyvern)
- Stagehand (Browserbase's SDK) is MIT, ~22.4k stars (April 2026), sits on CDP. — [Skyvern comparison post](https://www.skyvern.com/blog/browserbase-vs-stagehand-which-is-better/)
- Steel's browser API is Apache 2.0 and self-hostable; Kernel's images are Apache 2.0. — [Steel vs Kernel](https://steel.dev/blog/steel-vs-kernel)
- Hyperbrowser's HyperAgent is AGPL-3.0; Anchor is closed-source. — [Anchor vs Steel](https://llms.anchorbrowser.io/anchor-browser-vs-steel)

### Inferences
- Open-core works when the paid layer is operationally hard to self-host (hosting, scale, anti-bot, compliance) and the free layer drives adoption at zero sales cost. For Handrail the analogous split is: open the schema, replay engine and compiler (the parts an auditor and a developer want to read), keep paid the hosted evidence store, approval workflow, escalation ladder with its classifier/model backends, and compliance packaging.
- n8n's Sustainable Use License (free internal use, paid for embedding/white-label) is the precise instrument for option (d) when the primary customers are vertical-SaaS vendors who would otherwise embed the engine for free.
- A solo founder gets the adoption half of open-core cheaply but not the conversion half; conversion needs a hosted product and someone answering enterprise questionnaires, which argues for pairing (d) with (b) rather than running (d) alone.

### Gaps
- No ARR or customer counts for Browser Use, Skyvern or Stagehand.
- No data on conversion rates from self-hosted to paid at any of these companies.

## Q7. Pricing anchors a buyer would compare against: VA hourly, RPA developer rates, UiPath per-bot, Zapier tiers, per-FTE savings claims

### Takeaway
A buyer's mental ladder in 2026: offshore VA at $4.50-$12/hour ($720-$1,400/month); US RPA contractor at $22-$52/hour (~$114K salary); an unattended RPA robot at $8K-$10K/yr list plus 50-150% implementation; a Zapier task at roughly $0.001-$0.027 depending on tier; and vendor ROI stories framed as FTEs or hours (8 FTEs, 662,000 hours, 5-9x ROI).

### Cited Findings
- Filipino VA: $4.50-$7.50/hour or $720-$1,200/month full time; broader range $3-$25/hour by skill; advanced technical work $18-$35+/hour. — [Kinetic Staff](https://www.kineticstaff.com/how-much-does-it-cost-to-hire-a-filipino-virtual-assistant-in-2026-complete-rates-hidden-costs-roi-examples-and-strategic-guide/)
- Alternative ranges: $3-$12/hour, $600-$1,400/month ([HireTalent.ph](https://hiretalent.ph/salary-guide-for-hiring-filipino-virtual-assistants)); PayScale average ₱116.94/hour, 90th percentile ~₱490 ([PayScale](https://www.payscale.com/research/PH/Job=Virtual_Assistant)); North American advanced VA/EA $38-$50+/hour ([Stealth Agents](https://stealthagents.com/virtual-assistant-pricing-guide-2026)).
- RPA developer: US contract postings $42-$52/hour (Jan 2025) and $22-$27/hour (Jul 2026, Insight Global); average UiPath developer salary $114,265/yr (ZipRecruiter, Aug 2026); India freelance modelled at $10/hour (Flexiple). — [Insight Global Phoenix](https://jobs.insightglobal.com/find_a_job/arizona/job-399572); [ZipRecruiter](https://www.ziprecruiter.com/Salaries/UI-Path-Developer-Salary); [Flexiple](https://flexiple.com/hire/uipath)
- RPA implementation: "$5,000 for basic setup to $100,000+ for enterprise deployments" (CostBench, low-quality source); Vendr: 50-150% of first-year licence; Automation Anywhere professional-services inclusions of $50K-$150K are negotiable. — [CostBench](https://costbench.com/software/rpa/uipath/hidden-costs); [Vendr UiPath](https://www.vendr.com/marketplace/uipath); [Vendr AA](https://www.vendr.com/marketplace/automation-anywhere)
- Per-bot and per-task anchors are in Q1: UiPath unattended $8K-$10K/yr; AA unattended runner package £8,000/yr; Power Automate unattended $150/bot/month ($1,800/yr), hosted $215 ($2,580/yr); Zapier 2,000 tasks for $49 (~$0.0245/task) down to 2M tasks for $3,389 (~$0.0017/task).
- Per-FTE / hours claims: Royal Mail 85 automated processes, £55M saved, 662,000 hours returned ([UiPath case](https://www.casestudies.com/company/uipath/case-study/royal-mail-customer-case-study)); an Amaris client "savings equivalent to eight FTEs" after two years ([Amaris](https://amaris.com/client-story/rpa-client-story/)); a global insurer 18,000 labour-hours and £140,000 ([UiPath](https://www.uipath.com/resources/automation-case-studies/global-insurance-provider)); Thoughtful AI "5x-9x ROI" ([Pulse 2.0](https://pulse2.com/thoughtful-ai/amp/)); Nividous 75-90% manual-effort reduction ([Nividous](https://nividous.com/case-studies/a-leading-healthcare-provider-uses-nividous-platform-to-automate-its-rcm)); interface.ai ~300 hours/month saved at Bank of Guam ([interface.ai](https://interface.ai/ai/solutions)).
- Counter-anchor: MIT's "GenAI Divide" finding that 95% of enterprise GenAI pilots show no measurable P&L impact. — [Tunguz](https://tomtunguz.com/fde-arms-race/)
- Pricing-model adoption among AI companies (ICONIQ, ~300 execs, Jan 2026): 58% subscription/platform, 35% consumption (up from 19%), 18% outcome-based (up from 2%); 37% plan to change pricing within 12 months. — [SaaStr on ICONIQ](https://www.saastr.com/iconiqs-latest-state-of-ai-report-the-10-most-important-data-points-for-saas-founders)

### Inferences
- A deterministic replayed run has to be priced against a VA minute (~$0.08-$0.20) and a Zapier task ($0.002-$0.025), not against a model-in-the-loop agent step ($0.016-$0.05). Replays are cheap to serve (no model), so a per-run price of a few cents with a monthly capability fee is defensible and still high-margin.
- For the capability itself, the honest comparison is an unattended robot plus the developer days to build it: $8K-$10K/yr licence plus 50-150% implementation. "One capability, approved and replayable, for less than one robot licence, with the build included" is a sentence a buyer can evaluate.
- Buyers in this category are used to hearing FTE and hours claims and increasingly discount them (the 95% figure). Handrail's evidence chain lets it report runs completed, exceptions escalated and approvals granted per period, which is a more auditable ROI story than hours saved.

### Gaps
- No credible RPA consultant day rate for the UK/EU; only US hourly postings and salary data.
- No primary source for the Zapier-per-task dollar overage rate (Zapier publishes multiples, not dollars).

## Q8. Services-to-product playbook: companies that hand-built automations and productised; what first customers looked like

### Takeaway
The 2026 consensus (a16z, ICONIQ, Tunguz) is that complex enterprise AI starts services-heavy: a third of customers at AI companies now get forward-deployed engineers, gross margins sit around 52% and rise as workflows standardise, and the labs themselves have committed ~$9.75B to services arms. The documented first customers of the survivors were a handful of mid-size operators in one niche (DME suppliers, dental groups, mobile-health providers, community banks and credit unions), won by selling a specific workflow before the product was finished.

### Cited Findings
- a16z "Services-Led Growth": complex AI applications should begin with FDEs and implementation specialists; ServiceNow's gross margin was 63.2% at IPO and Workday's 54.1% versus an ~80% software ideal, rising to 79% and 75% by 2024; Salesforce burned $52M to make $22M before building a partner ecosystem; Decagon stands up customers with "Agent Product Managers"; enterprise AI companies in sales, support and legal grew from $0 to $5M, $10M or $20M+ ARR within two years; five-step conversion: services win the customer, capture the workflow, data creates lock-in, automation lowers service cost, ecosystems take over; advice includes narrow ICP, sell services at cost, build reusable libraries, automate delivery to lower minimum contract sizes. — [a16z](https://a16z.com/services-led-growth/)
- ICONIQ State of AI (Jan 2026): median share of customers receiving FDE support 32% projected for 2026, from 27% in 2025 and 20% in 2024; 44% use FDEs in a hybrid product-and-delivery role; AI gross margins 52% (2026) from 45% (2025) and 41% (2024); inference ~23% of revenue. — [SaaStr on ICONIQ](https://www.saastr.com/iconiqs-latest-state-of-ai-report-the-10-most-important-data-points-for-saas-founders)
- Tunguz "FDE arms race": Palantir ~400-500 FDEs (12% of headcount); Salesforce committed to 1,000 FDE roles; Indeed showed 5,330 FDE postings in April 2026, up 828%; lab services ventures total ~$9.75B (OpenAI "The Deployment Company" $4B at a $14B post, Anthropic JV $1.5B with Blackstone/H&F/Goldman targeting PE portfolio companies, Microsoft $2.5B, Amazon $1B, Google Cloud $0.75B partner fund); OpenAI acquired Tomoro (~150 FDEs); risks for startups: disintermediation by labs, talent cost ($350K-$550K senior FDE at labs), single-provider lock-in; the author's prescription is deep industry-specific FDE expertise. — [Tunguz](https://tomtunguz.com/fde-arms-race/)
- Infinitus: validated willingness to pay before building; first pilot preceded the self-serve web app and API by a 2-3 week build; "sell and then build". — [Infinitus retrospective](https://www.infinitus.ai/blog/looking-back-on-5-years-of-infinitus/)
- Tennr's named early customers are small-to-mid operators in one niche: Home Medix, Eastern MedTech, NEB Medical, Total Sleep Management, King Drug (DME, infusion, specialty pharmacy). — [Tennr](https://www.tennr.com/)
- Thoughtful AI's named customers were Allegiance Mobile Health and Signature Dental Partners; accounts expanded from one to 30 agents. — [Pulse 2.0](https://pulse2.com/thoughtful-ai/amp/)
- interface.ai: bootstrapped to "tens of millions" ARR and ~100 institutions (community banks and credit unions) before raising; the CEO's father owned a credit union in India. — [TechCrunch](https://techcrunch.com/2024/10/22/interface-ai-raises-30m-to-help-banks-field-customer-requests)
- Nividous sells a fixed-price "Quick Start" (governed agent live in 3-4 weeks) alongside its platform, i.e. productised services as the wedge. — [Nividous](https://nividous.com/about-us)
- Bardeen: began as a browser automation extension for recruiters, sales teams and agencies; by 2024 had 300K+ users, 1,000+ paying customers (Deel, Miro, WPP), took $3M from go-to-market partners with Dropbox and HubSpot as strategic investors, then repositioned to "business-ready AI agents". No evidence it started as a services business. — [BusinessWire](https://businesswire.com/news/home/20240808892830/en/Bardeen-Launches-First-Business-Ready-AI-Agent-as-More-Workers-Embrace-Task-Automation); [TechCrunch](https://techcrunch.com/?p=2833326)
- Magical offers two deployment models, "build and train agents using Magical's platform" or "work with the Magical team to deploy agents as a managed service"; no public pricing. — [Magical pricing](https://www.getmagical.com/pricing)
- Thoughtful.ai and Orby both ended inside larger services/platform owners (Access Healthcare / Smarter Technologies; Uniphore). — [Access Healthcare](https://www.accesshealthcare.com/); [Uniphore](https://www.uniphore.com/press-releases/uniphore-announces-the-acquisitions-of-orby-ai-and-autonom8/)

### Inferences
- "We build your capabilities" (option c) is the normal 2026 entry motion, not a detour, provided the services are priced at cost, scoped to one ICP, and every engagement leaves behind a reusable capability in the product. a16z's warning (services as a commodity signal) applies when services do not compound into the product; Handrail's compiler makes compounding structural, because each engagement produces a typed artefact.
- The first ten customers of the survivors were not banks; they were mid-size operators with a painful, countable back-office queue and no procurement department. For Handrail, the analogue is the vertical-SaaS or agent vendor's own implementation team, or a mid-size operator (a credit-union service organisation, a dental/DME group) rather than a bank's head office.
- The labs' $9.75B services push is a threat to generic FDE-led startups and an opportunity for narrow ones: the labs will need "hands" for legacy UIs in regulated accounts and will not build a hash-chained approval-gated replay engine themselves.

### Gaps
- No documented list of the actual first ten customers for Thoughtful AI, Nividous, Bardeen or Magical.
- No founder interview material on Thoughtful AI's or Nividous's early services-to-product transition was retrievable after the search budget was exhausted.
- Margin data for services-led startups is survey-level, not company-level.

## Q9. YC and investor framing that bears on the choice

### Takeaway
YC's current (Winter 2027) list does not name "agents" or "software for agents" as a category; its closest calls are "The $15-an-Hour Expert" (AI-equipped workers doing benefits, taxes, insurance claims, medical billing, immigration paperwork) and "AI for the Air-Gapped Economy" (on-prem AI for defense, banks, hospitals, nuclear plants). Earlier 2025-2026 lists did name vertical AI agents, "vertical AI for legacy industries" and "software for agents".

### Cited Findings
- YC Winter 2027 RFS categories: "Startups in a World of Abundant Space Access", "The $15-an-Hour Expert", "Robots Made in America", "LLMs That Write Well", "Plaid for Government Benefits", "Wall Street for the Physical Buildout", "Vertical Foundation Models", "AI for City Hall", "Data Center Supply Chain", "AI for the Air-Gapped Economy", "Own Your Intelligence". The $15-an-Hour Expert names benefits, taxes, insurance claims, medical billing and immigration paperwork; Air-Gapped names banks and hospitals; Plaid for Government Benefits notes agents will handle enrollment "if they can trust the data". — [YC RFS](https://www.ycombinator.com/rfs)
- Summer 2026 list (secondary coverage) included "Vertical AI for legacy industries - applying AI to industries with offline-heavy workflows" and "software for agents"; the 2025 list named "Vertical AI Agents ... tax accounting, legal compliance, and medical billing". — [VC Cafe](https://www.vccafe.com/requests-for-startups-summer-2026-edition/); [Genesis Accelerator](https://genesisaccelerator.substack.com/p/y-combinators-new-2025-startup-request)
- Forrester reads Anthropic's prebuilt agents and plugins as a push into legal, finance and "legacy modernization", arguing enterprises "need governance and reliability more than raw task completion"; Infosys and Anthropic announced a legacy-modernisation partnership in Feb 2026. — [Forrester](https://www.forrester.com/blogs/anthropic-doubles-down-on-agentic-for-the-enterprise); [Infosys alliance](https://www.infosys.com/about/alliances/anthropic.html)

### Inferences
- The investor framing has moved from "agents" as a category to "AI-equipped workers in paperwork-heavy regulated verticals" and "on-prem AI for banks and hospitals". Handrail's air-gap-friendly design (no model in the replay loop, evidence kept locally) fits the second theme directly, and its $15-an-hour comparison point is the first.

### Gaps
- No a16z or Sequoia essay using the phrase "AI hands" was found; the framing appears to be informal.

## Q10. Synthesis: how the evidence bears on options (a) direct vertical, (b) hands layer to agent/vertical-SaaS vendors, (c) services-led, (d) open-core

### Takeaway
The evidence favours a sequence rather than a single choice: (c) services-led capability building for one or two vendors who already own bank/CU relationships, delivered as (b) an MCP-exposed hands layer priced per approved capability plus per replayed run, with (d) an open, source-available core (schema, compiler, replay) under an n8n-style licence to drive developer adoption, and (a) direct sales deferred until a SOC 2 Type II and reference customers exist.

### Cited Findings
- This section synthesises Q1-Q9; see those sections for sources.

### Inferences
- (a) Direct to banks/credit unions: 6-18 month cycles ([DanishLeadCo](https://danishleadco.io/case-studies/voila-insurance-cold-outbound-case-study)), a 4-8 week vendor-risk review per deal ([FirstSales](https://firstsales.io/sales-guide/credit-union-account-based-selling/)), SOC 2 Type II as the floor ([Multimodal](https://www.multimodal.dev/post/ai-vendor-due-diligence-credit-unions)) costing ~$20K-$65K and 6-12 months ([Vendr Vanta](https://www.vendr.com/marketplace/vanta); [beancount](https://beancount.io/blog/2026/07/14/soc-2-type-ii-small-saas-audit-cost-guide)), and incumbents who bundle implementation into outcome pricing ([interface.ai](https://interface.ai/ai/solutions)). Not viable for one person with no customers in 2026; viable as a second act.
- (b) Hands layer to agent companies and vertical SaaS: buyers evaluate in 14-90 days ([Optifai](https://optif.ai/learn/questions/sales-cycle-length-benchmark/)); the infrastructure they already buy is priced at $0.02-$0.12/hour with no reviewed-capability product on any pricing page (Q2); MCP is the universally supported interface but not a billing channel (Q3); and the survivors' exits ran through the vendors that owned the customer (Q5). Pricing should mirror what those vendors can pass through: a monthly fee per approved capability (anchored below a $8K-$10K/yr robot licence) plus a per-run fee anchored to Zapier-task/VA-minute economics (Q7). Risk: being treated as COGS and squeezed; mitigation is owning the evidence/approval layer the vendor's own bank customers audit.
- (c) Services-led: the dominant 2026 motion (32% of customers get FDE support; a16z's explicit playbook), with the condition that each engagement compiles into a reusable capability, which Handrail's architecture guarantees. First customers should look like the survivors' first customers: mid-size operators or a vendor's implementation team with a countable queue, not a bank's head office.
- (d) Open-core: proven at n8n ($100M ARR, Sustainable Use License) and Temporal ($250M+ run-rate, MIT core) and adopted by every browser-infra peer; it buys developer adoption at zero sales cost but converts only with a hosted product and someone to answer questionnaires. Best used as the distribution channel for (b), with the licence blocking free embedding by vendors.
- Decision rule the data supports: measure the first year by number of approved capabilities in production and replayed runs per month at one or two vendor partners, not by ARR; the ARR follows the vendor's own deals once the capability catalogue exists.

### Gaps
- No example was found of a company that sells exactly a "reviewed, replayable capability" layer to other agent companies, so there is no revenue comparable for option (b); the closest are infra vendors' enterprise tiers (Q2) and n8n's embed/OEM execution commitments (Q6).
- Search budget exhausted before Induced, Caddi pricing, Sierra/Decagon per-outcome rates, Hippocratic's per-hour pricing, Thoughtful/Nividous founding histories and OpenAI app monetisation terms could be verified; follow-up searches are needed for those.
