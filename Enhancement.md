# Enhancements

A running log of what has changed on Ferasha, why, and what is next. Updated
with every change: newest first, each entry with its commit, so the owner and
anyone joining can see the state of the shop at a glance.

Every frontend change ships with its Storybook story (`frontend/stories`),
run before it is committed. If a story could not be run, the entry says so.

## Done

### 9 November 2026

| Enhancement | What it does, and why | Commit |
|---|---|---|
| Rounded drawers everywhere | The bag and the filters now use the theme's rounded, floating drawer on every screen: it rises from the bottom on phones and slides in from the right from tablet up, inset from the edges, frosted, and closes by swiping, the X, Escape or the backdrop. The phone menu, the dashboard's phone sidebar and "Select your fit" float with the same rounded corners, so no panel on the site has a sharp edge. Fixed on the way: "Select your fit" opened under the sticky header on laptops (it was trapped inside the page-fade layer); it now opens above everything, like every other dialog. Checked in a real browser at phone, tablet and laptop widths. New story: Glass & feedback / Desktop drawer. The Storybook runner could not start its browser on this machine this time (connection timeout, no story ran); the story's checks were run against the live site instead and pass. | this commit |
| Automatic quality checks | The frontend is now linted (Next.js's recommended rules), with zero warnings allowed, and CI runs it on every pull request alongside the typecheck, unit tests and stories. The backend's own lint (ruff) and migration check were run against this session's work: one import-order fix. | a688308 |
| Fonts shipped with the site | Cormorant Garamond and Inter now come from the site's own files (open licence, licences included) instead of being fetched from Google while building. The dev server had twice failed to fetch them and shown errors instead of pages. Same look; still preloaded with no layout shift; no requests to Google. | `6a56264` |
| Trust strip and order-placed moment | Four promises the shop already keeps (coverage stated, tailored in Kurla, made to measure, delivery terms) below the homepage hero and beside the buy button, from one source, so delivery wording always matches what checkout charges. Nothing about returns or payment security until those exist. After placing an order: a calm tick and "what happens next" (payment, the atelier - measurements checked first for bespoke - and delivery), shown only while the order is in progress. | `58ae924` |
| Motion, round one | The header steps aside while reading down a page and returns on scroll up (never while you are using it by keyboard). Product cards show a second photo on hover, ready for when photography arrives. Shop pages fade softly into each other, but never on the first load, so pages do not look slower. Fixed on the way: product photos would have shown as broken images the moment the first photo was approved (the site expected a plain link, the API sends a link and its description). Skipped: "Added ✓" (the bag already opens to confirm) and the photo-morph into the product page (needs React features that are not stable yet). | `ea02357` |
| Measurements forgotten at sign-out | Signing out (header, dashboard, password change) now also removes made-to-measure pieces from the bag, since each carries its owner's measurements; ready-made pieces stay. Found by an automated security review of the bespoke change. | `2c3ec30` |
| Bespoke orders | A customer chooses "made to measure" on the product page, enters measurements and adds the piece to the bag at the full price (garment + stitching). The server checks the measurements when the piece is added and again at checkout, then freezes them onto the order for the tailor. Each bespoke piece is its own line; made-to-measure never touches stock (not even on cancel). "Add full lining" now reaches the tailor. Browser measurement checks now match the server's exactly (one was stricter, four were missing). Unsent measurements are cleared on sign-out. Verified end to end with a real order. | `983726e` |
| This log, and reliable story runs | `Enhancement.md` is kept with every change. Storybook's test runner gets three minutes to start its browser (30 s was too short on a busy machine); the review and glass stories, which had not run, now pass, and a review-story bug (two "4 stars" on the page) is fixed. | `03ad2b3` |
| Phone drawers | Bag and filters rise from the bottom on phones and swipe away; side panels stay on desktop. No half-height stop: it hid the "Show garments" button. | `b995630` |
| Frosted glass | One definition (`frontend/lib/glass.ts`), three strengths: dialogs, sheets and drawers; things floating over photos (Tailored-by card, Bespoke badge); the phone buy bar. The secondary button is now the site-wide glass button. | `b995630` |
| Sweep button | "Book a bespoke fitting" fills green from the left on hover, in place of the paid shadcn.io pill button. | `b995630` |
| Bouncing checkbox | Every checkbox dips and springs when ticked, in theme green; still for reduced-motion users. | `b995630` |
| Chase loader | Six dots chasing round a circle while search results load. | `b995630` |
| Reviews | Product pages show the rating, star spread, "most say true to size" and "coverage as described" share; signed-in customers write reviews, which wait for moderation. | `f01a946` |
| Search | Every word counts, typos and regional spellings forgiven (gharara/garara, lehenga/lehnga), relevance ranking; header search with matches as you type. Postgres only, no new service. | `48bbbbc`, `f6b848e` |
| Account recovery | Forgot password, reset from the email link, confirm email (that link was dead before). | `89d5472` |
| Order emails | Customers are emailed when payment is confirmed, stitching starts (bespoke), it ships, is delivered, refunded or cancelled after payment. Fixed an HTML-injection gap in account emails. | `62bbfc4` |
| Help pages | Contact, Shipping, Returns, Privacy and Terms, with a visible "draft" box until the owner confirms each point. Fixed the footer's wrong "prices include GST". | `0d62f94` |
| Animated primitives | Dialogs, sheets, accordions, menus and tooltips move with animate-ui's springs. | `1b74b3c` |
| My account | Order history, name and mobile, password change. | `f262966` |

### 5 November 2026

| Enhancement | What it does, and why | Commit |
|---|---|---|
| Unpaid orders release stock | An order unpaid after 30 minutes is cancelled and its pieces return to stock, so abandoned checkouts never show items as sold out. | `2e805c6` |

### 4 November 2026

| Enhancement | What it does, and why | Commit |
|---|---|---|
| Owner dashboard | `/dashboard`: revenue, what needs the owner today, orders by stage, low stock, moving orders on. Editing stays in Django admin. | `9e1f01d`, `9ec594d`, `47777d1` |
| Collection page | Filters with live counts (modesty first), chips, sort, pages, phone filter panel; filtered views are shareable links. | `cf97a13`, `340a0fe`, `34c5fc3` |

## Next

Agreed or proposed, roughly in order:

1. **Motion, round two**: calm reveals for headings and sections. Also measure the homepage hero's fade-in text against load speed before launch.
2. **Frosted-glass icons** - waiting for the subject (categories? trust points?) and approval of CSS animation inside the SVG files.
3. **Review photos** through the face-blur pipeline.
4. **Payment gateway** (Razorpay) - deliberately last; the backend is largely ready.

## Later, when upgrading

- Next.js 16 with ESLint 10: ESLint 9 is marked deprecated, but Next 15's lint rules support only up to 9, so both move together.
- React's View Transitions, once stable: the photo flowing from a product card into its page.

## Waiting on the owner

- Confirm with the accountant: the stitching surcharge is taxed with the garment, at the garment's GST rate (one composite supply). That is how checkout charges it now.
- In Django admin, every bespoke product needs a "Made to measure" variant (size CUSTOM, stock 0); without one the product page falls back to "call the atelier".

- Photography and vector logos.
- Policy details shown in each page's draft box: return window and refunds, dispatch times and couriers, grievance officer, customer-care email, opening hours, legal name and GSTIN, record retention. A lawyer should read Privacy and Terms.
- Email sending settings (`EMAIL_HOST` and related) before launch.
- Changing the owner account's weak password.
