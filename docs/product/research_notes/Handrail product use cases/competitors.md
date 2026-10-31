# Competitive landscape: computer-use, browser-agent and legacy-UI automation (as of October 2026)

Research date: 2026-10-31. Everything older than 2026 is marked with its date. "Unverified" means I could not confirm it against a primary source. Most pricing figures came from vendor pricing pages fetched directly; where only an aggregator was available, that is noted.

A note on method: the YC directory pages render only a title to a non-browser fetch, so batch letters for several YC companies come from YC's own industry listing page or from third-party aggregators, as marked.

## Key question 1: Y Combinator companies (2023-2026) in browser agents, computer use, RPA replacement, "AI for legacy software"

### Takeaway
YC has funded at least fifteen companies in this space since 2023. The 2023-2025 cohort (Skyvern, Browser Use, Reworkd, Autotab, Basepilot, Sola, Cua, Cyberdesk) sells horizontal developer infrastructure or general "teach it once" agents; the 2026 cohort (Zomma, Pomerado, Tilion, StableBrowse, Markov, RamAIn) is splitting into vertical BPO-style agents for finance and into browser infrastructure. Almost none publicly describe deterministic replay, hash-chained evidence, or live-session human takeover; Skyvern's "code caching" and Browser Use's `workflow-use` are the closest things to Handrail's record-once-replay-without-a-model idea.

### Cited Findings

