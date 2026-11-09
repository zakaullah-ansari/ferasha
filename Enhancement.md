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
| Bespoke orders | A customer chooses "made to measure" on the product page, enters measurements and adds the piece to the bag at the full price (garment + stitching). The server checks the measurements when the piece is added and again at checkout, then freezes them onto the order for the tailor. Each bespoke piece is its own line; made-to-measure never touches stock (not even on cancel). "Add full lining" now reaches the tailor. Browser measurement checks now match the server's exactly (one was stricter, four were missing). Unsent measurements are cleared on sign-out. Verified end to end with a real order. | this commit |
| This log, and reliable story runs | `Enhancement.md` is kept with every change. Storybook's test runner gets three minutes to start its browser (30 s was too short on a busy machine); the review and glass stories, which had not run, now pass, and a review-story bug (two "4 stars" on the page) is fixed. | this commit |
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

1. **Motion from movin.design** (proposed): product photo flowing into the product page; second photo on card hover; a calm "Added ✓" on Add to bag; header that hides on scroll down; soft page fades; an order-placed moment.
2. **Trust strip** with real facts (coverage stated, fully lined, free Maharashtra delivery, tailored in Kurla). Proposed.
3. **Frosted-glass icons** - waiting for the subject (categories? trust points?) and approval of CSS animation inside the SVG files.
4. **Review photos** through the face-blur pipeline.
5. **Payment gateway** (Razorpay) - deliberately last; the backend is largely ready.

## Waiting on the owner

- Confirm with the accountant: the stitching surcharge is taxed with the garment, at the garment's GST rate (one composite supply). That is how checkout charges it now.
- In Django admin, every bespoke product needs a "Made to measure" variant (size CUSTOM, stock 0); without one the product page falls back to "call the atelier".

- Photography and vector logos.
- Policy details shown in each page's draft box: return window and refunds, dispatch times and couriers, grievance officer, customer-care email, opening hours, legal name and GSTIN, record retention. A lawyer should read Privacy and Terms.
- Email sending settings (`EMAIL_HOST` and related) before launch.
- Changing the owner account's weak password.
