# Practitioner pain points: automating legacy software with no API (2023–2026)

Scope note on sources. The assignment asked for Reddit first. In this session reddit.com was
unreachable on every channel: the search backend reports the domain blocks its crawler
(`site:reddit.com` and `allowed_domains` both refused), direct fetches of old.reddit.com and
www.reddit.com were refused, a curl fallback was denied by policy, and the Chrome extension
refused reddit.com as a restricted site. The shared web-search budget was then exhausted. So
this catalogue is built from the next-best practitioner forums that were reachable: Hacker News
(read thread by thread, with the Algolia index used to pin dates and comment IDs), the UiPath
Community Forum, and one measured benchmark (reflex.dev). Every quote below is verbatim, with
username, venue, date and URL. Reddit, Dentaltown, Spiceworks, CU forums and r/CreditUnion
remain unmined; see the Gaps under each question. A follow-up pass with Reddit access (or a
human pasting threads) would fill the two industries where HN was thin: credit unions and dental.

Index of industries covered with at least one first-hand quote: healthcare clinics / EHR /
medical billing / prior auth; pharmacy (Australia); accounting and tax (QuickBooks Desktop,
Cantax); banking (CICS mainframe); hospitality (hotel PMS); manufacturing (ERP, Oracle EBS);
auto dealerships (CDK / Reynolds DMS); property management (AppFolio, Yardi, MRI); freight
brokerage; government tax filing (IRS); govtech and insurance tech portals; parts procurement.

Handrail fit, in one line each, is given in the Inferences of questions 1 and 3.

---

## Q1. What do practitioners complain about when they say "no API", "screen scraping", "swivel chair", "copy paste between systems", "bot breaks when the UI changes", "we hired offshore to do data entry"?

### Takeaway
The complaints cluster into five themes that recur across industries: (a) the software they must
use will never have an API and the vendor has no incentive to add one; (b) humans spend hours a
day re-keying the same data between two screens; (c) RPA built on selectors breaks on every
update and most of the engineering effort goes into exceptions, not the happy path; (d) enterprise
RPA licensing runs to tens of thousands of dollars a month; (e) the fallback is offshore labour
with full remote access to the system. Practitioners' own words are below, grouped by theme.

### Cited Findings

#### Theme A: "No API, and there never will be"