**Skyvern (YC S23)**
- Founded 2023 by Suchintan Singh and Shuchang Zheng, YC Summer 2023 batch — [Extruct profile](https://www.extruct.ai/hub/skyvern-com/) (aggregator); YC directory — [ycombinator.com/companies/skyvern](https://ycombinator.com/companies/skyvern)
- Pricing (fetched from skyvern.com/pricing on 2026-10-31): Hobby $29/mo for 30,000 credits (~1,200 actions), Pro $149/mo for 150,000 credits (~6,200 actions), Enterprise custom with "HIPAA compliance, a SOC-2 report, Azure Key Vault and Bitwarden integrations, custom code blocks, human-in-the-loop, and a dedicated Slack channel." Page states Skyvern is "SOC 2 Type II certified." Audit trail is not mentioned on the pricing page. — [skyvern.com/pricing](https://www.skyvern.com/pricing)
- Earlier pricing was $0.05 per automation step before the credit model — [PricingSaaS history](https://pricingsaas.com/companies/skyvern) (aggregator)
- Funding: $2.7M seed per Skyvern's own blog — [Skyvern blog](https://www.skyvern.com/blog/skyvern-we-raised-2-7m-to-fix-browser-automation-open-source/); aggregators list $500K to $2.83M, so totals conflict — [Extruct](https://www.extruct.ai/hub/skyvern-com-funding/)
- Determinism/replay: Skyvern "code caching" records the actions of a successful AI run, generates executable code, and "subsequent runs execute the cached code directly, skipping LLM inference and screenshot analysis." If cached code hits "a layout change, a new field, a missing element," Skyvern re-runs with the full agent and regenerates the cache. Caching is per workflow block; conditional, wait and code blocks always run live. — [Skyvern docs: code caching](https://skyvern.com/docs/developers/features/code-caching); docs mirror — [docs-new.skyvern.com](https://docs-new.skyvern.com/docs/features/code-caching)
- Skyvern's own claimed result of code caching: average run time 278.95s to 119.92s (2.3x faster), average run cost $0.11 to $0.04 (2.7x cheaper). Vendor-reported, not independently verified. — [Fondo write-up of Skyvern launch](https://fondo.com/blog/skyvern-launches-ai)
- Skyvern's own benchmark post lists "hallucinating that it's achieved the goal when it has not" as a failure mode for write-heavy tasks — [Skyvern Web Bench](https://www.skyvern.com/blog/web-bench-a-new-way-to-compare-ai-browser-agents/)
- Human-in-the-loop is an Enterprise line item only; no public description of a human taking over the live browser session — [skyvern.com/pricing](https://www.skyvern.com/pricing)

**Browser Use (YC W25)**
- Raised $17M seed in March 2025 led by Felicis, with Paul Graham and Nexus Venture Partners — [Dealroom](https://app.dealroom.co/news/feed/browser-use-secures-17m-for-ai-navigation); listed as YC W25 — [Extruct](https://www.extruct.ai/hub/browser-use-com-funding) (aggregator)
- YC directory describes it as "the biggest open-source web agent project with 110k+ Github stars" (company's own claim) — [YC open-source listing](https://www.ycombinator.com/companies/industry/open-source)
- Pricing (fetched from browser-use.com/pricing on 2026-10-31): pay-as-you-go, no subscription; cloud browser $0.02/hour; web agent billed at model cost +20% plus browser time; bring-your-own-key charged at 20% of published token rates; custom model "BU 2.0" at $0.60 input / $3.50 output per 1M tokens; concurrency tiers unlock by cumulative spend ($0 = 10 sessions, $25,000 = 1,000). Enterprise: SOC 2 Type II, HIPAA, on-prem ("run browsers and agents inside your network"), zero-data-retention page. "Determinism: Not mentioned. Replay: Not mentioned. Human-in-the-loop: Not mentioned." — [browser-use.com/pricing](https://browser-use.com/pricing)
- April 2026 changelog: "Browser Use Cloud is now free. Every project gets free browser sessions" — [Browser Use changelog](https://browser-use.com/changelog/3-4-2026)
- Determinism: the separate `browser-use/workflow-use` repo is branded "Deterministic, Self Healing Workflows (RPA 2.0)"; it records a browser session into a JSON workflow and falls back to the Browser Use agent if a step fails. Its README roadmap admits the LLM fallback "is currently really bad" and plans a self-healing mode. — [SourcePulse mirror of workflow-use](https://www.sourcepulse.org/projects/2513677); forks — [github.com/sauravpanda/workflow-use](https://github.com/sauravpanda/workflow-use)

**Reworkd (YC S23)**
- YC profile: "The simplest way to extract web data at scale"; pivoted from "open-source Zapier of AI agents" (AgentGPT) to multimodal LLM agents that generate scraping code per site — [YC: Reworkd](https://www.ycombinator.com/companies/reworkd); original launch — [YC Launch: Reworkd AI](https://www.ycombinator.com/launches/J1r-reworkd-ai-the-open-source-zapier-of-ai-agents)
- Not a back-office or legacy-UI player; it is a data-extraction company. No pricing found.

**Autotab (YC S23, per aggregator)**
- YC page title: "Autotab: Building AI agents reliable enough to do real work" — [YC: Autotab (ztool)](https://www.ycombinator.com/companies/ztool)
- Show HN (Nov 2024): "Programmable AI browser for turning web tasks into APIs" — a Chrome-based browser you teach complex tasks with a simple API — [Show HN: Autotab](https://hn.svelte.dev/item?id=42197741)
- Funding: $500K pre-seed (aggregators; Caplight shows $1.5M, conflicting) — [VCBacked](https://www.vcbacked.co/company/autotab); [CB Insights](https://www.cbinsights.com/compare/hexomatic-vs-ztool)
- Pricing: one aggregator says "$1 per hour" for automated services; unverified — [Extruct](https://www.extruct.ai/hub/autotab-com/)
- Teach-by-demonstration is a "record once" model but I found no public claim of model-free replay or audit evidence.

**Basepilot (YC W24, per aggregator)**
- YC page title now: "Basepilot: AI agents for insurance claims" — [YC: Basepilot](https://www.ycombinator.com/companies/basepilot)
- Earlier description: Chrome extension; users "train it/construct their workflow by simply showing steps"; target industries logistics, insurance, finance, real estate; founders Ken and Pascal Wieler — [MIT AI Agent Index](https://aiagentindex.mit.edu/2024/basepilot) (dated 2024)
- Focus shift to "insurers, TPAs and MGAs ... claims operations" — [Extruct](https://www.extruct.ai/hub/basepilot-com-funding/) (aggregator)
- MIT index lists safety policies, documentation and external red-teaming as "unknown or unavailable" — [MIT AI Agent Index](https://aiagentindex.mit.edu/2024/basepilot)

**Sola (YC S23)**
- "A copilot for robotic agents that automate data entry and scraping in desktop and browser workflows, aligned with RPA" — [YC workflow-automation listing](https://www.ycombinator.com/companies/industry/workflow-automation)

**Cua (YC P2025 per directory), Cyberdesk (YC S25), Orgo**
- Cua: "cloud desktop for every agent ... built for Claude Code, Codex, and other computer-use agents" — [YC listings](https://www.ycombinator.com/companies/industry/open-source)
- Cyberdesk (S2025): "self learning computer use agent for developers" automating desktop workflows "including EHR appointment entry and processing files in legacy ERPs" — [YC workflow-automation listing](https://www.ycombinator.com/companies/industry/workflow-automation); page title — [YC: Cyberdesk](https://www.ycombinator.com/companies/cyberdesk)
- Orgo: "over 1000 teams use Orgo to run AI workers" (self-reported) — [YC listings](https://www.ycombinator.com/companies/industry/open-source)

**Zomma (YC S26)** — the closest vertical competitor to Handrail's banking target
- YC page title: "Zomma: AI BPO for financial services run by computer-use agents" — [YC: Zomma](https://www.ycombinator.com/companies/zomma)
- YC listing: "computer-use agents that work on the same screens human analysts use for KYC reviews, transaction alerts, and disputes, without integrations" — [YC workflow-automation listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Search snippet of the YC page: "every action stops for human approval before anything submits"; customers "hedge funds, asset managers, and fintech firms ... reconciliation, client onboarding, KYC, and investor reporting"; founders Varun Arumugam, Cashel Fitzgerald, Jihyun Kim; ~5 employees — [YC: Zomma](https://www.ycombinator.com/companies/zomma) (snippet; full page not rendered to fetch)
- Developer computer-use API appears waitlist-only — [APIs.io profile](https://apis.io/providers/zomma/) (third-party)

**Pomerado (YC F2026)**
- "Turn any website into an MCP for your agents, in minutes"; automates back-office workflows on "legacy ERP, EHR, and CRM systems" and "legacy portals" — [YC: Pomerado](https://www.ycombinator.com/companies/pomerado); [YC workflow-automation listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Directly overlaps Handrail's "expose approved capabilities as MCP tools" idea, but at the site-to-MCP layer rather than the reviewed-capability layer.

**Other YC 2025-2026 entrants (one-liners from YC directory pages)**
- Tilion (F2026): "self-healing browser infrastructure that runs millions of agent operations a day without supervision" — [YC listing](https://www.ycombinator.com/companies/industry/open-source)
- StableBrowse (P26): browser infrastructure for AI agents — same source
- Markov (S2026): expert computer-use datasets for frontier labs — same source
- Trelium (F2025): plain-English agents to "automate back-office work" such as order entry and PO-invoice matching — [YC workflow-automation listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Invo (W25): "infra for computer use agents"; RamAIn (W26): "super fast computer-use agents" — [YC: Invo](https://www.ycombinator.com/companies/invo); TechCrunch on YC computer-use startups — [TechCrunch, Jul 2025](https://techcrunch.com/2025/07/18/why-a-y-combinator-startup-tackling-ai-agents-for-windows-gave-up-and-pivoted)
- Pig (YC, Windows computer-use agents) gave up on Windows automation and pivoted to developer tooling in July 2025 — [TechCrunch, Jul 2025](https://techcrunch.com/2025/07/18/why-a-y-combinator-startup-tackling-ai-agents-for-windows-gave-up-and-pivoted)

**Named in the brief but NOT YC, or not in this space**
- TinyFish: not YC. $47M Series A led by ICONIQ (Aug 2025), ~25 staff, CEO Sudheesh Nair — [Reuters via Dunya](https://dunyanews.tv/en/Technology/901730-ai-agent-startup-tinyfish-raises-47-million-in-iconiqled-round-); [Seedtable](https://seedtable.com/companies/tinyfish/funding-rounds/series-a-2025-08). Pricing (vendor blog): Agent $0.016/step, Browser $0.002/session-minute, no mandatory subscription — [TinyFish blog](https://www.tinyfish.ai/blog/ai-browser-agents). Six API surfaces: Agent, Research, Search, Fetch, Browser, Monitor — [TinyFish docs](https://docs.tinyfish.ai/). Claims a Chromium fork where "automation runs below the js sandbox" — [HN: Building a Browser for the Agent Era](https://news.ycombinator.com/item?id=47767232). Vendor-reported benchmark: 81.9% on Online-Mind2Web hard tasks vs Operator 43.2% — [Show HN: TinyFish Web Agent](https://news.ycombinator.com/item?id=46991520)
- Induced AI: $2.3M seed led by Sam Altman and Peak XV; founders Aryan Sharma and Ayush Pathak; part of AI Grant Batch 2. YC status not confirmed by any source found. — [Analytics India Mag](https://analyticsindiamag.com/openais-ceo-sam-altman-backs-ai-startup-founded-by-indian-origin-teens/) (2023); product: cloud browser sessions, "100+ simultaneous sessions" — [JustCall directory](https://justcall.io/ai-agent-directory/induced-ai/)
- Yutori: not YC. $15M seed (Mar 2025) led by Radical Ventures, with Felicis, Fei-Fei Li, Jeff Dean — [SaaS News](https://www.thesaasnews.com/news/yutori-raises-15-million-in-seed-round/). Its n1 model is "pixels-to-actions ... initialized from Qwen3-VL" — [Yutori: Introducing Navigator](https://yutori.com/blog/introducing-navigator). Consumer/prosumer "Scouts" product — [Product Hunt](https://www.producthunt.com/products/scouts-by-yutori)
- Caddi: not YC. $5M seed from Ubiquity Ventures, Founders' Co-op, AI2 Incubator (Mar 2025); "record-to-code": analyzes a screen recording to build "a deterministic, API-driven automation"; targets law firms and financial advisors; SOC 2; 80+ integrations (vendor claim) — [FinTech Global](https://fintech.global/2025/03/06/caddi-bags-5m-seed-funding-to-drive-ai-powered-workflow-automation-in-legal-and-financial-sectors/); [GeekWire](https://www.geekwire.com/2025/this-seattle-ai-startup-watches-you-work-then-automates-the-tedious-back-office-tasks/); Aug 2026 launch of "an agent that builds and governs back-office agents" — [RuntimeWire](https://runtimewire.com/article/caddi-agent-builds-governs-back-office-agents)
- Orby AI: not YC (NEA/Wing/WndrCo/Pear). $30M Series A (2024), ActIO large action model; **acquired by Uniphore, announced 28 Aug 2025**, terms undisclosed — [Uniphore press release](https://www.uniphore.com/press-releases/uniphore-announces-the-acquisitions-of-orby-ai-and-autonom8/); [SiliconANGLE](https://siliconangle.com/2025/08/28/uniphore-buys-orby-ai-autonom8-extend-automation-capabilities/); earlier funding — [VentureBeat](https://venturebeat.com/ai/orby-ai-raises-30m-to-use-generative-ai-to-automate-your-most-tedious-work-tasks)
- Kombo: YC S22, but it is an HR-integrations API company ($10M+ ARR, $25M Series A per podcast listing), not a computer-use company — [Podcast listing](https://podcastaddict.com/episode/https%3A%2F%2Faudio.podigee-cdn.net%2F2553737-m-4afdddbe2f0eb455dcd3071e79b349b5.mp3%3Fsource%3Dfeed&podcastId=2924937). Probably a mix-up in the brief.

### Inferences
- The YC cohort has bifurcated: infrastructure (Browser Use, Cua, Tilion, StableBrowse, Invo) sold to developers by the token or the browser-hour, and vertical "AI BPO" agents (Zomma, Basepilot, Cyberdesk, Trelium) sold to ops teams in finance, insurance and healthcare. Handrail sits between them: it is infrastructure, but its buyer is an ops/compliance owner.
- "Teach by demonstration" (Autotab, Basepilot, Caddi) and "cache the successful run" (Skyvern, workflow-use) are both recognised patterns, which validates Handrail's core bet. But every one of them treats the cached artifact as an optimisation with an agent fallback, not as a typed, reviewed, versioned object with its own approval gate.
- Zomma's "every action stops for human approval before anything submits" is the only startup claim close to commit gating, and it is a blanket stop rather than a declared, named-approver commit step.

### Gaps
- YC directory pages only returned their titles to fetch; batch letters for Autotab (S23), Basepilot (W24) and Cyberdesk (S25) come from aggregators or the industry listing, not the company pages.
- No public pricing found for Autotab, Basepilot, Zomma, Pomerado, Cyberdesk, Caddi, Reworkd or Induced.
- No source describes any YC company offering hash-chained or tamper-evident evidence of runs.

## Key question 2: Big players — positioning and pricing

### Takeaway
The incumbents (UiPath, Automation Anywhere, Microsoft) have shipped GA "computer use" as a step type inside their existing governed platforms and bill it per step or per credit; the model labs (OpenAI, Anthropic, Google) sell computer use as a raw tool priced as ordinary tokens with no workflow, audit or replay layer; OpenAI's consumer Operator/agent products were retired by August 2026. Browserbase is browser infrastructure, Emergence is a multi-agent orchestrator, and Adept was reverse-acquihired by Amazon in 2024 (its tech became Amazon Nova Act).

### Cited Findings

**UiPath**
- Reorganised products as the "UiPath Platform for Agentic Automation" on 12 June 2025, including Maestro (orchestration) and Agent Builder — [Impress IT (Japanese)](https://it.impress.co.jp/articles/-/27988); SiliconANGLE on the Sep 2025 expansion — [SiliconANGLE](https://siliconangle.com/2025/09/30/uipath-expands-agentic-platform-orchestration-development-governance-tools/)
- Computer-use product is **ScreenPlay** (engine: Screen Agent), GA 18 Nov 2025, previously "UI Agent" in public preview; access via sales rep; macOS and Linux supported — [UiPath forum GA post](https://forum.uipath.com/t/uipath-screenplay-is-now-generally-available/5685821); docs — [ScreenPlay overview](https://docs.uipath.com/agents/automation-cloud/latest/user-guide-screenplay/overview)
- UiPath's own blog claims a #1 OSWorld ranking for Screen Agent; the forum post said #2. Unresolved. — [UiPath blog](https://www.uipath.com/blog/product-and-updates/uipath-screen-agent-number-one-osworld-ranking)
- Marketing page explaining its computer-use positioning — [uipath.com/ai/what-is-computer-use](https://www.uipath.com/ai/what-is-computer-use)
- May 2026: Agents, Healing Agent, ScreenPlay, Autopilot available in Automation Cloud Dedicated — [UiPath release notes (German)](https://docs.uipath.com/de/automation-cloud/automation-cloud/latest/release-notes/dedicated-may-2026)
- Sep 2026: building Maestro Flow orchestrations with a coding agent became GA — [UiPath coding agents release notes](https://docs.uipath.com/coding-agents/standalone/latest/release-notes/september-2026)
- Pricing: public entry tier "Automation Cloud Basic" around $25/month (Europe-only, up to 2 robots); Standard and Enterprise quote-based; agent execution consumes "Platform Units per LLM call" under unified pricing; unit price quote-only — [AutomationAtlas](https://automationatlas.io/answers/uipath-pricing-explained-2026/) (aggregator); [O-mega](https://o-mega.ai/articles/uipath-ai-agents-pricing-what-does-it-cost-you-2025) (aggregator)
- Third-party contract analysis (SpendHound via aggregator): SMB pricing down 2.56% YoY, enterprise up 9.35% — [VendorBenchmark](https://vendorbenchmark.com/blog/uipath-vs-automation-anywhere-pricing-benchmark) (unverified)

**Automation Anywhere**
- Product: "Agentic Process Automation (APA) System" on Automation 360, with AI Agent Studio and the Process Reasoning Engine (PRE), introduced at Imagine 2025 — [AA Q1 FY2026 results](https://automationanywhere.com/company/press-room/automation-anywhere-reports-strong-q1-fiscal-year-2026-growth-and-profitability)
- 20 Jan 2026: "AI-Native Agentic Solutions for the Enterprise with OpenAI" — OpenAI models handle reasoning, PRE "ensures governed execution"; target processes finance, HR, IT, customer service — [PR Newswire](https://tools.prnewswire.com/en-us/live/20823/release/20260120EN65806); [PEX Network](https://www.processexcellencenetwork.com/ai/news/automation-anywhere-openai-launch-new-generation-of-ai-native-agentic-solutions/amp)
- Pricing: free Community Edition; paid tiers quote-only; aggregators cite a $750/month Cloud Starter Pack or $9,000/year Basic — [Eesel](https://www.eesel.ai/blog/automation-anywhere-pricing); [CostBench](https://costbench.com/software/rpa/automation-anywhere/) (aggregators, conflicting)
- I found no AA press release specifically about computer-use agents in 2026.

**Microsoft Copilot Studio computer use** (primary source, docs updated 20 Oct 2026)
- "Computer use is a tool in Copilot Studio that lets your agent interact with and automate tasks on a Windows computer ... even when there's no API." Powered by "Computer-Using Agents (CUA)". Natural-language instructions, no code. — [Microsoft Learn: computer use](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)
- Licensing: "Each step consumes 5 Copilot Credits, or 15 Copilot Credits when using a premium model." Models: OpenAI CUA (GA, 5), OpenAI GPT-6 Sol (GA, 5), Claude Sonnet 4.5 (GA, 5), Claude Sonnet 4.6 (experimental, 5), Claude Opus 4.6 (premium experimental, 15). — same page
- Human supervision feature: an email reviewer is contacted "if the computer-use agent detects potentially harmful instructions"; request expires after a time limit and the run stops. This is an injection-escalation path, not a general human takeover of the session. — same page
- Credentials: Power Platform internal storage or Azure Key Vault; access control allowlist of URLs/apps; enforce-HTTPS toggle; "maker-provided credentials" default with a warning that anyone sharing the agent acts with the author's access — same page
- Third-party claim of GA on 13 May 2026 with Purview audit logging — [Digital Applied](https://www.digitalapplied.com/blog/copilot-studio-computer-use-agents-ga-deep-dive) (unverified blog)
- Retirement notice: OpenAI CUA and several Claude models lose support in the standard harness on 26 Nov 2026, migrating to GPT-6 Sol — [Pupuweb reproducing MC1525997](https://pupuweb.com/mc1525997-microsoft-copilot-studio-end-of-support-for-computer-use-models-in-standard-harness/) (secondary; unverified)
- Determinism/replay: not mentioned anywhere in the computer-use doc. "Because it's AI-powered, it adapts to interface changes" is the stated value proposition, i.e. the opposite bet from Handrail. — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)

**OpenAI Operator / ChatGPT agent**
- Operator launched January 2025 (virtual machine, "limited internet connectivity and with safety restrictions"; "struggled with complex user interfaces"); ChatGPT agent launched July 2025 and let users "interrupt tasks or give additional instructions" — [Wikipedia: OpenAI Operator](https://en.wikipedia.org/wiki/OpenAI_Operator)
- Operator folded into ChatGPT agent starting 17 July 2025; standalone shut 31 Aug 2025 (secondary sources) — [The Neuron](https://www.theneuron.ai/tools/openai-operator/review/)
- ChatGPT agent reportedly removed from ChatGPT in early August 2026 with the help-center note "ChatGPT agent is no longer available. Use ChatGPT Work for longer, multi-step tasks"; ChatGPT Work launched 9 July 2026 — [CollectiveBrain (German)](https://collectivebrain.de/chatgpt-agent-abgeschaltet-alternativen-unternehmen-2026/); [Wikipedia](https://en.wikipedia.org/wiki/OpenAI_Operator). The OpenAI help-center page itself returned 403 to fetch, so the removal rests on secondary sources. **Unverified at the primary source.**
- Codex "Background Computer Use" released 16 Apr 2026 for macOS desktop work — [Digital Applied](https://www.digitalapplied.com/blog/computer-use-agents-2026-claude-openai-gemini-matrix) (blog; unverified)

**Anthropic computer use** (primary source: platform docs)
- `computer_toolset_20260801` is stable on the Claude API and Google Cloud, beta on AWS Bedrock and Microsoft Foundry, not available in Claude Managed Agents; no beta header needed. Supported on Claude 5 and 5.5 families; older 4.x models use `computer_20251124` with a beta header. — [Claude docs: computer use tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- Pricing: no separate fee; "each screenshot costs roughly 1,000-1,800 input tokens, which makes long loops expensive" — same page
- Guardrails: dedicated VM/container, domain allowlist, prompt-injection classifiers on screenshots (opt-out via support), recommendation to "ask a human to confirm actions with meaningful real-world consequences, such as ... completing financial transactions." Client-side tool; screenshots stay in your environment; ZDR-eligible. — same page
- "The visible content does not mention audit logging or deterministic replay ... Any logging or replay capability would be something you build yourself." — same page
- Claude in Chrome: "limited beta" browser agent — [tldv blog](https://tldv.io/ru/blog/claude-enterprise-pricing/) (secondary; current enterprise availability unverified)
- A third-party estimate of $0.15-$0.85 per completed computer-use task — [CostBench](https://costbench.com/software/ai-computer-use/claude-code/hidden-costs/) (unverified)

**Google Project Mariner / Gemini computer use**
- Gemini 2.5 Computer Use model launched Oct 2025 (public preview 7 Oct 2025) and was reportedly shut down 28 Jul 2026; June 2026 changelog names Gemini 3.5 Flash as the recommended Computer Use model, "charged as regular tokens per model pricing" — [Tech Dev Notes changelog mirror](https://techdevnotes.com/releases/gemini-docs/20260624-180336Z-7d0f68320867); [Simular alternatives page](https://www.simular.ai/alternatives/gemini-computer-use-alternatives) (competitor; unverified)
- Project Mariner remained a Google Labs limited-access project; no 2026 pricing or GA found — [Google AI dev forum](https://discuss.ai.google.dev/t/when-will-project-mariner-be-powered-by-the-new-computer-use-model/107122)

**Browserbase / Stagehand**
- $40M Series B led by Notable Capital with CRV and Kleiner Perkins, $300M valuation (June 2025 per Sacra; April 2025 per CB Insights) — [SiliconANGLE](https://siliconangle.com/2025/06/17/browserbase-reels-40m-browser-automation-tools/); [Sacra](https://sacra.com/c/browserbase); total ~$67.5M — same
- Stagehand is MIT-licensed open source — [Vantaige](https://vantaige.io/ar/ai-tool/stagehand) (aggregator)
- Hosted pricing conflicts: Hobby $20/mo (100 browser hours) per one source; $39 Starter / $499 Pro per a sponsored teardown — [MakerStack](https://makerstack.co/reviews/browserbase-review/) (unverified)
- Positioning: headless browser infrastructure for agents, not an end-user automation product; no audit or replay claims found.

**Emergence AI**
- $97.2M equity round led by Learn Capital (June 2024) plus ~$100M venture debt; Caplight lists $197.2M total — [SiliconANGLE](https://siliconangle.com/2024/06/24/ai-startup-emergence-ai-raises-ton-cash-enhance-office-worker-productivity/); [Caplight](https://www.caplight.com/company/emergence)
- Product: Multi-Agent Orchestrator (Dec 2024) that "plans a job, delegates it and chooses the best route"; monetised via a premium API — [CO/AI](https://getcoai.com/news/emergence-ais-new-orchestrator-coordinates-agents-across-different-applications); press release — [Silicon UK](https://www.silicon.co.uk/press-release/emergence-ai-debuts-autonomous-multi-agent-orchestrator-advancing-web-automation-for-enterprise-efficiency)
- Leadership: sources disagree whether Satya Nitta is CEO or executive chairman (Ian Eslick named CEO in later profiles) — [Exa directory](https://exa.ai/websets/directory/emergence-executives)
- An aggregator lists a $300M round in Oct 2025; uncorroborated — [Exa funding](https://exa.ai/websets/directory/emergence-funding) (unverified)

**Adept**
- June 2024: Amazon hired CEO David Luan and co-founders, licensed Adept's models in a "reverse acquihire"; Adept had raised $415M+ at ~$1B valuation; investors repaid — [Semafor](https://www.semafor.com/article/08/02/2024/investors-in-adept-ai-will-be-paid-back-after-amazon-hires-startups-top-talent); [TechCrunch, Aug 2025](https://techcrunch.com/2025/08/23/amazon-agi-labs-chief-defends-his-reverse-acquihire/)
- Luan led the team behind Amazon Nova Act; GeekWire reports in 2026 that he is leaving Amazon, "latest exit from high-profile Adept deal" — [GeekWire 2026](https://www.geekwire.com/2026/head-of-amazons-agi-lab-is-leaving-in-latest-exit-from-high-profile-adept-deal/)

**Kognitos** (RPA-replacement, "no hallucinations" positioning)
- $25M Series B (June 2025) led by Prosperity7 with Khosla, Wipro Ventures; "neurosymbolic AI platform ... ensuring no hallucinations and full governance"; plans to deepen presence in "banking and healthcare"; current customers in manufacturing, CPG, retail, logistics, telecom — [BusinessWire](https://www.businesswire.com/news/home/20250624144427/en/Kognitos-Launches-Neurosymbolic-AI-Platform-for-Automating-Business-Operations-Ensuring-No-Hallucinations-and-Full-Governance-Backed-by-$25M-Series-B); [FinSMEs](https://www.finsmes.com/2025/06/kognitos-raises-25m-in-series-b-funding.html)
- Claims agents "use computer vision and browser automation to operate green screens, Citrix desktops" — [Kognitos blog](https://www.kognitos.com/blog/ai-in-legacy-systems/) (vendor)
- Crustdata: headcount down 26% YoY, no new round in 15 months (Oct 2026) — [Crustdata](https://profiles.crustdata.com/company/kognitos)

### Inferences
- The incumbents price computer use per step (Microsoft: 5 credits/step; UiPath: Platform Units per LLM call). Every replay of the same task costs the same again. Handrail's zero-model replay path is a direct cost argument against this metering, especially for a task run hundreds of times a day.
- The model labs explicitly push audit, approval and replay back onto the integrator ("something you build yourself"). That is the layer Handrail is.
- OpenAI's exit from consumer agent products and Microsoft's model-retirement notice show how fast the model layer churns; a compiled capability that does not depend on a specific model at replay time is insulated from that churn.

### Gaps
- Could not fetch the OpenAI help-center page (403), so the August 2026 ChatGPT agent removal is only secondarily sourced.
- UiPath and Automation Anywhere agentic unit prices are quote-only; no primary price list exists.
- No primary Gartner text was accessible; see Q4.

## Key question 3: Who does record-once/replay-without-model, live-session human takeover, and audit evidence for regulated industries?

### Takeaway
Model-free replay exists as a cost optimisation in Skyvern (code caching) and Browser Use (`workflow-use`), and in small open-source projects (relaywright, taprun), always with "fall back to the agent" semantics. Live-session human takeover was a consumer feature (ChatGPT agent interrupt) and is a half-feature in Microsoft (email a reviewer on suspected injection). Hash-chained audit logs appear only in hobby projects; no commercial product found advertises tamper-evident run evidence.

### Cited Findings

**Record once, replay deterministically without the model**
- Skyvern code caching: cached code "skipping LLM inference and screenshot analysis"; on unexpected state "Skyvern re-runs with the full agent and regenerates the cache" — [Skyvern docs](https://skyvern.com/docs/developers/features/code-caching)
- Browser Use `workflow-use`: "Deterministic, Self Healing Workflows (RPA 2.0)"; JSON workflow recorded from a session; fallback to agent on step failure; a fork notes a "no-AI mode that runs workflows through Browser-Use Cloud, with no LLM calls, uses semantic mapping" — [SourcePulse](https://www.sourcepulse.org/projects/2513677); [HarleyCoops fork](https://github.com/HarleyCoops/workflow-use)
- Caddi: screen recording becomes "a deterministic, API-driven automation rather than a script that must be manually coded" — [GeekWire](https://www.geekwire.com/2025/this-seattle-ai-startup-watches-you-work-then-automates-the-tedious-back-office-tasks/)
- relaywright (open source, Apache-2.0, 0 stars, 41 commits, v0.1.0-rc.1, individual GitHub account): "Record once, replay with zero LLM tokens"; agent explores once, saves a YAML skill, `skill_run` replays without a model; on breakage returns a "heal block" and the model patches only that step; "hands [login] to a person and keeps credentials out of the model"; audit logs in `~/.relaywright/audit/` with `relaywright audit verify` checking the hash chain; domain allowlist — [github.com/JiangnanZhang-2006/relaywright](https://github.com/JiangnanZhang-2006/relaywright). **This is the closest public design to Handrail, and it is a one-person pre-release project.**
- Taprun: "an AI step compiles a .flow.json program once, then replays it at zero AI cost" — [taprun.dev](https://taprun.dev/integrations/browser-use.html) (vendor; unverified)
- Conduit: "hash-chained log to replay and inspect exactly what the agent did" — [github.com/bkauto3/conduit](https://github.com/bkauto3/conduit) (small OSS; unverified)
- TERX: "self-healing replay (LLM fallback on DOM drift)" — [PyPI terx](https://pypi.org/project/terx/0.3.1/)
- TinyFish newsletter frames "compile to code" as a recognised practitioner pattern — [TinyFish Current](https://current.tinyfish.ai/issue/24/practitioners-corner/article/12828/compile-to-code-the-pattern-that-turns-agent)
- UiPath classic RPA is deterministic by construction but its computer-use product (ScreenPlay) is model-driven on every run; no replay claim found — [ScreenPlay docs](https://docs.uipath.com/agents/automation-cloud/latest/user-guide-screenplay/overview)
- Microsoft: no replay; "adapts to interface changes" on every run — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)
- Anthropic docs: replay "would be something you build yourself" — [Claude docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- A June 2026 arXiv paper argues "Agentic AI Needs Deterministic Environments" ("Grounded Scaling") — [arXiv 2606.22495](https://arxiv.org/pdf/2606.22495) (not read in full)

**Human takeover of the live session**
- ChatGPT agent (July 2025): users "can interrupt tasks or give additional instructions" — [Wikipedia](https://en.wikipedia.org/wiki/OpenAI_Operator). Product retired Aug 2026 (secondary).
- Microsoft Copilot Studio: "Human supervision" emails a reviewer only when the agent "detects potentially harmful instructions"; the run stops if no response within the time limit; conversational agents see "reasoning messages and screenshots" in chat — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)
- Skyvern: "human-in-the-loop" is an Enterprise line item with no description — [skyvern.com/pricing](https://www.skyvern.com/pricing)
- Zomma: "every action stops for human approval before anything submits" — [YC: Zomma](https://www.ycombinator.com/companies/zomma) (snippet)
- relaywright: hands login/captcha steps to a person — [relaywright](https://github.com/JiangnanZhang-2006/relaywright)
- I found no commercial product that describes a human taking over the same live browser session mid-run and handing back to the deterministic engine.

**Audit / evidence for regulated industries**
- Skyvern Enterprise: SOC 2 Type II, HIPAA; "Audit: Not mentioned" on pricing page — [skyvern.com/pricing](https://www.skyvern.com/pricing)
- Browser Use: SOC 2 Type II, HIPAA, on-prem, ZDR; no audit-trail feature named — [browser-use.com/pricing](https://browser-use.com/pricing)
- Microsoft: Azure Key Vault credentials, allowlists, maker-credential warning; third-party blog says audit logging to Purview — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use); [Digital Applied](https://www.digitalapplied.com/blog/copilot-studio-computer-use-agents-ga-deep-dive) (unverified)
- Kognitos markets "audit-defensible automation" that "produces an entry in the audit log for every decision, cites the rule the system executed, version-controls the rules with approval evidence, and routes high-risk cases to a human" — [Kognitos blog](https://www.kognitos.com/blog/what-is-intelligent-automation/) (vendor)
- Apify's Playwright runner advertises "a per-action audit trail and bills only successful actions ($0.004 per successful browser action)" — [Apify](https://apify.com/moneyagent_lab) (vendor)
- Hash-chained logs: only relaywright and Conduit (both tiny OSS) — links above

### Inferences
- "Replay without a model" is converging as a cost feature, not a governance feature. Nobody ships the artifact as a reviewable, versioned, typed object with a declared commit step and a named approver. That is Handrail's distinct position.
- "Human-in-the-loop" in this market means either (a) approve-before-submit (Zomma, Anthropic guidance), or (b) escalate-on-suspicion (Microsoft). Neither is "take over the live session, fix it, hand back, and the fix is recorded." Handrail's ladder (classifier, bounded model, human on the same session) has no public equivalent among commercial products.
- Tamper-evident evidence is unclaimed territory at the commercial level; the idea exists only in hobby repos, which suggests demand is nascent rather than absent.

### Gaps
- Enterprise products (UiPath ScreenPlay, AA APA) may have audit features behind the paywall that are not in public docs; I could not read their enterprise documentation.
- relaywright's actual replay robustness is unverified beyond its README.

## Key question 4: What reviewers, HN threads and G2/Capterra say are the weaknesses

### Takeaway
Three complaints recur across HN and review sites: (1) non-determinism and low consistency ("fail in step 2 or 3", "prefer the brittleness of scripts to non-deterministic workflows"), (2) cost per run ("pricing is utterly insane", "$0.10 of 1 page interaction"), and (3) for incumbent RPA, brittle selectors and maintenance after every UI or version change. Safety and credential handling were raised loudly at Skyvern's launch; audit trail and human handoff were conspicuously absent from the conversation, which reads as an unarticulated gap rather than a solved problem.

### Cited Findings

**Hacker News on browser agents**
- Launch HN: Skyvern (YC S23), Oct 2024: "Cool but pricing is utterly insane" (ProofHouse); "For the $0.10 of 1 page interaction charged by Skyvern, I can create several scripts using O1" (rmbyrro); launch post concedes "Skyvern is still quite expensive to run"; "The reliability part of autonomous agent has to become really really reliable first" (wintonzheng); "we could use assertions to verify steps had succeeded/failed ... can't see that option in Skyvern" (sahmeepee); "expecting them to pass over their website login credentials and apparently their credit card details too, in plain text" (sahmeepee); "not a single paragraph on safety" (bbor); founder: "you can cut out a decent number of LLM calls by doing static analysis of the page" and "Phase 3: build the thing that builds the playwright thing." "No commenter raised hallucination or human handoff directly." — [HN item 41936745](https://news.ycombinator.com/item?id=41936745)
- Show HN: Skyvern, Mar 2024: a commenter "found the rate of hallucinations to be a bit too high to be used in production" with earlier vision-only approaches; "relying on image-only analysis with X,Y coordinate interactions wasn't able to offer high enough reliability for production workflows" — [HN item 39706004](https://news.ycombinator.com/item?id=39706004)
- Ask HN, Jan 2026 (Browser Use vs Skyvern for directory submission): "the quality/consistency is very low even with different models and detailed prompts ... They fail to understand the task or fail in step 2 or 3." — [HN item 46600252](https://news.ycombinator.com/item?id=46600252)
- "AI agents: Less capability, more reliability, please" (Mar 2025): a commenter reported "impressive demos but constant production incidents" and pivoted "to more constrained workflows with human checkpoints" — [HN item 43535653](https://news.ycombinator.com/item?id=43535653)
- Widely re-quoted HN sentiment: preferring "the brittleness of scripts to non-deterministic workflows for critical production tasks"; consensus that agents "work well for single-step tasks and supervised workflows, but fully autonomous multi-step tasks still need human-in-the-loop checkpoints" — [TestMu AI](https://www.testmuai.com/blog/state-of-ai-browser-agents-2026/) (secondary; original thread not located)
- Anthropic computer-use tester on HN: "I cannot reliably extract specific pixel coordinates from just viewing the screenshot" (drothlis) — [HN item 41936745](https://news.ycombinator.com/item?id=41936745)
- Perplexity Comet indirect prompt injection thread (97 points, 31 comments) — cited by [Firecrawl](https://www.firecrawl.dev/blog/best-browser-agents) (secondary)

**Vendor and practitioner write-ups**
- Skyvern's own benchmark lists "hallucinating that it's achieved the goal when it has not" as a failure mode — [Skyvern Web Bench](https://www.skyvern.com/blog/web-bench-a-new-way-to-compare-ai-browser-agents/)
- Third-party self-host comparison: an agent saying "done" is not evidence the workflow finished correctly — [DEV: Browser Use vs Skyvern self-hosted](https://dev.to/jangwook_kim_e31e7291ad98/browser-use-vs-skyvern-self-hosted-setup-trade-offs-and-completion-verification-1l5c)
- "Cost per completed task = total cost of all attempted runs / verified successful tasks, including retries and human time" — [BrowserAct](https://www.browseract.com/blog/browser-agent-reliability-metrics) (vendor)
- Practitioner failure: a sub-task "hit a captcha ... It just waited 90 minutes for an element that was never going to appear" — [HackerNoon](https://hackernoon.com/the-worst-ai-agent-failures-dont-crash-they-just-stop-being-useful)
- TestMu: "because an agent is non-deterministic, a single passing run proves little"; Online-Mind2Web results "cluster near 30% for typical agents" — [TestMu AI](https://www.testmuai.com/blog/state-of-ai-browser-agents-2026/)
- InfoWorld, "When will browser agents do real work?" — [InfoWorld](https://www.infoworld.com/article/4081396/when-will-browser-agents-do-real-work.html) (not read in full)

**G2 / Capterra / PeerSpot on incumbents**
- UiPath (Capterra): "difficult to capture a UI element when the selectors are often changing"; "the bot must be adjusted whenever [external applications] are updated"; "frequent version changes and stability issues, which sometimes broke existing workflows"; "without maintenance, a UiPath bot cannot run well"; pricing split between "expensive" and "cost-effective" — [Capterra UiPath reviews](https://www.capterra.com/p/135186/UiPath-Robotic-Process-Automation/reviews/); [PeerSpot](https://origin.peerspot.com/products/uipath-reviews/page-2)
- UiPath (AWS Marketplace): "complex initial setup across several components, each with its own installation and maintenance requirements" — [AWS Marketplace reviews](https://aws.amazon.com/marketplace/reviews/reviews-list/B08Z5YWC8H?page=22)
- Automation Anywhere (G2 summaries): "pricing model to be expensive and complex, especially for small teams"; "steep learning curve"; "software bugs that disrupt automation processes"; "bot issues with complex UI and debugging challenges"; PeerSpot: "implementation cost even for a POC was very high" — [G2 AA APA](https://ai.g2.com/product/automation-anywhere-agentic-process-automation); [PeerSpot AA AI Agent pros and cons](https://www.peerspot.com/products/automation-anywhere-ai-agent-pros-and-cons)
- UiPath's own docs on computer use: "performance may not always match traditional workflow automations" — [Impress IT](https://it.impress.co.jp/articles/-/27757)

**Analyst framing**
- Gartner Market Overview for RPA (23 Feb 2026) names "computer use," agentic automation and business orchestration as the trends reshaping RPA — [Gartner document 7488853](https://www.gartner.com/en/documents/7488853) (abstract only; paywalled)
- Gartner's first Hype Cycle for Agentic Automation reportedly 7 Jul 2026; prediction that 60% of organisations will adopt agent orchestration platforms from outside their systems-of-record vendors by 2030 — [Kissflow summary](https://kissflow.com/no-code/gartner-hype-cycle-agentic-automation/) (secondary)
- Gartner 2025 MQ data via SAP: RPA revenue $3.8B, up 18% — [SAP](https://www.sap.com/resources/gartner-magic-quadrant-robotic-process-automation)
- TechCrunch (Apr 2024) on RPA vendors' relevance against agents — [TechCrunch](https://techcrunch.com/2024/04/28/how-rpa-vendors-aim-to-remain-relevant-in-a-world-of-ai-agents)

### Inferences
- The two loudest complaints (non-determinism, per-run cost) are both consequences of putting a model in the loop on every run. The incumbents' loudest complaint (brittle selectors, maintenance) is the consequence of having no model at all. Handrail's "model once, deterministic after, bounded model only when a check fails" is a direct answer to both halves, and that is the sentence to lead with.
- The sahmeepee comment ("assertions to verify steps had succeeded") is a user asking for Handrail's verify-from-the-card design in 2024.
- Nobody on HN asked for audit trails or evidence, which suggests the buyer who cares (compliance, internal audit at a bank) is not the HN reader. Position the evidence feature to that buyer, not to developers.

### Gaps
- Could not open G2's own UiPath page; UiPath weaknesses come from Capterra, PeerSpot and AWS Marketplace.
- The frequently quoted "prefer the brittleness of scripts" HN comment could not be traced to its original thread.
- Only the first comment of the TinyFish HN thread rendered; no criticism captured from it.

## Key question 5: Who sells specifically to banks, credit unions, healthcare, insurance, government?

### Takeaway
The vertical push is young and mostly 2025-2026: Zomma (YC S26) for hedge funds, asset managers and fintechs; Basepilot (YC W24) for insurers, TPAs and MGAs; Cyberdesk (YC S25) and Pomerado (YC F26) name EHRs; Caddi targets law firms and financial advisors; Kognitos says it plans to enter banking and healthcare; Microsoft and UiPath sell horizontally to all of them through existing enterprise agreements. I found no startup publicly targeting credit unions or government with computer-use agents.

### Cited Findings
- Zomma (YC S26): "AI BPO for financial services run by computer-use agents"; KYC reviews, transaction alerts, disputes, reconciliation, investor reporting; "hedge funds, asset managers, and fintech firms" — [YC: Zomma](https://www.ycombinator.com/companies/zomma); [YC listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Basepilot (YC W24): "AI agents for insurance claims"; "insurers, TPAs and MGAs" — [YC: Basepilot](https://www.ycombinator.com/companies/basepilot); [Extruct](https://www.extruct.ai/hub/basepilot-com-funding/)
- Cyberdesk (YC S25): "EHR appointment entry and processing files in legacy ERPs" — [YC listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Pomerado (YC F26): back-office workflows "on legacy ERP, EHR, and CRM systems" — [YC listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Caddi: "legal and financial sectors"; law firms and financial advisors — [FinTech Global](https://fintech.global/2025/03/06/caddi-bags-5m-seed-funding-to-drive-ai-powered-workflow-automation-in-legal-and-financial-sectors/)
- Kognitos: "plans to deepen its presence in highly regulated industries such as banking and healthcare" (a plan, not customers) — [FinSMEs](https://www.finsmes.com/2025/06/kognitos-raises-25m-in-series-b-funding.html)
- Orby (now Uniphore): customers in "technology, insurance, consumer goods, and real estate" (2024) — [VentureBeat](https://venturebeat.com/ai/orby-ai-raises-30m-to-use-generative-ai-to-automate-your-most-tedious-work-tasks)
- Reform (YC W24): critical industries "run on outdated systems" — [YC listing](https://www.ycombinator.com/companies/industry/workflow-automation)
- Banking-specific context: PYMNTS, "Banks Add AI Agents, Keep Their 40-Year-Old Cores" describes computer use as a way for agents "to work through the same screens an employee uses" — [PYMNTS 2026](https://www.pymnts.com/news/artificial-intelligence/2026/banks-add-ai-agents-keep-their-40-year-old-cores/)
- Maximum raised $30M seed (CRV) in Aug 2026 to replace legacy bank cores with an AI-native core, arguing batch cores leave agents on stale data; core migration takes 18-24 months — [TechTimes](https://www.techtimes.com/articles/322922/20260804/legacy-bank-cores-cannot-power-ai-agents-maximum-raises-30m-replace-them.htm)
- FlowX.AI recommends API gateway + agent orchestration, with "RPA only for systems with no API"; FlowX and Sutherland partner on prebuilt agents over existing cores — [FlowX hub](https://www.flowx.ai/hub/ai-banking-automation-platforms-that-bridge-legacy-cores-in-2026) (vendor)
- Abstracta built an open-source AS/400 (IBM i) MCP server to sit between core systems and agents — [Abstracta](https://abstracta.us/blog/ai/ibm-systems-in-banking) (vendor)
- Microsoft Copilot Studio ships finance demo scenarios (invoice processing, portfolio lookup) and credential handling via Azure Key Vault, with Anthropic models gated by an admin "external models" toggle — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)
- Skyvern and Browser Use both list HIPAA on their enterprise tiers, implying healthcare sales — [skyvern.com/pricing](https://www.skyvern.com/pricing); [browser-use.com/pricing](https://browser-use.com/pricing)

### Inferences
- Zomma is the nearest direct competitor by customer: same "no integration, same screens" pitch, same finance back office, with a blanket approve-before-submit. Its gap versus Handrail: it is a BPO (it does the work for you) rather than a compiled, reviewable capability the bank owns; no public claim of deterministic replay or tamper-evident evidence.
- Credit unions and community banks (Jack Henry / Fiserv / FIS cores with thin APIs) are unclaimed by any startup found. Government is entirely unclaimed in this search.
- The "replace the core" camp (Maximum, 10x) and the "overlay the core" camp (FlowX, Kognitos, Zomma, Handrail) are both betting banks will not migrate soon; the 18-24 month migration figure supports the overlay camp for the next several years.

### Gaps
- No evidence found of any named bank or credit union customer for any computer-use startup; all vertical claims are from company self-descriptions.
- No source found for government-sector computer-use agents.
- No healthcare-specific pricing found.

## Key question 6: Gaps Handrail's design could fill (synthesis)

### Takeaway
Across roughly thirty products, the unfilled combination is: a run compiled into a typed, versioned, reviewable artifact; replay with zero model calls as the default (not a cache with agent fallback); a classifier-then-model-then-human ladder where the human takes the same live session and hands back; declared commit steps gated by a named approver; and hash-chained evidence of every run. Each piece exists somewhere in isolation; no one ships the set, and no one ships it to banks.

### Cited Findings
- Skyvern caches code but re-runs the agent on any surprise; cache is an optimisation — [Skyvern docs](https://skyvern.com/docs/developers/features/code-caching)
- Browser Use `workflow-use` falls back to the agent and admits the fallback "is currently really bad" — [SourcePulse](https://www.sourcepulse.org/projects/2513677)
- Microsoft bills every step at 5 credits every run and markets model adaptation, not determinism — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)
- Anthropic says audit and replay are "something you build yourself" and recommends human confirmation before "completing financial transactions" — [Claude docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- Zomma stops every action for approval (no distinction between read steps and commit steps) — [YC: Zomma](https://www.ycombinator.com/companies/zomma)
- Only hobby projects (relaywright, Conduit) mention hash-chained logs — [relaywright](https://github.com/JiangnanZhang-2006/relaywright); [Conduit](https://github.com/bkauto3/conduit)
- HN user asked for step assertions and found none in Skyvern — [HN item 41936745](https://news.ycombinator.com/item?id=41936745)
- Pomerado exposes websites as MCP but without a review or approval layer in its description — [YC: Pomerado](https://www.ycombinator.com/companies/pomerado)

### Inferences
- Positioning sentence that the evidence supports: "The agents compete on how well a model handles the hundredth run. Handrail competes on never needing a model for the hundredth run, and proving what happened on every one."
- Pricing wedge: competitors meter per step or per token on every run. Handrail can price per capability or per seat, with replay effectively free, and make the escalation-rung calls (classifier/LLM) the only metered events; `RunResult.classifier_calls` and `llm_calls` being separate and zero on the ordinary path is already a billing statement.
- Buyer wedge: the HN crowd wants reliability and low cost; the bank buyer wants evidence and named approval. Handrail is the only product in this map whose design serves both at once.
- Risk to watch: Skyvern or Browser Use could promote their cache to a first-class artifact with approvals in one release; Microsoft could add Purview-backed replay. Handrail's defensible part is the combination plus the regulated-vertical focus, not any single mechanism.

### Gaps
- No pricing benchmarks exist for "per capability" products in this space, so Handrail's price point has no public comparable.
- Whether banks will accept a deterministic replayer that was authored by a model (model-authored, human-reviewed) is a buyer question this research cannot answer from public sources.
