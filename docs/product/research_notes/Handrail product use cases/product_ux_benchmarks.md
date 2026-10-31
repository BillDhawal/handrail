# Product and UX benchmarks for a "record once, replay deterministically, human takes over when stuck" UI (as of 2026-10)

Scope note: this is a catalogue of concrete UI patterns from automation, computer-use, synthetic-monitoring and co-browsing products, mapped to Handrail's stages (author -> review/approve -> run -> escalate/take over -> monitor -> consume). Everything cited is from vendor docs, changelogs, pricing pages or public threads fetched 2026-10-31. Where a vendor page could not be fetched (403/404) or the web-search budget ran out, it is listed under Gaps rather than guessed.

Method caveat: the shared web-search budget was exhausted part way through; the last batches were direct fetches of known URLs only. Several vendor marketing pages (OpenAI, mabl help center, UiPath Task Capture) returned 403/404 and are recorded as gaps.

---

## 1. Recording / authoring UI: how products show actions as they happen, let a human intervene, and mark risky steps

### Takeaway
The mature pattern (UiPath App/Web Recorder, Power Automate Desktop recorder, Playwright codegen, Skyvern's new code-first recorder) is a side panel that fills with one card per action in real time, each card carrying a screenshot and an editable target, with a Record/Pause control and a per-step delete. No surveyed product has a first-class "mark this step as irreversible / commit" affordance during recording; the closest analogues are UiPath's "Confirm every step" toggle (confirm the target, not the risk) and Zapier/Skyvern approval steps added after the fact. Handrail's "confirm which presses are commits" prompt is a genuine gap in the market.

### Cited Findings

**UiPath App/Web Recorder (Studio desktop)**
- Opened from the Studio ribbon or Ctrl+Alt+R; the window has **Record** and **Pause** buttons, a **Confirm every step** toggle ("makes you confirm each target's anchors before recording"; hold Shift on one click to confirm a single step), an Object Repository toggle, an **Input Mode** menu (Auto / Chromium API / Window Messages / Hardware Events / Simulate), and **Save and return to Studio** — [UiPath App/Web Recorder docs](https://docs.uipath.com/activities/other/latest/ui-automation/app-web-recorder.md)
- "Elements highlight as you move the mouse over them. Clicking one records its default action." A **Choose action** menu appears beside the element for non-default actions (Get Text, Hover, Highlight); it can be pinned open or switched between icon and list layout — [same](https://docs.uipath.com/activities/other/latest/ui-automation/app-web-recorder.md)
- Live preview: "Recorded actions appear as activities with screenshots in the preview under the Recorded Steps header, which you can collapse." Each activity card has a delete icon top-right; Type Into lets you edit the text, Get Text lets you choose the output variable — [same](https://docs.uipath.com/activities/other/latest/ui-automation/app-web-recorder.md)
- "The recorder displays a preview of the activities that will be added to your project in real time... The preview includes informative screenshots that are also added to the activities in the automation project." — [UiPath App/Web Recorder overview](https://docs.uipath.com/activities/docs/app-web-recorder)
- F2 adds a 5-second delay during element selection for off-screen elements — [same](https://docs.uipath.com/activities/other/latest/ui-automation/app-web-recorder.md)

**UiPath Studio Web Autopilot Recorder (the model-assisted version, docs updated 2026-04-16)**
- Opened from a **Use Browser** activity; the panel has an activity list with a plus button and a prompt field "Describe your actions on this page". A "Generate with Autopilot" placeholder card is created first; clicking **Test** runs the generated activities "as a best-effort, default-configured attempt. Executed activities are marked with a green checkmark." If the prompt is not fully covered, a **Continue 'prompt'** button generates the next activities; the user alternates Continue and Test — [UiPath Autopilot Recorder](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/ui-automation-autopilot-recorder)
- "If a test fails, you can interact with the application manually to perform the remaining steps." Manual steps: plus button, select a **target** on screen and optionally an **anchor**, **Confirm**. "Selecting an activity card... triggers a five-second highlight of its target and anchors." — [same](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/ui-automation-autopilot-recorder)
- Cards drag-to-reorder; hamburger menu has Properties / Rename / Delete; "The Delete key removes the selected card with no confirmation prompt." Esc after changes prompts to save — [same](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/ui-automation-autopilot-recorder)
- Limits: no loops or conditionals; prompt-generated sequences use only Click, Type Into, Get Text, Select Item, Check/Uncheck; Test unavailable in Safari; Autopilot can be disabled by governance policy ("Allow Autopilot UI" = No), after which only manual steps work — [same](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/ui-automation-autopilot-recorder)
- UiPath's October 2026 release notes list "Autopilot as a coding agent in Studio Web — Public Preview, focused on API workflows" — [UiPath Studio Web release notes Oct 2026](https://docs.uipath.com/studio-web/automation-cloud/latest/release-notes/dedicated-october-2026)

**Microsoft Power Automate for desktop recorder (docs dated 2026-08-31)**
- Flow: click **Recorder** in the flow designer toolbar, click **Record** in the recorder window, act in the app. "The recorder keeps track of mouse and keyboard activity in relation to UI elements, and it records each action separately." — [MS Learn: Record desktop flows](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- Latency affordance: "When you perform a left or right-click on a UI element during the recording, the highlighter displays a **Wait for action** message, instructing you to wait for the recorder to record and insert the action." — [same](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- Right-click an element for a context menu of alternative actions; **Pause** to pause; **Add a comment** inserts a comment among recorded steps; **Done** converts steps to flow actions and "All the UI elements used... are added automatically to the UI elements pane." — [same](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- A **Capturing mode** menu lets the user pick UIA vs MSAA selectors per app (UIA for WPF/WinForms/UWP, MSAA for VB6/Win32 legacy) — [same](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- Custom pop-up screens appear for drop-downs, date pickers and colour pickers so the recorded value is explicit rather than a raw click sequence — [same](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- **Image recording** fallback: enable via the dots menu; "Upon clicking on an element, an image is captured automatically and saved with a default editable name"; **Extract text from image** prompts for a text area then an **anchor area** "that isn't expected to change, such as the label next to a field" (Tesseract OCR) — [same](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- Honest framing in the docs: "Use the recorder to create the backbone of your flow... most recorded tasks should be modified... conditionals and loops can't be recorded... there might be redundant actions in a recording that should be removed." — [same](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow)
- **Record with Copilot (AI recorder) is deprecated** as of the 2026-08-03 doc: "Record with Copilot (also known as the AI recorder) is deprecated and isn't available in Power Automate for desktop." Alternatives named: describe the flow in natural language with Copilot plus the classic recorder, or a Copilot Studio agent with computer use — [MS Learn: Record with Copilot (deprecated)](https://learn.microsoft.com/en-us/power-automate/desktop-flows/create-flow-using-ai-recorder)

**Playwright codegen (the developer-facing reference)**
- `npx playwright codegen` opens the Playwright Inspector beside the browser; generated code appears live: "Playwright will generate the code for the user interactions which you can see in the Playwright Inspector window." Controls: **Record** (press again to stop), assertion icons (assert visibility / text / value, then click an element), **Copy**, **Clear**, and **Pick Locator** (appears after stopping) — [Playwright codegen](https://playwright.dev/docs/codegen)
- Pick Locator: "hover over elements in the browser window to see the locator highlighted underneath each element"; clicking fills an editable field, "edit the locator in this field to fine tune it" — [same](https://playwright.dev/docs/codegen)

**Skyvern (model-driven authoring and the new recorder, July 2026 changelog)**
- Code-first browser recording (preview): "A live browser session shows a red recording indicator" and a "live draft panel" beside the session "builds workflow code step by step, with a screenshot for each step." — [Skyvern changelog July 2026](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Workflow Studio pairs a build canvas with a run timeline and a Past Runs tab; "resizable, drag-to-reorder panes," "full-screen YAML editing mode," "an unsaved-changes indicator that summarizes what changed," and the editor "highlights run-blocking blocks and disables Run until they're resolved." — [same](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Copilot: "A credential card appears in chat when Copilot needs a login" and a "live action timeline" in MCP sessions — [same](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Per step the agent "takes a screenshot of the page, then an LLM picks the next action (click, type, select, scroll, upload or extract)"; each run records "a screenshot for each action, the reasoning behind each action", plus a browser recording — [Skyvern concepts](https://www.skyvern.com/docs/concepts.md)

**Automation Anywhere Universal Recorder**
- Started from "the Universal Recorder video camera icon... on the top-left of the workbench"; insertion point is the selected action (below it, or before children of a loop); recorded interactions become editable **Capture** actions (change window, capture a different object, select a new action, enable background processing, wait time, output variable). "Secure recording mode prevents bots from capturing certain property values or storing application images." — [Automation Anywhere: Using the recorder](http://docs.automationanywhere.com/r/automation-360/cloud-using-the-recorder)
- The single-step **Capture** action has an Anchor tab with **Capture anchor**; "A dialog box appears, verifying whether the action has correctly identified the main object." — [Automation Anywhere: Capture action](https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/aae-client/bot-creator/commands/cloud-using-recorder-action.html)

**Zapier Agents (approval inserted by instruction, not by UI)**
- You add a sentence to the instructions: "ask for my confirmation through [messaging app] before continuing to the next instructions." The agent "stops and waits for you to confirm." It needs a messaging action to reach you; "You return to Zapier Agents and either approve the request or stop the workflow." Inside a Zap, a **Human in the Loop** action after the agent step sends approvals by email/Slack — [Zapier help: approval steps](https://help.zapier.com/hc/en-us/articles/41776074420493)
- Human in the Loop step statuses: pending keeps the run paused; on decline or timeout the run either continues or stops depending on configuration — [Zapier HITL statuses](https://ob-zapier.helpjuice.com/special-step-run-statuses-in-human-in-the-loop-actions)

**Autotab / Orby / TinyFish (record-and-learn products)**
- Autotab's Show HN describes "a chrome-based browser you can teach to do complex tasks, with a simple API for running them from your app or backend" — [Show HN: Autotab](https://hn.svelte.dev/item/42197741); a tutorial says "the Record button activates the AI agent overlay" — [aiindigo tutorial](https://aiindigo.com/tutorials/getting-started-with-autotab-automate-complex-web-workflows-without-code); a competitor (Skyvern) claims Autotab "records workflows once and generates Python scripts that run headlessly" — [Skyvern blog (competitor, treat with caution)](https://www.skyvern.com/blog/browser-use-vs-autotab-which-ai-automation-tool-is-better/)
- Orby: "observe, learn and automate" — the model watches a user work, then "recommending automation opportunities to the user" — [TechTarget](https://www.techtarget.com/ai/news/366602913/Startup-aims-to-upend-old-school-RPA-with-large-action-model), [CO/AI listing](https://getcoai.com/tool-detail/orbyai/121304/). A comparison page claims Orby's posture "aligns with Uniphore's Business AI Cloud" since Aug 2025 (unverified) — [Beam vs Orby](https://beam.ai/lp/comparison/beam-ai-vs-orby)
- TinyFish: natural-language goal, "Vault feature lets an agent sign in mid-run, and credentials are not exposed to the model"; no recording feature found — [TinyFish vs Browserbase (vendor blog)](https://www.tinyfish.ai/blog/tinyfish-vs-browserbase)

**Bardeen / Axiom / Browse AI (extension recorders; thin, secondary evidence)**
- Bardeen is a Chrome extension with an AI builder that "turns plain-English descriptions into steps"; a G2 excerpt complains "a single Chrome browser window was enough to max out my computer with this extension installed" — [G2 Bardeen](https://g2.com/products/bardeen/reviews); pricing reported from $10/mo with a free plan — [makerstack review](https://makerstack.co/reviews/bardeen-review/)
- Axiom: Chrome extension, "Free 2hr trial; Starter $15/mo; Pro $50/mo; Plus $150/mo; Enterprise $250/mo"; its G2 listing was "marked as no longer valid as of May 2026" — [theaiagentindex comparison](https://theaiagentindex.com/compare/axiom-ai-vs-bardeen)
- Browse AI is positioned as scraping/monitoring from $19/mo — [same](https://theaiagentindex.com/compare/bardeen-vs-axiom-ai)

### Inferences
- Patterns to copy for Handrail's authoring run: (a) a right-hand "Recorded steps" rail that appends one card per action with a thumbnail and the resolved target (UiPath, Playwright codegen, Skyvern); (b) a red recording indicator in the live browser frame (Skyvern) and a "Wait for action" overlay while the step is being captured (Power Automate), so the person does not click twice; (c) target plus **anchor** as the stable locator unit (UiPath, Power Automate image mode), which maps onto Handrail's locator ladder; (d) "Test" after each generated chunk with green checkmarks on executed steps (UiPath Autopilot), which is close to Handrail's "model drives, person watches"; (e) explicit value pickers for drop-downs/dates (Power Automate) so recorded values are typed inputs, not click sequences.
- Marking irreversible steps: none of the surveyed recorders has it. UiPath's "Confirm every step" (hold Shift for one step) is the nearest interaction primitive; reuse the gesture but change the semantics: a modifier-click or a per-card toggle that flips a card to "commit". Zapier and Skyvern show the alternative (a separate approval block inserted later), which loses the moment of authoring context.
- Trap: UiPath deletes a card on the Delete key "with no confirmation prompt"; for a card marked as a commit, require confirmation.
- Trap: Microsoft shipped and then deprecated an AI-watches-you-and-writes-the-flow recorder within roughly two years; the replacement is "describe it, then use the classic recorder". Handrail's model-drives-while-you-confirm approach is the inverse and avoids the narration-to-flow translation problem.

### Gaps
- No primary-source description of Browse AI, Magical, Induced, Orby's actual authoring screens, or Autotab's current UI was retrievable (search budget exhausted; secondary listings only).
- UiPath Task Capture page returned 404 at the attempted path; only a 2022.4 release-note hit was found by search.
- Could not retrieve screenshots of any recorder; descriptions are from docs text.

---

## 2. Reviewing the artifact: step lists, screenshots per step, parameters, version diffs, draft/approved lifecycle with a named approver

### Takeaway
Workato's Recipe Diff is the best-in-class artifact diff (step-level colour coding plus field-level drill-down), but even Workato only promised in-platform review/approval as "on the way". UiPath Autopilot's card list and Skyvern's "unsaved-changes indicator that summarizes what changed" are the nearest to a reviewable step list. No surveyed product shows a draft -> verified -> approved lifecycle with a named approver on the artifact itself; Handrail's lifecycle plus named approval is differentiated.

### Cited Findings
- Workato creates a version on every save: "A new version of the skill or recipe is created when the skill or recipe is saved." Versions tab -> check two versions -> **Compare VXX and VXX**; or from a version page, **Compare to current version** / "Compare to the previous version". **Compare from** / **Compare to** menus update the diff automatically — [Workato recipe diff docs](https://docs.workato.com/recipe-development-lifecycle/compare-versions-with-recipe-diff)
- Colour coding: green = step added, red = step deleted, blue = moved/nested/unnested/config updated/skipped/unskipped with a matching label ("Moved", "Updated config", ...). Expanding a step shows field-level changes: green addition, red removal, grey update "which includes switching datapills and formulas." — [same](https://docs.workato.com/recipe-development-lifecycle/compare-versions-with-recipe-diff)
- Workato product post: "More updates in this area are on the way, including in-platform review and approval steps to manage the integration lifecycle" and "view diffs as part of an in-platform peer review process" — [Workato product hub](https://www.workato.com/product-hub/compare-any-two-versions-of-a-recipe-with-visual-recipe-diffs/). The diff doc does not mention who saved a version or per-version notes — [docs](https://docs.workato.com/recipe-development-lifecycle/compare-versions-with-recipe-diff)
- Skyvern: "an unsaved-changes indicator that summarizes what changed," "recent-activity history on the canvas," "shareable block selection in the URL," and "Read-only workflow canvases let you click through conditional branches." — [Skyvern changelog July 2026](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Skyvern's workflows list shows "reliability badges" — [same](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Datadog Synthetics keeps a **Test Version** column on every run row and the **Compare Screenshots** feature "requires a prior passing run with the same version, start URL, device, browser, and run type" — [Datadog browser test results](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- Zapier Managed MCP mode: "Each action is exposed as its own tool, and you configure the tools at mcp.zapier.com... lets you lock specific field values for each tool" and "The agent can't enable new actions" — [Zapier MCP: how tools work](https://docs.zapier.com/mcp/overview/how-tools-work.md)
- Composio: each toolkit page "shows its tools (with input and output parameters) and authentication methods supported for that toolkit" and the Toolkits dashboard page is for "inspect current toolkit versions, tool and trigger schemas, and supported auth schemes" — [Composio tools and toolkits](https://docs.composio.dev/tool-router/tools-and-toolkits), [Composio dashboard overview](https://docs.composio.dev/kb/guide/dashboard-navigation-overview.md)
- UiPath governance: Autopilot generation can be switched off by policy, leaving manual authoring only — [UiPath Autopilot Recorder](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/ui-automation-autopilot-recorder)

### Inferences
- Copy: Workato's three-colour step diff with labels, and field-level drill-down; apply it to Handrail capability versions (steps, targets/locator ladders, outcomes). Add what Workato lacks: who saved, a note per version, and the approval record inline.
- Copy: a version column on every run row (Datadog) so the run history reads against the artifact version, and so "compare against last good run" is only offered when versions match.
- Copy: Skyvern's "summarize what changed" indicator for unsaved edits, and read-only canvases with clickable branches for approvers who must not edit.
- Copy: Zapier managed-mode "lock specific field values" as the model for exposing a capability with some inputs pinned by the approver.
- Differentiator: a lifecycle chip (draft / verified / approved) on the capability card, with the three verify runs linked and the approver's name and time. No surveyed product shows this on the artifact.

### Gaps
- Whether Workato's in-platform review/approval has shipped by 2026 could not be confirmed (search budget exhausted before a lifecycle-management query ran).
- No product found that pairs "N clean runs against the system of record" with approval; the verify gate is unbenchmarked.

---

## 3. Running and results: run history tables, per-run logs with screenshots, result taxonomies, retry controls, alerting; who explains "why it failed" well

### Takeaway
Playwright Trace Viewer (actions sidebar + before/action/after snapshots + red error line on the timeline) and Datadog Synthetics (per-step card with screenshot, Test Runs table with Steps "completed out of total", AI failure summary that classifies "true failure vs test misconfiguration") set the bar. Skyvern has the most complete result taxonomy for agentic runs (completed / failed / terminated / timed_out / canceled / paused), which maps closely to Handrail's success / business outcome / recoverable / hard failure.

### Cited Findings

**Playwright Trace Viewer**
- Actions tab shows the locator used for each action and its duration; selecting one reveals snapshots, action log and source; "Double-clicking an action filters the Console and Network logs to that action's time range." — [Playwright trace viewer](https://playwright.dev/docs/trace-viewer)
- Snapshots in three types: Before, Action, After; "The Action snapshot shows the exact click position as well as the DOM node." — [same](https://playwright.dev/docs/trace-viewer)
- Timeline: screencast frames as a film strip; drag to select a range; "a red line highlighting where the error occurred." — [same](https://playwright.dev/docs/trace-viewer)
- Tabs: Metadata (browser, viewport, duration), Source, Call (duration, locator, strict mode, key), Log ("waiting for the element to be visible, enabled, and stable"), Errors, Console, Network, Attachments (visual comparison with a slider between expected and actual) — [same](https://playwright.dev/docs/trace-viewer)
- trace.playwright.dev "loads the trace entirely in your browser and does not transmit any data externally." — [same](https://playwright.dev/docs/trace-viewer)

**Datadog Synthetics browser tests**
- Test page tabs: Activity, Test Runs, Performance, Properties. Global Uptime graph "turns red only when the alert conditions for the test are triggered"; "location uptime is computed based on the final test result after retries complete." Timeline shows alert triggers, recoveries and test modifications; selecting an event opens a Summary panel "with the failing result and suggested next steps." — [Datadog test results](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- Test Runs table columns: Status (PASSED/FAILED), Date, Run Type, **Steps (completed out of total)**, Duration, Location, Device, Browser, **Test Version**; filter by status/run type/location/device; click a row for detail — [same](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- Per-step card: "a screenshot of the step action, a link to the session in Session Replay, the step description, starting URL for a given step, step ID, step duration, and page performance information"; LCP and CLS as pills beside the step URL — [same](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- Errors & Warnings tab lists errors by type (`js` / `network`) and status code, max 8 shown; Resources tab max 100, with headers/bodies for XHR when payload capture is on — [same](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- AI failure summary "classifies the failure as a true failure (a real application problem) or a test misconfiguration (a test setup issue), and suggests next steps"; docs warn to "Treat them as a starting point for investigation, not as authoritative root cause analysis"; thumbs up/down feedback — [same](https://docs.datadoghq.com/synthetics/browser_tests/test_results/); Bits Investigation extends this across APM traces, logs, test history — [Datadog blog](https://datadoghq.com/blog/bits-investigation-synthetic-tests/)
- Compare Screenshots: failed run beside last successful run — [docs](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- Named error strings: "Element located but it's invisible", "Cannot locate element", "Select did not have option", "Forbidden URL", "General test failure" — [same](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)

**Checkly**
- Results view "shows where failures happened across browsers and projects. Each failure links to the failing line of code, with the associated traces, videos, screenshots, and snapshots, plus logs scoped to the failed test" (Playwright Check Suites GA, 2025-10-23) — [Checkly changelog](https://www.checklyhq.com/changelog/playwright-check-suites-ga.md)
- Traces/videos retained only on failure for scheduled runs; editor runs keep them regardless; traces open in trace.playwright.dev; "Automatic trace and video creation makes these checks run about 30–50% longer" — [Checkly Playwright support](https://www.checklyhq.com/detect/synthetic-monitoring/browser-checks/playwright-support), [Checkly docs](https://docs.checklyhq.com/docs/browser-checks/playwright-test)
- No retries in the Playwright Test runner; "Double-check on failure" is the alternative — [Checkly docs](https://docs.checklyhq.com/docs/browser-checks/playwright-test)
- Alert types: failure, degradation ("just slow, but still working"), recovery; "browser checks currently do not have a degraded state"; thresholds "after a set number of failures or a set duration of failures"; alert notification log for noise analysis — [Checkly alerting](https://checklyhq.com/docs/alerting)

**Browserbase Session Inspector**
- Open by clicking a session in the Dashboard; **Copy Debug URL** button appears only "when a session is actively running" — [Browserbase session inspector](https://docs.browserbase.com/features/session-inspector)
- Status bar metadata: Session ID, Status "with termination reason if applicable", Started, Region, Duration, Proxy Bandwidth, Settings (keepAlive, context), User Metadata, Extension ID, Expires — [same](https://docs.browserbase.com/features/session-inspector)
- Video replay of up to 10 tabs; speeds 0.5x/1x/2x/4x; retention 30 days (24h on BYOS); recording at `https://browserbase.com/sessions/{session.id}` — [same](https://docs.browserbase.com/features/session-inspector)
- Events timeline (pages loaded, CDP Runtime/Page/Input/Log events, network), Logs (console; captcha events `browser-solving-started` / `browser-solving-completed`), Network tab, Stagehand tab (token usage, execution time, extraction schemas as JSON or Zod) — [same](https://docs.browserbase.com/features/session-inspector)
- Debug table: unexpected termination -> "Check Status Bar for termination reason"; selector not found -> "Use DOM view to inspect element state at failure point"; failed request -> Network tab — [same](https://docs.browserbase.com/features/session-inspector)
- The rrweb DOM replay is marked deprecated in favour of video — [Browserbase session recording](https://docs.browserbase.com/platform/browser/observability/session-recording.md)

**Skyvern**
- Run statuses: created, queued, running, **paused** ("Waiting for a person at a Human Interaction Block"), completed, failed ("Stopped by an error, or reached its step limit"), **terminated** ("Skyvern decided the goal can't be reached on this site"), timed_out, canceled ("Stopped by you") — [Skyvern concepts](https://www.skyvern.com/docs/concepts.md)
- Run page: "Failed Code blocks include a screenshot and the final page URL"; "Screenshots, viewers, and artifact download links refresh automatically instead of expiring"; Run History has "colored tags and auto-detected platform tags, with a bulk tagging toolbar"; analytics "can group by run metadata"; weekly email digest with trend arrows — [Skyvern changelog July 2026](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Mask Secrets setting hides typed values in screenshots and logs — [Skyvern concepts](https://www.skyvern.com/docs/concepts.md)

**n8n (third-party tutorials; verify against official docs)**
- Open an execution, click a node to see input/output JSON; "the failed node is highlighted in red on the canvas. Click the failed node to see the error message, stack trace, and the input data that caused the failure." Retry re-runs with the same trigger data; "Execute Node" runs one node plus required predecessors — [rapidevelopers n8n debugging](https://rapidevelopers.com/n8n-tutorial/how-to-debug-workflows-in-n8n), [executions](https://rapidevelopers.com/n8n-tutorial/how-to-manage-workflow-executions-in-n8n)

**Zapier MCP**
- "Every tool call runs through your app connections and is logged in the History tab at mcp.zapier.com." — [Zapier MCP docs](https://docs.zapier.com/mcp/overview/how-tools-work.md)

### Inferences
- Copy for Handrail's run page: Datadog's per-step card (thumbnail, description, start URL, step id, duration) in a vertical list; Playwright's before/action/after triptych with the click point drawn on the action frame; a red marker on a filmstrip where the first failing check fired; a status bar with a human-readable termination reason (Browserbase).
- Result taxonomy: show Handrail's four typed results as distinct chips and map Skyvern's wording: success, business outcome (Skyvern "terminated: goal can't be reached on this site" is the same idea with worse naming), recoverable (-> escalation ladder), hard failure. Add a "Steps: completed of total" column (Datadog) and a capability version column on every run row.
- "Why it failed": Datadog's two-way classification (application problem vs automation misconfiguration) is exactly the split Handrail's classifier rung produces; surface it as the first line of the failure panel, with the deterministic check that failed quoted underneath, and the model's suggestion labelled as a proposal (consistent with "every rung only proposes").
- Retry controls: Checkly's "Double-check on failure" with no automatic retries for the Playwright runner is the safe default; given Handrail's rule 2 (a dispatched-not-observed commit is never re-executed), the retry button must be disabled or relabelled "resume after commit" when the journal shows a dispatched commit.
- Retention: Checkly keeps traces only on failure to control cost and runtime (+30-50%). Handrail's hash-chained evidence needs screenshots on every run, so expect the same overhead and show it honestly.

### Gaps
- Could not retrieve Checkly's actual check-result page layout (only changelog text); no screenshot-level description.
- Browserbase "DOM view" location in the inspector is not documented on the fetched page.

---

## 4. Human-in-the-loop takeover: what the handoff UI looks like, how control is signalled, how it is logged

### Takeaway
Browser-infrastructure vendors (Browserbase, Anchor, Hyperbrowser, Kernel) all converge on a single primitive: an iframe-embeddable live-view URL that is interactive by default and made read-only with `pointer-events: none` or a `readOnly` flag. Only Cloudflare Browser Run has a structured handoff protocol (instructions -> operator works -> operator clicks **Done** or **Failed** with a reason -> event resumes the script). Browser Use's HITL is pause-via-keepAlive plus a follow-up run on the same session. Co-browsing tools add what browser vendors lack: an explicit consent dialog before control transfers (Cobrowse.io, Upscope) and a "Give control" button with a cursor icon (Surfly in NICE CXone). Skyvern's paused-run review card (Approve / Reject) is the simplest in-product form.

### Cited Findings

**Browserbase Live View**
- "watch, click, type, and scroll in real-time"; framed as "Human in the loop" for iframes, credentials, uploads. API: `bb.sessions.debug(session.id)` returns `debuggerFullscreenUrl`, `debuggerUrl` (with browser borders) and `pages` (one URL per tab) — [Browserbase live view](https://docs.browserbase.com/platform/browser/observability/session-live-view)
- Embed with `sandbox="allow-same-origin allow-scripts"` and `allow="clipboard-read; clipboard-write"`; read-only by adding `style="pointer-events: none;"`; hide navbar with `&navbar=false`; iframe posts `browserbase-disconnected` when the session ends — [same](https://docs.browserbase.com/platform/browser/observability/session-live-view)
- No explicit hand-back API is documented; the docs note some keys such as Tab may need overriding to reach the remote session — [same](https://docs.browserbase.com/platform/browser/observability/session-live-view)
- Use case from the vendor blog: hand the live view to a user at a 2FA/CAPTCHA prompt "without ending the session" — [Browserbase blog](https://browserbase.com/blog/what-is-a-browserbase-browser)

**Browser Use Cloud V4 HITL**
- "Open the live browser, take over, then continue the same session." Start the run with `keep_alive=900` and a task that ends at a checkpoint ("Open the login page and stop for human review"); wait for the `browser.ready` event and read `live_view_url`; the person works in the live view; then create a follow-up run with the same `session_id` which "continues from the current page" with the session's conversation and workspace — [Browser Use HITL](https://docs.browser-use.com/cloud/agent/human-in-the-loop.md)
- "Treat live-view URLs as credentials." Without keepAlive the browser stops about 2 minutes after the run ends; kept time is billed. UI guidance: "replace the terminal prompt with an explicit Continue control." — [same](https://docs.browser-use.com/cloud/agent/human-in-the-loop.md)

**Cloudflare Browser Run (the only structured handoff protocol found)**
- Script subscribes to `Cloudflare.handoffComplete`, calls `Cloudflare.getLiveView` with `mode: "tab"` (only "tab" supports handoff) to get a `devtoolsFrontendUrl`, then `Cloudflare.handoff` with `instructions` and optional `timeout` (30-minute max; omitted = no timeout), returning `handoffId` — [Cloudflare HITL](https://developers.cloudflare.com/browser-run/features/human-in-the-loop/index.md)
- "The operator opens the Live View, completes the task, and selects Done or Failed." `handoffComplete` carries `success` and, on failure, `reason`; docs recommend asking the operator for a reason when marking Failed. `Cloudflare.getHandoffState` returns `active`, `handoffId`, `durationMs` "to avoid starting a second handoff while one is active." Live View URLs expire (default 5 min, max 1 hour) — [same](https://developers.cloudflare.com/browser-run/features/human-in-the-loop/index.md)
- Caveat: traffic "is always identified as bot traffic, so some third-party services may still block requests even when a human is in control." — [same](https://developers.cloudflare.com/browser-run/features/human-in-the-loop/index.md)

**Anchor Browser**
- `live_view_url` returned on session create; headful shows "the full chrome view, including the address bar," and "the presented tab is always the active tab"; interactive by default; read-only via `pointer-events: none;`; `one_time_url: true` makes the URL invalid "After the first viewer connects and disconnects"; `show_cursor=1` shows the remote OS pointer — [Anchor live view](https://docs.anchorbrowser.io/advanced/browser-live-view.md)
- No pause / take-over / hand-back mechanism documented on that page — [same](https://docs.anchorbrowser.io/advanced/browser-live-view.md)

**Hyperbrowser**
- `liveUrl` of the form `https://app.hyperbrowser.ai/live?token=<TOKEN>`, tokens expire after 12 hours; `viewOnlyLiveView: true` makes it read-only; "anyone holding the URL can view the session and potentially interact with it, so the URL should be treated as a secret" — [Hyperbrowser live view](https://hyperbrowser.ai/docs/sessions/live-view)

**Kernel**
- `browser_live_view_url` "humans-in-the-loop can access in real-time to resolve errors or take unscripted actions"; `?readOnly=true`; parent page can toggle read-only at runtime by posting `KERNEL_SET_READ_ONLY`; `kiosk_mode: true` hides address bar and tabs (restarts Chromium, "can take several seconds"); CLI `kernel browsers view <session-id>` — [Kernel live view](https://www.kernel.sh/docs/browsers/live-view.md), [Kernel observe](https://kernel.sh/docs/introduction/observe)
- Viewer health: gate on `KERNEL_PLAYING`; `KERNEL_CONNECTION_FAILED` / `KERNEL_CONNECTION_TIMEOUT` are terminal with a `reason`; watchdog of 60 s and bounded remounts suggested; Safari needs `.focus()` from a user gesture; CSP must allow `*.onkernel.com:8443` / `*.kernel.sh:8443` incl. wss — [Kernel live view](https://www.kernel.sh/docs/browsers/live-view.md)

**Skyvern (in-product)**
- Paused runs show "a review card with Approve and Reject buttons, and a paused status chip that matches the public run status API"; reviewers can act "directly from either run view"; a Live Browser view in Studio "no longer shows blank frames during a run, and Cmd+V paste works there on macOS"; Enterprise plan lists "human-in-the-loop" as a feature — [Skyvern changelog](https://www.skyvern.com/blog/skyvern-changelog-july-2026/), [Skyvern pricing](https://www.skyvern.com/pricing)

**Co-browsing tools (consent and control signalling)**
- Cobrowse.io: "By default, Cobrowse will show a remote control consent dialog when an agent requests remote control." Sample Web UI: title "Remote Control Request", a question whether to allow the named agent to take control, **Deny** / **Allow**; `resolve(true)` / `reject()`; admins can disable the prompt in account settings — [Cobrowse.io remote control consent](https://docs.cobrowse.io/sdk-features/customize-the-interface/remote-control-consent); separate session-consent dialog for incoming sessions — [Cobrowse.io user consent](https://docs.cobrowse.io/sdk-features/customize-the-interface/user-consent-dialog)
- Upscope viewer SDK: `requestControl` exists only "when the visitor's SDK requires a control request and control is currently off"; remote actions fail with `remote_control:inactive` until granted; action functions are `undefined` while unavailable "so their presence can be used to enable or disable UI" — [Upscope viewer SDK](https://cobrowsingapi.com/docs/rest-api/viewer-sdk); mobile SDKs have `requireControlRequest`, `controlRequestMessage`, and an in-app banner with a terminate button — [Upscope Flutter options](https://cobrowsingapi.com/docs/sdk/flutter/configuration-options)
- Surfly: leader/follower model; "Control can move between leader and follower at any point during the session" — [Surfly docs on GitHub](https://github.com/surfly/docs); in NICE CXone the agent has a "Give control" button "shown as a cursor icon" — [NICE CXone co-browse](https://help.nicecxone.com/Content/agent/cxoneagent/cobrowseincxa.htm); Bright Pattern tells agents to say they hold control "but can take over if the customer allows it" — [Bright Pattern Surfly guide](https://help.brightpattern.com/latest:Surfly-integration-guide/Configuration/AgentProcedures)
- Quiq: "When the agent selects Remote Control, a Permissions Request dialog displays in the user's Chat window." — [Quiq cobrowse](https://knowledge.quiq.com/docs/cobrowse); Zoho Assist: "The customer will see a prompt asking for permission to grant control." — [Zoho Assist](https://www.zoho.com/assist/help/cobrowse/features/request-control.html)

**RPA attended bots**
- UiPath Assistant is "an interface between the human user and the attended robot"; Form and Callout activities exist "to make attended automation more interactive" (Callout = "a screen pop-up to provide contextual guidance") — [UiPath Marketplace docs](https://docs.uipath.com/marketplace/automation-cloud/latest/user-guide/assistant-compatible-listings.md), [UiPath Agent Desktop blog](https://www.uipath.com/blog/product-and-updates/introducing-agent-desktop-for-attended-automation)
- A PeerSpot reviewer: attended robots "prevent the user from locking their screen," ruling them out for many government agencies — [PeerSpot UiPath review](https://www.peerspot.com/landing/study-uipath-platform-review-61308-by-rene-abel-christensen)

### Inferences
- The takeover surface to build: an iframe of the live browser inside the Handrail run page (Browserbase/Kernel pattern), read-only while the engine is driving (`pointer-events: none` / `readOnly`), flipped to interactive only when the escalation ladder reaches the human rung. Kernel's runtime `KERNEL_SET_READ_ONLY` message is the model for flipping without reloading.
- Copy Cloudflare's protocol almost verbatim for the UI: a banner with the engine's instructions ("Check failed at step 7: expected balance field; please get the page to the account summary"), a timer, and two buttons **Done** and **Failed (reason required)**. The handoff id, start time, duration and outcome become the journal entries; this is the only vendor that returns a typed result from the human.
- Copy co-browsing's consent and signalling: a persistent coloured border or banner stating who is in control ("You are driving" / "Engine is driving"), a visible switch of cursor ownership (Anchor `show_cursor`), and a "Hand back" button that is the human equivalent of the Cobrowse Allow/Deny dialog. Co-browsing products put the consent on the visitor; in Handrail the "visitor" is the engine, so the consent is logged, not asked.
- Log the takeover as a first-class step in the evidence chain: handoff requested (rung, reason), human joined (who, when), actions taken (screenshots at the same cadence), outcome (Done/Failed + reason), hand back, engine re-verified the check. Browser Use's follow-up-run model shows the trap: the human's actions are invisible to the run log unless you record them.
- Trap: live-view URLs are bearer tokens in every vendor (Hyperbrowser 12 h, Cloudflare 5 min default, Anchor one-time). Use short-lived, one-time URLs and never show them in the UI as copyable text.
- Trap: Cloudflare's bot-traffic caveat means the human may still be blocked; show the operator that the browser identity is unchanged.
- Trap: Browser Use bills kept-alive time; expose the pause cost/timeout in the banner and auto-fail the handoff when it expires (Cloudflare 30-min max).

### Gaps
- OpenAI ChatGPT agent / Operator "take over the browser" UX (the most-seen consumer takeover pattern) could not be fetched (403 on both openai.com and help.openai.com); not included.
- Fullview and Intercom screen-share consent/indicator UI: search budget exhausted before the query ran.
- No vendor documents an audit log format for a human takeover; the Cloudflare handoff payload is the closest.

---

## 5. Monitoring drift and reliability: flakiness, drift, success rates over time, self-healing locator UX

### Takeaway
Self-healing products expose healing as a reviewable record (mabl insights with a Find Summary confidence score; Healenium report rows with failed locator, healed locator, screenshot, score and a correct/not-correct toggle), which is the right pattern for Handrail's locator ladder and calibration table. Flakiness as a first-class view is missing even in Checkly (open feature request); Skyvern's "reliability badges" and self-heal panel are the newest attempt.

### Cited Findings
- mabl: healed steps appear on the insights page, filter by "Auto-heal", each insight opens to "the test, screenshot, and element history"; Slack/Teams notifications "when there are auto-heal insights"; to stop a step healing "add a Configure Find step and disable auto-heal"; auto-healed steps have a "Find Summary tab that outlines mabl's find confidence"; insights only created when the test passes in a plan run, otherwise just the Activity log; an "advanced auto-heal" early-access program uses generative AI — [mabl: Reviewing auto heals (search snippet; page itself returned 403)](https://help.mabl.com/hc/en-us/articles/19078598947092-Reviewing-auto-heals)
- mabl marketing: "Adaptive Multi-Layer Auto-Healing", "Human-in-the-Loop Context" where "the agent asks for the reasoning behind an action when it needs clarification", claims "up to 95%" less maintenance — [mabl auto-healing](https://www.mabl.com/auto-healing)
- Healenium report at `http://<hlm-backend>/healenium/report/` with sections "Path to healed locator", "Failed locator value", "Healed locator value", "Screenshot of healed locator on page", "Correct or not correct healing slide", "Score of the healing result" — [Healenium report docs](https://healenium.io/docs/report); architecture: proxy between client and Selenium, Postgres stores "reference selectors / healing / report" — [Healenium GitHub](https://github.com/healenium/healenium)
- Testim: "automatically create 'smart locators' for every element used in your test" — [Bloor on Testim](https://www.bloorresearch.com/?p=22614)
- Skyvern: workflows list shows "reliability badges"; run pages have "a self-heal panel listing when recovery kicked in"; "self-healing can be switched on or off" per workflow — [Skyvern changelog](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Checkly: dashboards show each check as passing/degraded/failing with availability and P95/P99 — [Checkly dashboards](https://www.checklyhq.com/product/dashboards.md); an open feedback request asks to "view a list of 'flaky' checks in the dashboard, and perhaps even alert if a Check fails a certain percentage of failures over a period of time" — [Checkly feedback](https://feedback.checklyhq.com/p/listingalerting-on-flip-flopping-checks); degraded-alert debouncing is "In Review" — [Checkly feedback](https://feedback.checklyhq.com/p/configurable-alert-debouncing-for-degraded-response-time-thresholds)
- Datadog: uptime graph per location "after retries complete"; Compare Screenshots against last good run with matching version — [Datadog](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)
- Power Automate selector drift in the wild: a dropdown broke after refresh because "the drop-down element gets a different frameID"; fix was switching the match from "equals" to "starts with" — [Power Users forum](https://powerusers.microsoft.com/t5/Power-Automate-Desktop/Extract-data-from-web-page-failed-multiple-selectors-with/m-p/2135412); a user reported "Power Automate Desktop will not let me edit the selector" — [Power Users forum](https://powerusers.microsoft.com/t5/Power-Automate-Desktop/Failed-to-get-UI-Element/m-p/855063)

### Inferences
- Copy: a "Healed targets" / "Ladder fallbacks" view listing, per step, which rung of the locator ladder matched on each run (primary -> fallback -> vision), with the screenshot and a correct/incorrect toggle (Healenium) and a confidence number (mabl Find Summary). Feed the toggle into the calibration table, which is exactly what Healenium's "correct or not correct slide" implies but does not document.
- Copy: per-capability reliability badge on the catalog list (Skyvern) computed from the last N runs, plus a drift sparkline showing how often fallback rungs fired. That is the "flaky list" Checkly users asked for and did not get.
- Trap: mabl only records a healing insight when the run passes; silent healing on passing runs is how drift accumulates unseen. Handrail should record ladder fallbacks on every run, pass or fail, and raise a "drift" state when the primary locator fails N times in a row even though the run succeeded.
- Trap: Power Automate's non-editable selector. Expose the ladder as editable text with a "test this target now" button.

### Gaps
- mabl's actual insights page layout could not be fetched (403); description is from search snippets of the help article.
- Testim's review UI and Healenium's feedback-loop behaviour (how the correct/incorrect slide changes future healing) are undocumented in the pages fetched.

---

## 6. Catalog and consumption: presenting callable automations to developers and agents; what a good "capability card" shows

### Takeaway
Composio's toolkit page (tools with input/output parameters, auth schemes, version) and Zapier's managed MCP mode (one tool per action, fields lockable, History tab of every call) are the reference. Smithery pages show the failure mode: a card with "No description", empty metadata labels and "No deployments found". Handrail's capability card should add what none show: lifecycle state, approver, verify evidence, and reliability.

### Cited Findings
- Zapier MCP agentic mode: 16 always-available meta-tools in six groups (e.g. `inspect_zapier_actions`, `discover_zapier_actions`, `enable_zapier_action`, `execute_zapier_read_action`, `execute_zapier_write_action`, `list_zapier_connections`, `get_configuration_url`, `send_feedback`); actions auto-provisioned from connected apps; `inspect_zapier_actions` returns a human-readable description per action. Managed mode: one tool per action, configured at mcp.zapier.com, "lock specific field values," agent cannot enable new actions. "Every tool call... is logged in the History tab at mcp.zapier.com." — [Zapier MCP: how tools work](https://docs.zapier.com/mcp/overview/how-tools-work.md); (the open-source page says 14 meta-tools; docs say 16 — conflicting) — [Zapier open source](https://zapier.com/opensource.md)
- Zapier scale: "9,000+ apps... 3,000+ apps with raw API access, and 30,000+ actions" — [Zapier SDK](https://zapier.com/sdk); Zapier publishes a machine-readable catalog at `/.well-known/ai-catalog.json` — [Zapier ai-catalog](https://zapier.com/.well-known/ai-catalog.json)
- Note the split of read vs write execution into separate meta-tools (`execute_zapier_read_action` / `execute_zapier_write_action`) — [Zapier MCP docs](https://docs.zapier.com/mcp/overview/how-tools-work.md)
- Composio: "Each toolkit page shows its tools (with input and output parameters) and authentication methods supported for that toolkit"; `GITHUB_CREATE_ISSUE` is a tool, `github` a toolkit; `composio.toolkits.list()` lists the catalog "independent of any session"; no-auth toolkits flagged "always available" — [Composio tools and toolkits](https://docs.composio.dev/tool-router/tools-and-toolkits), [Composio glossary](https://docs.composio.dev/resources/glossary)
- Composio dashboard sidebar: Getting Started, Playground, API Keys, Toolkits, Skills, Users, Sessions, Auth Configs, Triggers, Logs; Logs show "request, response, error, version, and Log ID" per execution; Playground tests a session with selected toolkits/tools/auth — [Composio dashboard overview](https://docs.composio.dev/kb/guide/dashboard-navigation-overview.md)
- Smithery server page observed: header nav MCPs / Skills / Docs / Pricing / Publish; card shows name, repo path, "No description", metadata labels (Overview, Repository, Homepage, Published, License, Tool Calls) with no values, "No deployments found"; a banner says Smithery's MCP Proxy and managed identity shut down on October 31 — [Smithery server page](https://smithery.ai/server/layer5-5/mcp-server-pipedrive)
- Merge's docs: "the tool list on a generic Zapier MCP server is defined by Zapier... so the list changes when Zapier changes it" — [Merge docs](https://docs.merge.dev/merge-agent-handler/connectors/generic/zapier.md)

### Inferences
- Capability card contents (copy + extend): name and one-line description (Zapier `inspect`), typed inputs and outputs with examples (Composio), auth/credential requirements (Composio), version (Composio logs carry version per call), read vs write classification (Zapier's read/write split maps onto Handrail's commit steps), and then Handrail-only: lifecycle chip, approver and date, link to the three verify runs, success rate over last N runs, last drift event, a "Try it" playground (Composio Playground) that runs in a sandbox and shows the evidence.
- Expose only `approved` capabilities over MCP (Handrail already does); mirror Zapier's managed mode: no tool to "enable" drafts from the agent side, and a History tab of every call with the run id.
- Trap: Smithery's empty cards show that an auto-generated catalog with no curation reads as abandoned; require description, example and reliability before a capability is listable.

### Gaps
- Pipedream's MCP catalog page and Postman collection pages were not fetched (search budget).
- Composio's live "All Toolkits" browse URL not confirmed.

---

## 7. Pricing and onboarding: free tier, self-serve vs demo-gated

### Takeaway
Infrastructure vendors are self-serve with a small free tier (Browserbase Free: 3 concurrent browsers, 1 browser hour; Browser Use: $1 free credit, pay-as-you-go, "No subscription plans are offered"); agent-workflow vendors gate the human-in-the-loop feature behind Enterprise (Skyvern lists "human-in-the-loop" only on the custom-priced tier, with a 14-day trial instead of a free plan). Pricing units differ (browser hours vs credits vs tokens+20%), and credit pages tend not to define what a credit buys.

### Cited Findings
- Browserbase: Free $0 (3 concurrent, 1 browser hour, 3 Agent runs, 1,000 Search/Fetch calls, 15 min/session, $5 in model tokens, no captcha solving); Developer $20/mo (25 concurrent, 100 hours then $0.12/hr, 1 GB proxy); Startup $99/mo "MOST POPULAR" (100 concurrent, 500 hours then $0.10/hr, 5 GB proxy); Scale custom, contact sales, 250+ concurrent, HIPAA BAA, SSO. Page: four cards, compare table, "A browser hour goes further than you think", testimonials, ~8-question FAQ — [Browserbase pricing](https://www.browserbase.com/pricing)
- Browser Use: "Pay as you go. No subscription. Credits never expire." $5 minimum top-up; cloud browsers $0.02/hour; web agents = model cost +20% plus browser time; bring-your-own-key charged at 20% of published token rates; "$1 free credit" for Google/GitHub/Microsoft signups, no card; concurrency scales with total paid (10 at $0, 50 at $100, 250 at $1,000, 500 at $5,000, 1,000 at $25,000); "No subscription plans are offered" (legacy subscribers managed separately); on-prem = talk to sales; trust badges SOC 2 Type II, HIPAA; a model quality-vs-price chart on the pricing page — [Browser Use pricing](https://browser-use.com/pricing)
- Skyvern: Hobby $29/mo (30,000 credits, 10 concurrent, ~1,200 actions), Pro $149/mo (150,000 credits, 25 concurrent, ~6,200 actions, team workspaces, 2FA/TOTP, 1Password), Enterprise custom (100 concurrent, HIPAA, SOC-2 report, custom code blocks, "human-in-the-loop"); "Every self-serve plan starts with a 14-day free trial: 30,000 credits with Hobby limits"; no permanent free plan; "Book a Demo" in nav; FAQ "What counts as a run or credit?" has a heading with no captured answer — [Skyvern pricing](https://www.skyvern.com/pricing)
- Zapier Human in the Loop "is listed as a premium app, and a paid Zapier account is a prerequisite" — [Zapier HITL help](https://ob-zapier.helpjuice.com/get-more-control-over-your-workflows-with-human-in-the-loop)
- Autotab: "$1 per hour... only pay for the time the AI agent actively spends working" (third-party listing) — [VideoSDK](https://www.videosdk.live/ai-apps/autotab)
- TinyFish advertises 500 free credits; third-party says plans from $29/mo — [devtoollab](https://devtoollab.com/ai-tools/tinyfish)
- Axiom tiers and Bardeen from $10/mo as above — [theaiagentindex](https://theaiagentindex.com/compare/axiom-ai-vs-bardeen), [makerstack](https://makerstack.co/reviews/bardeen-review/)
- HN on Skyvern cost: dtnewman called it "pretty pricey" and asked for "a cap on calls or tokens, ideally a dollar limit"; founder cited "between 5 cents and 20 cents per page" — [Show HN: Skyvern](https://news.ycombinator.com/item?id=39706004)

### Inferences
- Handrail's economics invert the market: authoring costs model tokens once; replay costs nothing in tokens. Price the authoring run and escalations (classifier/model/human minutes) and make replay flat or free; show on the run page that `llm_calls = 0` (rule 4) as a visible cost line, which no competitor can show.
- Do not gate human-in-the-loop behind Enterprise (Skyvern); it is the core loop, not an add-on. Do copy Browserbase's "Free with hard caps and no captcha" and Browser Use's "no card, $1 credit" onboarding.
- Define the unit on the pricing page (Skyvern's unanswered "What counts as a credit?" is a trap); Handrail's natural units are "authoring runs", "replays" and "escalation minutes".

### Gaps
- UiPath, Automation Anywhere, Power Automate, Bardeen, Magical, Axiom, Browse AI official pricing pages were not fetched; figures above are from third-party listings.

---

## 8. Known UX failures: what users complain about (too complex, black box, can't tell why it broke, no way to stop a bot mid-run)

### Takeaway
The recurring complaints are vague errors with no path to the cause (Automation Anywhere reviews), selectors that break for invisible reasons and cannot be edited (Power Automate forums), runaway cost with no stop or dollar cap (Skyvern HN), and distrust of per-page LLM decisions when users wanted the clicks worked out once and then exported as deterministic code (Skyvern HN). The last point is Handrail's thesis stated by users.

### Cited Findings
- Automation Anywhere (G2-syndicated/PeerSpot/Gartner): "the errors that automation makes available, when a bot gives an error, are very vague and don't help, most of the time, to solve the problem itself"; "debugging mode is poorly functional... variables don't store values of current debug run"; "User cannot put breakpoints at runtime. Cannot debug into Subtasks."; May 2026 Gartner review: "debugging and error handling is time consuming task" — [AWS Marketplace reviews (G2-sourced)](https://aws.amazon.com/marketplace/reviews/reviews-list/B085L5P311?page=246), [PeerSpot pros and cons](https://peerspot.com/products/automation-anywhere-pros-and-cons), [Gartner reviews](https://www.gartner.com/reviews/market/robotic-process-automation/vendor/automation-anywhere)
- UiPath (PeerSpot): UX "intuitive" but debugging "needs work"; monitoring needs improvement; attended robots stop users locking their screen — [PeerSpot UiPath](https://peerspot.com/landing/study-uipath-review-126962-by-suraj-deoram-agarkar), [PeerSpot UiPath](https://www.peerspot.com/landing/study-uipath-platform-review-61308-by-rene-abel-christensen)
- Power Automate Desktop: selector breaks on dynamic iframe id; "Power Automate Desktop will not let me edit the selector"; a vendor blog frames it as "Every captured element is a bet that those attributes hold still" (Supergood.ai, Aug 2026, vendor opinion) — [Power Users forum](https://powerusers.microsoft.com/t5/Power-Automate-Desktop/Extract-data-from-web-page-failed-multiple-selectors-with/m-p/2135412), [Power Users forum](https://powerusers.microsoft.com/t5/Power-Automate-Desktop/Failed-to-get-UI-Element/m-p/855063), [Supergood blog](https://supergood.ai/blog/power-automate-desktop-keeps-breaking)
- Skyvern Show HN (2024): bravura "objected to running vision and LLMs on every page, wanting them used only to work out the clicks once"; pmontra proposed "the AI compiles a traditional scraper that is regenerated when the UI changes"; epr argued users "wanted exportable automation code, not an internal cache"; croes: "Good luck debugging any errors"; Kerbonut asked if it is worth $1 if it gets "10% of the information wrong every time"; barfbagginus flagged LLM-driven password reset as "uniquely vulnerable to attack"; founders replied they would "replay stored actions and use LLMs less often" and "only use LLMs when there's a problem"; the only stop control cited was a "max steps" setting — [Show HN: Skyvern](https://news.ycombinator.com/item?id=39706004)
- Libretto's HN post (54 points) positioned "deterministic" AI browser automations as the selling point — [PromptZone on Libretto](https://www.promptzone.com/arlo_suzuki/libretto-makes-ai-browser-automations-deterministic-1981.md)
- Bardeen G2: extension "max[ed] out my computer" — [G2 Bardeen](https://g2.com/products/bardeen/reviews)
- Cloudflare: even with a human in control, traffic "is always identified as bot traffic" — [Cloudflare HITL](https://developers.cloudflare.com/browser-run/features/human-in-the-loop/index.md)
- Datadog warns its own AI summary is "a starting point for investigation, not as authoritative root cause analysis" — [Datadog](https://docs.datadoghq.com/synthetics/browser_tests/test_results/)

### Inferences
- Traps to avoid, each with the product that fell into it: vague error text with no link to the failing step and screenshot (Automation Anywhere); un-editable or hidden locators (Power Automate); no spend/step cap and no visible Stop (Skyvern 2024; its 2026 taxonomy now has `canceled: Stopped by you`); AI explanations presented as authoritative (Datadog explicitly disclaims); human-in-the-loop sold as an enterprise upsell (Skyvern pricing); recording UI that looks finished but needs cleanup the docs admit is usual (Power Automate's "most recorded tasks should be modified").
- Copy: a big always-visible **Stop** on every running run, a per-run budget (steps and escalation minutes), and an "export" affordance for the compiled capability so users feel they own deterministic code (the epr complaint).
- Handrail's rule 6 (never a bare exception; always a typed RunResult) directly answers the "vague error" complaint; the UI should print the typed result, the failing check, and the step card together.

### Gaps
- Reddit-sourced complaints for UiPath/Power Automate/Zapier/Make and the Browser Use HN launch thread could not be retrieved (search budget exhausted before those queries; one Reddit query returned only Microsoft forum hits).
- No source found quoting users on "no way to stop a bot mid-run" beyond the Skyvern HN step-cap exchange.

---

## 9. Summary: patterns to copy and traps to avoid (cross-stage)

### Takeaway
Build each Handrail stage from the best existing primitive, and add the three things nobody ships: commit marking during authoring, a lifecycle + named approver on the artifact, and a typed, journalled human handoff.

### Cited Findings
(All items above; condensed here with the source product for each.)
- Authoring rail with one card per action, screenshot, editable target+anchor, delete, pause — UiPath App/Web Recorder [docs](https://docs.uipath.com/activities/other/latest/ui-automation/app-web-recorder.md); Power Automate "Wait for action" overlay [docs](https://learn.microsoft.com/en-us/power-automate/desktop-flows/recording-flow); Skyvern red recording indicator + live draft panel [changelog](https://www.skyvern.com/blog/skyvern-changelog-july-2026/)
- Artifact diff: step colours + field drill-down — Workato [docs](https://docs.workato.com/recipe-development-lifecycle/compare-versions-with-recipe-diff)
- Run page: per-step card + before/action/after + red error marker + termination reason — Datadog [docs](https://docs.datadoghq.com/synthetics/browser_tests/test_results/), Playwright [docs](https://playwright.dev/docs/trace-viewer), Browserbase [docs](https://docs.browserbase.com/features/session-inspector)
- Result taxonomy with `paused`, `terminated`, `canceled` distinct from `failed` — Skyvern [concepts](https://www.skyvern.com/docs/concepts.md)
- Handoff protocol: instructions, timeout, Done/Failed+reason, completion event, single-active-handoff guard — Cloudflare [docs](https://developers.cloudflare.com/browser-run/features/human-in-the-loop/index.md)
- Live view embed, read-only toggle at runtime, one-time URL, cursor ownership — Kernel [docs](https://www.kernel.sh/docs/browsers/live-view.md), Anchor [docs](https://docs.anchorbrowser.io/advanced/browser-live-view.md), Browserbase [docs](https://docs.browserbase.com/platform/browser/observability/session-live-view)
- Control consent dialog and "Give control" cursor button — Cobrowse.io [docs](https://docs.cobrowse.io/sdk-features/customize-the-interface/remote-control-consent), NICE/Surfly [docs](https://help.nicecxone.com/Content/agent/cxoneagent/cobrowseincxa.htm)
- Healing review rows with score and correct/incorrect feedback — Healenium [docs](https://healenium.io/docs/report), mabl [help](https://help.mabl.com/hc/en-us/articles/19078598947092-Reviewing-auto-heals)
- Catalog card with typed params, auth, version, read/write split, call history — Composio [docs](https://docs.composio.dev/tool-router/tools-and-toolkits), Zapier MCP [docs](https://docs.zapier.com/mcp/overview/how-tools-work.md)
- Free tier with hard caps, no card — Browserbase [pricing](https://www.browserbase.com/pricing), Browser Use [pricing](https://browser-use.com/pricing)

### Inferences
- Traps: vague errors (Automation Anywhere), hidden/uneditable selectors (Power Automate), no stop/cap (Skyvern 2024 HN), HITL as enterprise upsell (Skyvern pricing), empty auto-generated catalog cards (Smithery), bearer live-view URLs shown to users (all browser vendors), silent healing on passing runs (mabl), AI root cause presented without the disclaimer Datadog itself adds, and deprecating the model-watches-you recorder after shipping it (Microsoft).

### Gaps
- OpenAI/Operator takeover UX, Fullview/Intercom, Testim, Browse AI/Magical/Induced screens, Pipedream/Postman catalog pages, Reddit threads and the Browser Use HN thread remain unverified for the reasons stated above.