- danielbln, HN, 2024-10-25 (general): "There is plenty of legacy software out there that has no and will never have a nice API to integrate with." — [HN 41946118 thread](https://news.ycombinator.com/item?id=41946118)
- alpha_squared, HN, 2024-10-25 (slow-to-change industries): "There are no APIs and no access to underlying databases, just user-focused point-and-click." — [HN 41946118 thread](https://news.ycombinator.com/item?id=41946118)
- solidasparagus, HN, 2025-01-14: "...most actually useful software built for humans doesn't have a good programmatic API." — [HN 42670619 thread](https://news.ycombinator.com/item?id=42670619)
- jackvalentine, HN, 2025-01-14 (line-of-business apps): "LOB apps often don’t have a useful API" and "RPA bridged the gap a bit for us." — [HN 42670619 thread](https://news.ycombinator.com/item?id=42670619)
- rootcage, HN, 2026-05-05 (hotel property-management systems): "These companies can barely keep the product alive, they definitely aren't incentivized to maintain an API." — [HN 48025952](https://news.ycombinator.com/item?id=48025952)
- LASR, HN, 2024-10-22 (a doctor's custom Windows practice software; Cantax, Canadian tax prep): "pretty much most of the real world runs on software that directly interfaces with people" and, on having assumed API integrations would be enough, "Boy was I wrong." — [HN 41917568](https://news.ycombinator.com/item?id=41917568)
- halfcat, HN, 2024-10-23 (QuickBooks Desktop, accounting): "Intuit forces you into using their API, which is XML-based and ranges from slow to timing out." — [HN 41920748](https://news.ycombinator.com/item?id=41920748); same user, same thread: "Being "on the network" doesn't mean there's an accessible API." and "you can count on at least one database corruption every year or two" — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- enraged_camel, HN, 2023-05-21 (QuickBooks Desktop): "One huge problem with Quickbooks Desktop is that it's hugely expensive to integrate it with anything" — [HN 36025724](https://news.ycombinator.com/item?id=36025724)
- brabel, HN, 2024-10 (pharmacy software, Australia): "the DB is encrypted and they provide no way to access it." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- kole78 (Propify founder), HN, 2023-03-15 (property management: Yardi, AppFolio, MRI, ResMan): "not much has changed with these APIs since 2012... or since 1999 for that matter." and "we only support integrations for customers who have officially sanctioned relationships with each PMS" — [HN 35171944](https://news.ycombinator.com/item?id=35171944)
- ayanb9440, HN, 2024-09 (hospitals and banks): "Lots of hospitals and banks use RPA to automate routine processes on their EHRs and systems of record" ... "because these kinds of software typically don't have APIs available." ... "Or if they do, they're very limited." — [HN 41567387 thread](https://news.ycombinator.com/item?id=41567387)
- nradov, HN, 2025-05-14 (Epic, EHR): "The strong vendor lock-in is unavoidable given how deeply an EHR gets embedded into any provider organization." — [HN 43988357](https://news.ycombinator.com/item?id=43988357); same user, 2025-05-22, on Epic: "Their culture is more that they know the correct way to do things and customers should change" — [HN 44065109](https://news.ycombinator.com/item?id=44065109)
- SoftTalker, HN, 2025-11-25 (banking fintech breach): "Their web app is "screen scraping" a legacy mainframe CICS interface via a virtual 3270 terminal." — [HN 46050990](https://news.ycombinator.com/item?id=46050990)
- mediaman, HN, 2026-05-26 (manufacturing firms on legacy ERP): "They want to wrap it in AI to automate stuff without changing out the core system." — [HN 48284582](https://news.ycombinator.com/item?id=48284582); same thread: "they hate their legacy systems but can't really do anything about it" and "ERP changes are an extreme nightmare" — [HN 48280729 thread](https://news.ycombinator.com/item?id=48280729)
- araes, HN, 2024-06-25 (dealership DMS during the CDK outage): "you can't migrate away. No system to import into DT or R&R or whatever from" — [HN 40791697](https://news.ycombinator.com/item?id=40791697)
- jasomill, HN, 2026-05-06 (unnamed Windows desktop app that hid grid data from accessibility APIs): "all functions that allowed data to be exported were protected by CAPTCHAs." and "I had to resort to a combination of OCR, simulated user input, and print capture to drive the application" — [HN 48032043](https://news.ycombinator.com/item?id=48032043)
- bonoboTP, HN, 2026-10-04 (general admin office work): "The vast majority of software in such applications is legacy stuff or proprietary" / "The only way to interact with it is via GUI." — [HN 49953299](https://news.ycombinator.com/item?id=49953299)
- nkov47 (Coasty founder, relaying customer pain), HN, 2026-07-15: "Many of these applications have no API, incomplete APIs, or integrations that take months to build." — [HN 48922706](https://news.ycombinator.com/item?id=48922706)
- fkilaiwi (Intuned founder), HN, 2026-06-08: "Customers primarily use the Intuned AI agent to automate websites that don't expose APIs." ; co-founder ahmadilaiwi on which verticals: "the main ones being: govtech and insurance tech." — [HN 48445171](https://news.ycombinator.com/item?id=48445171)

#### Theme B: Swivel chair, re-keying, fax, spreadsheets

- rootusrootus, HN, 2026-06-09 (office/middle-management work): "Nope, just people who basically swivel chair information from one place to another." — [HN 48468104](https://news.ycombinator.com/item?id=48468104)
- whalesalad, HN, 2023-10-17 (tax filing, IRS pilot) labels the manual step a "Swivel chair handoff" and adds "Most systems will allow you to export data in a columnar CSV format." — [HN 37922804](https://news.ycombinator.com/item?id=37922804)
- bonoboTP, HN, 2026-10-04 describing what admin staff do all day: "Essentially copying information between textboxes, slightly rephrasing, clicking buttons, formulating emails" — [HN 49953299](https://news.ycombinator.com/item?id=49953299)
- arcb (BitBoard founder, relaying clinic customers), HN, 2025-06-10: "Their MAs were spending 15 to 20 minutes per patient just entering intake form data into the EHR." ; "relied on thousands of remote contractors to do repetitive administrative work" ; "have a legacy portal and operate on spreadsheets / paper" ; "Many legacy ERPs don't run in the browser and we have to meet them there." — [HN 44237769](https://news.ycombinator.com/item?id=44237769)
- Mashimo, HN, 2025-06 (same thread): "the staff builds a spreadsheet, and then enter it into other software." — [HN 44237769](https://news.ycombinator.com/item?id=44237769)
- ansong99 (Cenote founder, relaying clinic customers), HN, 2025-03-06: "Many clinics still rely on faxed (!) referrals, and even well-funded practices use obsolete workflows." and "It’s a manual back-and-forth process that is time-consuming, prone to errors, and slows down patient care." — [HN 43280836](https://news.ycombinator.com/item?id=43280836)
- grepfru_it, HN, 2024-01-07 (small-business accounting): "Every month I would spend 8-16 hours updating bills manually." — [HN 38905061](https://news.ycombinator.com/item?id=38905061)
- suchintan (Skyvern founder, relaying customers), HN, 2025-01-17 (parts ordering across tens of vendor websites, e.g. finditparts.com): "have people (usually the CEO) spending a few hours a week doing it manually" — [HN 42742518](https://news.ycombinator.com/item?id=42742518)
- pasttense01, HN, 2023-10-20 (freight brokerage): "brokers who handle issues between shippers and carriers manually (on the phone constantly)" — [HN 37951064](https://news.ycombinator.com/item?id=37951064)
- const_cast, HN, 2025-06-04 (clinic staff): "most of their job is handling records, contacting insurance, prior auth" — [HN 44185847](https://news.ycombinator.com/item?id=44185847)
- halfcat, HN, 2024-08-11 (medical billing on an AS400 green screen): "The employees work by keyboard shortcuts and are extremely efficient" — [HN 41218553](https://news.ycombinator.com/item?id=41218553)
- araes, HN, 2024-06-21, relaying a Reddit user during the CDK outage (second-hand): "Excel spreadsheets and post it notes for any parts we're handing out." — [HN 40751755](https://news.ycombinator.com/item?id=40751755)

#### Theme C: "The bot breaks every time the UI changes"; exceptions eat the effort

- DebtDeflation, HN, 2024-10-23 (legacy enterprise systems via RPA): "it is absolutely awful, incredibly brittle, and unmaintainable once you get past a certain level of complexity." and "Even when it works, performance at scale is terrible." — [HN 41926346](https://news.ycombinator.com/item?id=41926346)
- eastendguy, HN, 2024-10-23 (Ui.vision for business tasks): "90% of the work goes into error and edge case handling" ; "Current RPA tools like Uipath or ui.vision need explicit programming for every potential situation." ; "A human can work around all these error cases once she encounters them." — [HN 41923181](https://news.ycombinator.com/item?id=41923181)
- visarga, HN, 2024-10: "Most RPA work is in dealing with errors and exceptions, not the "happy path"." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- claytongulick, HN, 2024-10 (healthcare RPA projects): "they're always brittle and sensitive to minor updates" and "if we do end up using it, we'll have solid guard rails in place" — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- CSMastermind, HN, 2024-10 (RPA frameworks): "It's almost always a framework around existing tools like Selenium that you constantly have to fight against" — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- ravindra.reddy33, UiPath Community Forum, 2026-04-23 (one app, 20 automations): "Suddenly, multiple processes start failing." ; "So even a small change becomes a big maintenance effort" ; "you end up duplicating the same logic across them, and any change means touching several places." — [UiPath Forum 5741088](https://forum.uipath.com/t/one-app-20-automations-ui-change-breaks-everything-how-are-you-handling-this/5741088)
- himanshu.chopra, UiPath Forum, 2026-04: "if you don't centralize, you spend more time fixing bots than building them." and "The biggest challenge isn’t fixing the code; it’s updating the 20 processes without breaking them all at once." — [UiPath Forum 5741088](https://forum.uipath.com/t/one-app-20-automations-ui-change-breaks-everything-how-are-you-handling-this/5741088)
- Jeroen_van_Loon, UiPath Forum, 2026-04: "So accepting that fact, it is all about making it a planned activity instead of disaster recovery." — [UiPath Forum 5741088](https://forum.uipath.com/t/one-app-20-automations-ui-change-breaks-everything-how-are-you-handling-this/5741088)
- Satish Yadav, UiPath Community Forum, 2025-12-16: "selectors behave differently every time the app reloads." ; "Attributes keep changing, anchors don't always resolve, and wildcarding makes it unstable." ; "What's the correct way to build selectors that actually survive real production changes instead of breaking every few days?" — [UiPath Forum 5699124](https://forum.uipath.com/t/selectors-breaking-after-every-application-reload-how-to-build-production-stable-selectors-in-uipath-studio/5699124)
- fchishtie (Minicor founder, on Windows desktop RPAs at scale), HN, 2026-05-26: "30%+ failure rates are not uncommon." ; "At scale we’ve seen cases of failed RPAs leading to thousands of support tickets a month." ; "the pattern we've seen with RPAs is you can catch maybe 80% of the edge cases in the first week" ; "lots and lots of webhooks when things break" — [HN 48280729](https://news.ycombinator.com/item?id=48280729)
- sidgarimella, HN, 2025-01: "I’ve worked on a few projects in RPA prior and I’m losing faith in selectors." — [HN 42565821 thread](https://news.ycombinator.com/item?id=42565821)
- YaBa, HN, 2025-01: "I had a scrapper working, website changed, had to re-do the scrapper again" — [HN 42565821 thread](https://news.ycombinator.com/item?id=42565821)
- dataviz1000, HN, 2024-09: "The biggest issue with automating 3rd party websites is knowing when the 3rd party developer pushes changes" — [HN 41567387 thread](https://news.ycombinator.com/item?id=41567387)
- bnyhil31-afk, HN, 2026-05: "if RPA has taught me anything, it's 'don't rely on the UI'." — [HN 48029573](https://news.ycombinator.com/item?id=48029573)
- fkilaiwi (Intuned), HN, 2026-06-08: "Websites change, selectors break, and failures can be painful to reproduce and fix." and "the actual hard problem in browser automation is maintenance." — [HN 48445171](https://news.ycombinator.com/item?id=48445171)
- hamasho, HN, 2026-05-06 (hand-written Playwright "skills" for recurring tasks): "It's also error-prone because web sites often tweak the UI and scripts can stop working." — [HN 48031468](https://news.ycombinator.com/item?id=48031468)
- nkov47 (Coasty), HN, 2026-07-15: "it often breaks when a button moves, a pop-up appears" and "Getting an agent to complete a task once is fairly straightforward." — [HN 48922706](https://news.ycombinator.com/item?id=48922706)
- Vendor-estimated (not practitioner) maintenance figures, supergood.ai, 2026-08-19: enterprise portals redesign "1 to 3 times a year"; each selector-drift break costs "4 to 16 developer-hours"; FAQ puts ongoing RPA maintenance at "50+ developer-hours per year per portal integration" — [supergood.ai blog](https://supergood.ai/blog/rpa-bot-keeps-breaking-enterprise-portals) (vendor sells the alternative; treat as a marketing estimate)

#### Theme D: Offshore / VA / contractors as the current "automation"

- jasomill, HN, 2026-05-06, on the manual process his OCR hack replaced: "giving cheap offshore labor full read-only remote access to all data in the system" — [HN 48032043](https://news.ycombinator.com/item?id=48032043)
- arcb (BitBoard), HN, 2025-06-10, on a prior healthcare employer: "relied on thousands of remote contractors to do repetitive administrative work" and "Our software solutions were always too brittle, never managing to handle the variance of clinical data we oversaw." — [HN 44237769](https://news.ycombinator.com/item?id=44237769)
- nradov, HN, 2026-08-20 (medical transcription review): "A lot of those workers are offshore in India and Philippines." — [HN 49370594](https://news.ycombinator.com/item?id=49370594)
- deaux, HN, 2025-10-16 (a large traditional company replacing contractors with LLMs): "these were cheap offshore contracting jobs being replaced" — [HN 45603350](https://news.ycombinator.com/item?id=45603350)

#### Theme E: Fear of unattended mistakes; the need for a human and a record

- stavros, HN, 2024-10-22 (medical software, technical director): "We have humans double-check everything, because we're required by law to." — [HN 41920002](https://news.ycombinator.com/item?id=41920002)
- trollbridge, HN, 2025-03-07 (clinic back office): "this will be used to replace back office staff and serious mistakes will get made" and "Back office workers are skilled workers who often know how to do things like navigate an insurer" — [HN 43280836 thread](https://news.ycombinator.com/item?id=43280836)
- candiddevmike, HN, 2025-06 (AI agents entering EHR data): "that's medical malpractice territory." and "If you have an API, why are you using browser agents?" — [HN 44237769 thread](https://news.ycombinator.com/item?id=44237769)
- throw03172019, HN, 2026-05 (desktop agents in practices): "this can touch a lot of PHI" and "Most practices are not tech savvy." — [HN 48280729 thread](https://news.ycombinator.com/item?id=48280729)
- smcleod, HN, 2024-10 (enterprise customers): "90% of our customers do not allow this due to data sovereignty." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- rkagerer, HN, 2025-08-14 (on a cloud-hosted desktop-automation vendor): "Personally I think this approach is flawed because it runs in the cloud." and "I don't want to be paying per-action, per-month, per-token, etc." — [HN 44901528 thread](https://news.ycombinator.com/item?id=44901528)
- xenospn, HN, 2025-03 (selling to clinics): "It is so incredibly hard to get established, small businesses to do anything regarding IT or tech." — [HN 43280836 thread](https://news.ycombinator.com/item?id=43280836)

### Inferences
- The vocabulary practitioners actually use is "no API / will never have an API", "brittle", "selectors break", "edge cases", "exceptions", "swivel chair", "spreadsheet then re-enter", "fax", "offshore contractors". "RPA" is used as a slightly embarrassed word for "we drive the GUI because we have to".
- The complaint is rarely "I cannot automate it once". It is "it broke again after the update and now twenty processes are down" and "90% of the work is the exception path". That is the gap between a one-off run and a hundred runs, which is the bet Handrail is built on.
- Handrail fit, by theme:
  - A (no API): answered. Handrail drives the UI by design and does not wait for a vendor API.
  - B (swivel chair): answered for recurring, well-defined re-keying; the compiled capability is exactly a typed version of "take these fields from screen 1 and put them in screen 2".
  - C (breaks on UI change): partly answered. Deterministic replay removes model nondeterminism, and the classifier -> bounded model -> human ladder is a built-in answer to "unknown screen". Not answered: the UiPath forum's real pain is fleet maintenance across 20 processes sharing one app; Handrail would need a shared per-application screen library or the same duplication appears.
  - D (offshore labour with full access): answered. A compiled capability runs with scoped credentials and masks secrets at the boundary; no contractor has read-only access to everything.
  - E (fear of unattended mistakes): strongly answered. Named-human approval on irreversible steps, hash-chained evidence per run, and a human who can take over the same browser are each a direct response to a quote above (stavros, trollbridge, candiddevmike).
  - Not answered by design: data-sovereignty and "must run on-prem" objections (smcleod, rkagerer) are deployment questions; the notes do not establish where Handrail runs.

### Gaps
- No Reddit quotes at all (see scope note). The subreddits named in the brief (r/rpa, r/UiPath, r/sysadmin, r/smallbusiness, r/accounting, r/healthIT, r/CreditUnion, r/dentistry, r/pharmacy, r/propertymanagement, r/logistics) are unmined.
- No first-hand credit-union (Symitar/Episys, Jack Henry, Fiserv) complaint was found; HN's index returns nothing for those names in 2023–2026. Vendor material notes SymXchange exists as an interface, which may mean the pain there is access and cost rather than absence of an API, but no practitioner said so.
- No first-hand dental practitioner quote (Dentrix, Eaglesoft, Open Dental) was found; only vendor pages claiming 12–45 minutes per patient for manual insurance verification.
- No first-hand logistics quote beyond the Convoy thread; no court e-filing or state-portal quote; no SAP GUI or Citrix-published-app quote from 2023 onward.
- Capterra AppFolio review pages (where a reviewer reportedly says AppFolio "don't allow API interactions") returned HTTP 403 and could not be verified.

---

## Q2. Which legacy applications get named most?

### Takeaway
In the reachable sources the most-named systems are EHRs (Epic by far, then Athena, Cerner,
OpenDental, eClinicalWorks only via vendors), QuickBooks Desktop, SAP/ERP (SAP ECC, Oracle EBS),
dealership DMSs (CDK, Reynolds & Reynolds, DealerTrack), property-management systems (Yardi,
AppFolio, MRI, Entrata, Buildium), hotel PMSs, AS/400 and 3270/CICS green screens, and Canadian
tax software (Cantax). Payer portals are named generically, not by brand.

### Cited Findings
- Epic / EHRs: nradov on Epic lock-in and in-house culture — [HN 43988357](https://news.ycombinator.com/item?id=43988357), [HN 44065109](https://news.ycombinator.com/item?id=44065109); dgoncharov (Metriport founder, promotional): "the only way to get data into EHRs is by writing one-off integrations with a specific hospital IT system" — [HN 40459153](https://news.ycombinator.com/item?id=40459153); arcb: "Amongst EHRs we currently work with Athena" — [HN 44237769](https://news.ycombinator.com/item?id=44237769); ansong99: "integrating with larger EHRs is notoriously labor-intensive, so for now, we’re prioritizing more accessible clinics." — [HN 43280836](https://news.ycombinator.com/item?id=43280836); throw03172019 names OpenDental and EMR/practice-management systems as desktop targets — [HN 44901528 thread](https://news.ycombinator.com/item?id=44901528); 0xWTF: "Akasa gets a seat license for each medical system they service" (medical billing RPA) — [HN 48024859 thread](https://news.ycombinator.com/item?id=48024859)
- QuickBooks Desktop: halfcat [HN 41920748](https://news.ycombinator.com/item?id=41920748); enraged_camel [HN 36025724](https://news.ycombinator.com/item?id=36025724); trollbridge, 2025-10-07: "QuickBooks Desktop only exists in an Enterprise edition anymore (which is expensive)" — [HN 45499247](https://news.ycombinator.com/item?id=45499247); glancast, 2025-06-30, building a "JSON API to integrate with QuickBooks Enterprise / QuickBooks Desktop" as a workaround — [HN 44423668](https://news.ycombinator.com/item?id=44423668)
- SAP / ERP: bayesnet, 2025-10-01: "The only tool I had available was the SAP GUI input emulation API for VBA." — [HN 45439894](https://news.ycombinator.com/item?id=45439894); sixdimensional, 2025-08-05, on a manufacturer on Oracle EBS: "they were trying to implement UIPath" — [HN 44798744](https://news.ycombinator.com/item?id=44798744); UiPath forum replies use SAP ECC and Salesforce as the "one app, 20 automations" examples — [UiPath Forum 5741088](https://forum.uipath.com/t/one-app-20-automations-ui-change-breaks-everything-how-are-you-handling-this/5741088); mediaman on manufacturing ERPs — [HN 48284582](https://news.ycombinator.com/item?id=48284582)
- Dealership DMS: WarOnPrivacy, 2024-06-24: "US dealerships are dominated by UCS(Reynolds&Reynolds) and CDK." — [HN 40777633](https://news.ycombinator.com/item?id=40777633); araes on no migration path from CDK — [HN 40791697](https://news.ycombinator.com/item?id=40791697); shagie, 2024-06-24, on the manual fallback: "Pen and paper, but please no cursive" — [HN 40777665](https://news.ycombinator.com/item?id=40777665)
- Property management: kole78 (Propify) naming Yardi, AppFolio, MRI, ResMan, Entrata — [HN 35171944](https://news.ycombinator.com/item?id=35171944), [HN 35173814](https://news.ycombinator.com/item?id=35173814); akouri, 2026-04-14: "Appfolio, TurboTenant, Innago, etc. are just an extra chore, they don't actually help you do the work." — [HN 47760241](https://news.ycombinator.com/item?id=47760241); taylorhou, 2026-06-03, an outsourced accounting firm "specializing in property management (appfolio, buildium, rentvine)" — [HN 48385726](https://news.ycombinator.com/item?id=48385726)
- Hotel PMS: rootcage — [HN 48025952](https://news.ycombinator.com/item?id=48025952)
- Green screens / mainframe: SoftTalker (CICS via 3270) — [HN 46050990](https://news.ycombinator.com/item?id=46050990); halfcat (AS400 medical billing) — [HN 41218553](https://news.ycombinator.com/item?id=41218553); avgDev, 2023-03-03: "Company I work for still uses AS400, which has been released in 1988 just after I was born." — [HN 35011810](https://news.ycombinator.com/item?id=35011810); uticus, 2023-11-21: "Green screen allowed 99% of things to get done faster with 1000% less fuss." — [HN 38366520](https://news.ycombinator.com/item?id=38366520); lobochrome, 2024-02-16: "I was soooo much faster with a num pad and the terminal than clicking around the SAP GUI." — [HN 39395556](https://news.ycombinator.com/item?id=39395556)
- Tax software: LASR on Cantax — [HN 41917568](https://news.ycombinator.com/item?id=41917568)
- Pharmacy: brabel on an Australian pharmacy package with an encrypted DB — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- Portals, generically: suchintan (Skyvern) lists "downloading your electricity statements, looking up freight shipment information" — [HN 43572596](https://news.ycombinator.com/item?id=43572596); Intuned's customers in govtech and insurance tech — [HN 48445171](https://news.ycombinator.com/item?id=48445171)
- Prior-auth regulation context: nradov, 2026-05-14, on HL7 Da Vinci APIs: "These APIs give providers standard ways to check whether prior authorization is required" — [HN 48129564](https://news.ycombinator.com/item?id=48129564); vendor pages note CMS-0057-F requires affected payers to offer a Prior Authorization API by 2027-01-01 — [optexity blog](https://optexity.com/blog/automating-prior-authorization-and-eligibility-verification-across-payer-portals) (vendor)

### Inferences
- Green-screen users praise the speed of the keyboard-driven UI; the pain is not the UI, it is the hand-off out of it. A compiled capability that reads a value back from a terminal screen and writes it to a web form matches that.
- Payer-portal automation has a regulatory clock on it (CMS-0057-F prior-auth APIs by 2027); eligibility and the long tail of non-covered payers remain UI-driven.
- The named systems split into desktop-Windows (QuickBooks Desktop, Cantax, OpenDental, SAP GUI, DMS) and browser (payer portals, AppFolio, govtech). The brief's design (a human takes over "the same browser") covers the second group directly; the first group needs a desktop surface.

### Gaps
- No mentions in 2023–2026 HN comments of Symitar/Episys, Jack Henry, Fiserv, Availity, eClinicalWorks, Dentrix, Eaglesoft, or court e-filing systems. Absence on HN is not absence of pain; those communities live on Reddit, Dentaltown and vendor user groups.

---

## Q3. What do people say about AI browser / computer-use agents they tried?

### Takeaway
First-hand reports from 2024-12 to 2026-06 are consistent: agents are slow (minutes to tens of
minutes for a click path), expensive per run ($2.27 for three contact-form submissions; "$40/hr
in token costs"; half a 5-hour Codex plan on one search), nondeterministic, prone to claiming
success without doing the action, and frightening on irreversible steps. The practitioners who
report success did so by getting the model out of the hot path: record once, replay as a script,
fall back to the agent only on a broken step, and keep a human able to review.

### Cited Findings

#### Slow
- janalsncm, HN, 2026-05: "The vision model took almost 20 minutes to do the thing that Sonnet did in 20 seconds." — [HN 48024859 thread](https://news.ycombinator.com/item?id=48024859)
- rahulyc, HN, 2026-05-05: "we don't have the patience to wait 20 mins. to click a button." — [HN 48027704](https://news.ycombinator.com/item?id=48027704)
- hamasho, HN, 2026-05-06: "Computer use is a hit and miss (mostly miss), but playwright MCP often works very well." and "So easy tasks can easily add up to tens of minutes or even hours." — [HN 48031468](https://news.ycombinator.com/item?id=48031468)
- etothet, HN, 2026-05 (AWS Nova Act): "I remember trying an early version of AWS's Nova Act and laughed at how slow it was." ; on Claude driving a grocery site: "It was hilariously slow, but it did get the job done." — [HN 48024859 thread](https://news.ycombinator.com/item?id=48024859)
- ceejayoz, HN, 2026-05 (Claude Chrome extension): "It breaks like 80% of the time for me, and it's incredibly slow." — [HN 48024859 thread](https://news.ycombinator.com/item?id=48024859)
- edunteman (Pig.dev, legacy Windows apps in healthcare, lending, manufacturing), HN, 2025-05-14: pure agents "can run around $40/hr in token costs and take 5x longer than a human to perform a workflow" ; "Using a pure-agent approach proved to be highly wasteful." — [HN 43988381](https://news.ycombinator.com/item?id=43988381)
- gregpr07 (Browser Use founder), HN, 2025-05-16: "Pure LLM agents were slow, expensive, and unpredictable for these high-frequency tasks." and, of recorded scripts, "Scripts run reliably, 10x faster, and ~90% cheaper than Browser Use." — [HN 44007065](https://news.ycombinator.com/item?id=44007065)

#### Expensive per run
- arbol, HN, 2026-06-08 (Intuned trial): "So far its cost me $2.27 to submit a contact form 3 times" ; asks "why is this better than a captcha solver with human solves at 1000 per $2?" — [HN 48447275](https://news.ycombinator.com/item?id=48447275)
- m3kw9, HN, 2026-05-06: "I did a simple computer use to search something, and used up 50% of my 5h plan limit from codex." — [HN 48032122](https://news.ycombinator.com/item?id=48032122)
- sheepscreek, HN, 2026-05 (computer-use agents): "the worst of both worlds. Expensive and inaccurate." — [HN 48024859 thread](https://news.ycombinator.com/item?id=48024859)
- deepdarkforest, HN, 2025-08-14: "It actually is annoyingly expensive with Claude if you break caching" — [HN 44905715](https://news.ycombinator.com/item?id=44905715)
- jacktu, HN, 2026-05-05 (on cost and latency): "are absolute dealbreakers for real-time consumer apps right now." — [HN 48026333](https://news.ycombinator.com/item?id=48026333)
- Measured benchmark, reflex.dev, 2026-04-27 (Claude Sonnet via browser-use screenshots vs the same task as structured API calls): 53 ± 13 steps vs 8; 1003 s ± 254 s vs 19.7 s; 550,976 vs 12,151 input tokens (the "45x"); the vision agent "missed three of four pending reviews" until a 14-step walkthrough was added; the author still calls vision agents the right tool "for applications you do not control" — [reflex.dev](https://reflex.dev/blog/computer-use-is-45x-more-expensive-than-structured-apis/)

#### Unreliable, nondeterministic, lies about completion
- virgildotcodes, HN, 2025-07-17: "I have yet to try a browser use agent that felt reliable enough to be useful, and this includes OpenAI's operator." and "They seem to fall apart browsing the web, they're slow, they're nondeterministic." — [HN 44595959](https://news.ycombinator.com/item?id=44595959)
- timabdulla, HN, 2025-01-23 (Operator preview): "they can still get very easily confused with more complex tasks or unfamiliar interfaces." — [HN 42806730](https://news.ycombinator.com/item?id=42806730)
- planar_vector, HN, 2024-12-09: "I've tried multiple times to book a restaurant on skyvern and AgentE, but the agents never got to completion." — [HN 42365427](https://news.ycombinator.com/item?id=42365427)
- zhendlin, HN, 2024-12-09: "often times will say a task is completed, but it actually has not done the action." — [HN 42362929](https://news.ycombinator.com/item?id=42362929)
- moomoo11, HN, 2025-10-18: "I tried skyvern like 6 mo ago and it didn’t work for scraping a site" — [HN 45625571](https://news.ycombinator.com/item?id=45625571)
- androng, HN, 2025-04-23: "they all can do is the one-page job applications and not the much more common Workday 10-page job applications" — [HN 43777550](https://news.ycombinator.com/item?id=43777550)
- nycdatasci, HN, 2025-02-15 (travel booking agent): "it has made enormous errors like booking for a month and 3 days instead of 3 days" — [HN 43057888](https://news.ycombinator.com/item?id=43057888)
- julius, HN, 2026-05-05 (open vision models): "They fully hallucinate x,y coords." — [HN 48027390](https://news.ycombinator.com/item?id=48027390)
- sneefle, HN, 2026-07 (on verification): "vision-only verification passes because the screen genuinely looks correct." and the failure class "it was commits that don't commit." — [HN 48922706 thread](https://news.ycombinator.com/item?id=48922706)
- madikz, HN, 2026-07: "the hardest part is definitely the verification step." — [HN 48922706 thread](https://news.ycombinator.com/item?id=48922706)
- cdolan, HN, 2025-05: "We've been using BrowserUser to try and create deterministic playwright scripts for months with mixed results." — [HN 44007065 thread](https://news.ycombinator.com/item?id=44007065)
- _crowecawcaw, HN, 2026-05: "LLMs had trouble getting precise pixel coordinates from a screenshot to move a mouse." — [HN 48280729 thread](https://news.ycombinator.com/item?id=48280729)

#### Scary on irreversible actions; no way to step in
- sensanaty, HN, 2024-10-23: "it'll just click on the "close my account" button for no reason half the time" — [HN 41925096](https://news.ycombinator.com/item?id=41925096)
- imranq, HN, 2024-10-25: "If the LLM gets even one pixel value wrong, then at best the whole process breaks down." / "At worst, you could do some irreversible damage." — [HN 41946118 thread](https://news.ycombinator.com/item?id=41946118)
- throwaway0123_5, HN, 2024-10: "Would basically need constant monitoring for me not to be paranoid it did something stupid." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- minimaxir, HN, 2024-10-22: "And it's guaranteed that there will be a viral story where Claude will accidentally delete something important with it." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- StarPA, HN, 2026-07: "Clicking around a page is one thing, but submitting a form, sending a message or confirming a payment is another" — [HN 48922706 thread](https://news.ycombinator.com/item?id=48922706)
- fchishtie (Minicor), HN, 2026-05-26: "you don’t want an agent to potentially mess something up" — [HN 48280729](https://news.ycombinator.com/item?id=48280729)
- iamcreasy, HN, 2025-08-17: "How does it know when to stop and ask a human to intervene?" — [HN 44901528 thread](https://news.ycombinator.com/item?id=44901528)
- huss97 (Surf.new, open-source Operator alternative), HN, 2025-02-03: "We also don't yet support operator features like taking control and multiple tabs yet either." and "Heads up - it's new, and slow, and agents can fail in all sorts of ways." — [HN 42919217](https://news.ycombinator.com/item?id=42919217), [HN 42921823](https://news.ycombinator.com/item?id=42921823)
- dangoodmanUT, HN, 2025-09-15: "One achillies heel of browser use agents is that you often can't filter permissions like you can with API keys" — [HN 45249535](https://news.ycombinator.com/item?id=45249535)
- deepdarkforest, HN, 2025-08-14: "agents are inherently very tough to guardrail on an action space so big like in CUA." and "The funny thing about determinism is how deterministic you should be when to break" — [HN 44905715](https://news.ycombinator.com/item?id=44905715)
- EGreg, HN, 2024-10, on approval prompts: "People would mostly just rubber-stamp it" — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- herpdyderp, HN, 2025-10-17: "I'd be all over Skyvern if only they had enterprise compliance agreements available." — [HN 45622188](https://news.ycombinator.com/item?id=45622188)
- Second-hand Reddit sentiment (no usernames or URLs given by the aggregator): r/ChatGPT view of Operator summarised as "Impressive demo, genuinely useful for specific tasks, too expensive at $200 unless you actually use it for browser tasks" — [aitooldiscovery.com](https://www.aitooldiscovery.com/guides/best-ai-agents-reddit); a 2026 Manus review reports the "recurring consensus" that it is "worth trying for well-scoped, low-stakes tasks and risky to trust with anything mission-critical" and that "Credit burn on looping tasks is the most common complaint" — [ciela.ai](https://ciela.ai/blogs/manus-ai-reddit-review) (both are aggregator blogs; not verifiable here)

#### What the successful practitioners converged on (record once, replay, model only on failure, human reviews)
- edunteman (Pig / Muscle-Mem), HN, 2025-05-14: "The goal of Muscle-Mem is to get LLMs out of the hot path of repetitive automations" ; "intelligently swapping between script-based execution for repeat cases" ; "falling back to agent mode if edge cases are detected." ; "An explicit goal of Muscle Mem is to be a deterministic system, more like a DB" ; "it misses the sneaky challenge of Muscle Mem systems, which is continuous cache validation." ; "Emulating human mouse and keyboard is an absolute last resort for getting data across the application boundary" — [HN 43988381](https://news.ycombinator.com/item?id=43988381)
- deepdarkforest, same thread, on validating a cached trajectory: "comparing embeddings to cache validate the starting position is super gray, no clear threshold." and "I just don't see how you can reliably validate." — [HN 43988381](https://news.ycombinator.com/item?id=43988381)
- gregpr07 (Workflow Use), HN, 2025-05-16: enterprises want workflows "that they want to reliably run a million times without breaking" ; "If a step breaks, workflow will fallback to Browser Use and agentically run the step." — [HN 44007065](https://news.ycombinator.com/item?id=44007065); vasusen, same thread: "we independently arrived at the same pattern and have been impressed with how well it works." ; deepdarkforest, same thread, on healing: "it's very easy to get off the rails if one step fails"
- hamasho, HN, 2026-05-06, proposing the agent decide when to compile a skill: "Like Just-In-Time compiler, the skills are a byproduct of the agent instruction" — [HN 48031468](https://news.ycombinator.com/item?id=48031468)
- mattfrommars, HN, 2025-08-18, on cached replays: "Very efficient strategy than to run the step each time using LLM" — [HN 44901528 thread](https://news.ycombinator.com/item?id=44901528)
- fkilaiwi (Intuned), HN, 2026-06-08: "What our users love is the agent and the idea that we are not using AI at runtime which improves reliability." ; "its also predictable, if it messes up, you know what happened" ; "why not write the code, run it, and get consistent and fast result?" ; on self-healing, it "either proposes a fix for review or deploys it automatically." ; "getting code that you can review and merge has been life changing for our customers." — [HN 48445171](https://news.ycombinator.com/item?id=48445171)
- nkov47 (Coasty), HN, 2026-07-15: "The API can also pause a run for human approval, retry from a checkpoint, or return control to the developer" ; "the agent’s recovery job is to get the UI back into one of those known states" ; risk framing: "that becomes risky in workflows involving patient records, payments, or regulatory filings." — [HN 48922706](https://news.ycombinator.com/item?id=48922706); madikz, same thread: "The agents handle the execution path, the rules handle the truth."
- arcb (BitBoard), HN, 2025-06-10, on their operating rule: "100% of our outputs are reviewed by the clinical team shortly after entry" and "Otherwise, we fail the task and flag it to the team." ; "we prefer the strongest data types we can access." — [HN 44237769](https://news.ycombinator.com/item?id=44237769)
- mediaman, HN, 2026-05-26, on why he prefers a scripted desktop approach: general "computer use" automation, in his view, has not worked well outside the browser — [HN 48284582](https://news.ycombinator.com/item?id=48284582)
- sahmeepee, HN, 2024-09, on a scripted automation: "the automation has already paid for itself many times over in a couple of years." — [HN 41567387 thread](https://news.ycombinator.com/item?id=41567387)

### Inferences
- The HN practitioner consensus by mid-2026 is almost exactly Handrail's architecture: model once, compile, replay deterministically, model only on a detected edge case, human review of the compiled thing. Five independent teams (Pig/Muscle-Mem, Browser Use/Workflow Use, Intuned, Coasty, hamasho's personal JIT-skills idea) describe arriving at it. That is strong validation of the bet and also a warning that the record-replay-fallback shape is becoming table stakes; the differentiators have to be the parts the others admit are hard.
- The parts they admit are hard are: (1) validating that the cached run still applies (deepdarkforest: "no clear threshold"; edunteman: "continuous cache validation"); (2) verification that an action actually committed (sneefle: "commits that don't commit"; madikz: "the hardest part is definitely the verification step"); (3) deciding when to stop and ask (iamcreasy; deepdarkforest's "how deterministic you should be when to break"). Handrail's typed capability with deterministic checks, the independent verify step, and the rung ladder are aimed at exactly these three.
- Handrail fit on browser-agent complaints:
  - Slow / expensive per run: answered. No model on the ordinary path; `llm_calls` zero on replay.
  - Nondeterministic: answered. Replay is deterministic by construction.
  - Lies about completion: answered if the capability's verify step reads an independent signal (the brief's "independent check comes from the card"), not the screenshot.
  - Irreversible actions: answered. Named-human approval before commit steps; journalled `dispatched`/`observed` so a commit is never re-executed.
  - No way to step in: answered. Human rung takes over the same browser and hands back.
  - Audit / compliance (herpdyderp, stavros): answered in spirit by hash-chained evidence; an actual compliance agreement is a business artefact, not a design one.
  - Approval fatigue (EGreg: "rubber-stamp it"): not answered by design; a named approver on every irreversible step can become a rubber stamp if the volume is high. Worth a product rule on batching or sampling.
  - Data sovereignty / cloud (smcleod, rkagerer, ilundin): not addressed in the notes; depends on deployment model.
  - CAPTCHAs and bot detection (arbol, colesantiago, capiki): not answered; a deterministic replay still gets flagged, and the only honest answer is the human rung.

### Gaps
- No first-hand Reddit experience reports on Operator, Manus, Browser Use, Skyvern; only two aggregator blogs summarising Reddit without attributable quotes.
- No practitioner named Anthropic's Computer Use, Operator or Manus as something they run in production for a business process; the production stories are all the hybrid record-replay products.

---

## Q4. What do people pay, or say they would pay, to make a recurring UI task go away?

### Takeaway
Concrete numbers are scarce and mostly come from HN rather than Reddit. Enterprise RPA is quoted
at "$50k a month" versus "$500 a month" for Power Automate and "a couple of hundred thousand
dollars for UIPath licensing"; agent token cost is quoted at "$40/hr"; the going consumer price
of a browser agent is the $200/month tier; and in healthcare the cost being displaced is a
medical assistant's 15–20 minutes per patient or an offshore contractor's hourly rate.

### Cited Findings
- devjab, HN, 2023-08-14 (EU investment bank; RPA vendor selection): "It's literally $500 a month vs $50k a month" (Power Automate vs BluePrism/UiPath/Automation Anywhere, author's own figures) and "Back then you had to consider what go buy, would it be BluePrism, UIPath, automation anywhere, something else?" — [HN 37117988](https://news.ycombinator.com/item?id=37117988)
- devjab, HN, 2023-08-05: "Why would your organisation shell out a couple of hundred thousand dollars for UIPath licensing" — [HN 37010712](https://news.ycombinator.com/item?id=37010712)
- deepdarkforest, HN, 2025-08-14, on incumbent lock: "uipath and the others have a chokehold" — [HN 44905715](https://news.ycombinator.com/item?id=44905715)
- infecto, HN, 2024-10, on market size as a proxy for spend: "UiPath has a $7bn market cap and thats only a single player in the industry of automation." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)
- edunteman, HN, 2025-05-14: pure agents "can run around $40/hr in token costs" — [HN 43988381](https://news.ycombinator.com/item?id=43988381)
- gregpr07, HN, 2025-05-16: recorded scripts "~90% cheaper than Browser Use" — [HN 44007065](https://news.ycombinator.com/item?id=44007065)
- zuzululu, HN, 2026-06-08: "we already pay $200/month to OpenAI to turn automation into code" — [HN 48445171 thread](https://news.ycombinator.com/item?id=48445171)
- arbol, HN, 2026-06-08: "$2.27 to submit a contact form 3 times" vs human CAPTCHA solvers "at 1000 per $2" — [HN 48447275](https://news.ycombinator.com/item?id=48447275)
- OsrsNeedsf2P, HN, 2025-02-25 (comparing Browser Use and Skyvern pricing): "it's only $30 worth of credits" — [HN 43175070](https://news.ycombinator.com/item?id=43175070)
- 0xWTF, HN, 2026-05: "Akasa gets a seat license for each medical system they service" (how a medical-billing automation vendor is charged by the EHR) — [HN 48024859 thread](https://news.ycombinator.com/item?id=48024859)
- rkagerer, HN, 2025-08-14, on pricing models he rejects: "I don't want to be paying per-action, per-month, per-token, etc." — [HN 44901528 thread](https://news.ycombinator.com/item?id=44901528)
- Labour being displaced: arcb, "Their MAs were spending 15 to 20 minutes per patient just entering intake form data into the EHR." — [HN 44237769](https://news.ycombinator.com/item?id=44237769); grepfru_it, "8-16 hours" a month on bills — [HN 38905061](https://news.ycombinator.com/item?id=38905061); suchintan, "usually the CEO" spending "a few hours a week" ordering parts — [HN 42742518](https://news.ycombinator.com/item?id=42742518); deaux, offshore contracting jobs that were "still far more expensive than LLMs" (paraphrase of the comment's claim) — [HN 45603350](https://news.ycombinator.com/item?id=45603350)
- Vendor figures (unverified, marketing): manual dental insurance verification "12 to 20 minutes per patient" — [RevenueWell](https://www.revenuewell.com/article/why-your-practice-should-automate-the-insurance-verification-process); "20–45 minutes per patient" — [Kairos Health AI](https://kairoshealthai.com/blog/dental-insurance-verification-ai); RPA maintenance "50+ developer-hours per year per portal integration" — [supergood.ai](https://supergood.ai/blog/rpa-bot-keeps-breaking-enterprise-portals); Fiverr data-entry gigs averaging about $72 per job, copy-paste gigs from $10–25 — [Fiverr data entry](https://block.fiverr.com/hire/data-entry)
- debarshri, HN, 2026-05: "Legacy system users are also the one who pays the most for tools and services." — [HN 48280729 thread](https://news.ycombinator.com/item?id=48280729)

### Inferences
- The price anchors a buyer will have in mind are: enterprise RPA at five figures a month plus a developer to keep it alive; Power Automate at hundreds a month; an offshore contractor or VA at an hourly rate; a $200/month agent subscription. A deterministic replay priced per capability rather than per token lines up with rkagerer's stated preference and with the "90% cheaper" figure the hybrid products advertise.
- In healthcare the willingness to pay is bounded by the MA's time per patient and by the EHR vendor's seat-licence tax on any automation vendor (0xWTF). Both should go into any unit-economics model.

### Gaps
- No Reddit data on VA/BPO hourly rates for data entry (r/smallbusiness, r/Entrepreneur, r/virtualassistants are the usual sources); no 2023–2026 HN comment states an hourly VA rate.
- No practitioner statement of the form "I would pay $X/month to make this task go away" was found anywhere reachable.
- No UiPath list-price or per-bot licence figure from a 2023–2026 practitioner; the $50k and "couple of hundred thousand" figures are one commenter's recollection.

---

## Q5. Hacker News threads on computer-use agents and "RPA is dead" with practitioner comments (index)

### Takeaway
The useful HN threads are the vendor launch posts, because the founders describe the customer
pain and the commenters push back with their own RPA scars. The 2026-05 "45x more expensive"
thread is the richest single source on cost and latency.

### Cited Findings
- "Computer Use is 45x more expensive than structured APIs", 2026-05-05, 495 points, 271 comments — [HN 48024859](https://news.ycombinator.com/item?id=48024859); the child thread "RPA companies like UiPath ard dead in the water, right?" — [HN 48029573](https://news.ycombinator.com/item?id=48029573)
- "Computer use, a new Claude 3.5 Sonnet, and Claude 3.5 Haiku", 2024-10-22 — [HN 41914989](https://news.ycombinator.com/item?id=41914989); and "Notes on Anthropic's Computer Use Ability", 2024-10-25 — [HN 41946118](https://news.ycombinator.com/item?id=41946118)
- "AI agents may soon surpass people as primary application users", 2025-01-14 — [HN 42670619](https://news.ycombinator.com/item?id=42670619)
- "Show HN: Muscle-Mem, a behavior cache for AI agents", 2025-05-14, 226 points — [HN 43988381](https://news.ycombinator.com/item?id=43988381)
- "Show HN: Workflow Use – Deterministic, self-healing browser automation (RPA 2.0)", 2025-05-16 — [HN 44007065](https://news.ycombinator.com/item?id=44007065)
- "Launch HN: Cyberdesk – Automate Windows legacy desktop apps", 2025-08-14 — [HN 44901528](https://news.ycombinator.com/item?id=44901528)
- "Launch HN: Minicor – Windows desktop automations at scale", 2026-05-26 — [HN 48280729](https://news.ycombinator.com/item?id=48280729)
- "Launch HN: Intuned – Build and run reliable browser automations as code", 2026-06-08 — [HN 48445171](https://news.ycombinator.com/item?id=48445171)
- "Launch HN: Coasty – An API for computer-use agents", 2026-07-15 — [HN 48922706](https://news.ycombinator.com/item?id=48922706)
- "Launch HN: Cenote – Back Office Automation for Medical Clinics", 2025-03-06 — [HN 43280836](https://news.ycombinator.com/item?id=43280836)
- "Launch HN: BitBoard – AI agents for healthcare back-offices", 2025-06-10 — [HN 44237769](https://news.ycombinator.com/item?id=44237769)
- "Show HN: Finic – Open source platform for building browser automations", 2024-09-17 — [HN 41567387](https://news.ycombinator.com/item?id=41567387)
- "Show HN: API Parrot – Automatically Reverse Engineer HTTP APIs", 2025-01-01 — [HN 42565821](https://news.ycombinator.com/item?id=42565821)
- "Show HN: legacy-use", 2025-07-14 (OP claims "A medical provider automated 30% of their admin work using GPT + legacy-use" and "We build in guardrails, so if something goes astray a human operator can be called in"; vendor claims) — [HN 44557169](https://news.ycombinator.com/item?id=44557169)
- UiPath Community Forum, 2025-12 and 2026-04, two threads on selectors breaking in production — [5699124](https://forum.uipath.com/t/selectors-breaking-after-every-application-reload-how-to-build-production-stable-selectors-in-uipath-studio/5699124), [5741088](https://forum.uipath.com/t/one-app-20-automations-ui-change-breaks-everything-how-are-you-handling-this/5741088)
- Contrarian framing worth keeping: imranq, 2024-10-25: "This is basically RPA with LLMs. And RPA is basically the worst possible solution to any problem." and "Any automated 'computer use' will always be a one-off, absurdly expensive, and completely impractical." — [HN 41946118 thread](https://news.ycombinator.com/item?id=41946118); kjellsbells, 2025-08-15: "a part of me wonders if our industry isnt putting a bandaid on a problem that we ourselves created." — [HN 44901528 thread](https://news.ycombinator.com/item?id=44901528); Hizonner, 2024-10: "It's just bizarre to force a computer to go through a GUI to use another computer." — [HN 41914989 thread](https://news.ycombinator.com/item?id=41914989)

### Inferences
- "RPA is dead" is argued on HN mostly by people who have never run RPA; the people who have (DebtDeflation, eastendguy, claytongulick, the UiPath forum posters) say it is awful and also that it is the only thing that works, and ask for better exception handling and guard rails, not for its removal.

### Gaps
- The 2022 thread "My biggest mistake as an RPA developer" (HN 30741335) is outside the 2023–2026 window and was not mined.
- The 380k-character Claude Computer Use thread was read only to the 300k mark; the last quarter may hold more first-hand accounts.
