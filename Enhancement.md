# Enhancements

A running log of what has changed on Ferasha, why, and what is next. Updated
with every change: newest first, each entry with its commit, so the owner and
anyone joining can see the state of the shop at a glance.

Every frontend change ships with its Storybook story (`frontend/stories`),
run before it is committed. If a story could not be run, the entry says so.

## Done

### 12 November 2026

| Enhancement | What it does, and why | Commit |
|---|---|---|
| Sign-in pages on silk | Sign-in, register, forgot/reset password and email confirmation now sit on a fine silk twill (gold threads one way, green the other, under a soft sheen) that fades out before the footer: a fabric house's own texture, in place of the coloured glows, which ended in a hard line above the footer. Drawn in SVG from the theme colours (Magic UI's striped pattern): a few hundred bytes, no photo, nothing moving, so nothing extra for a phone to load or run. The card is solid white and rises in gently, in CSS, so it never waits for the page's scripts, and stays still for anyone who has turned motion off. Inspired by Housiq's textured sign-in; Finvo's and Housiq's full-screen sign-in without the shop header was offered and declined in favour of keeping the shop around it. Skipped: Magic UI's noise texture (a filter that phones redraw slowly over a whole page). | this commit |
| White form fields everywhere | Text boxes, dropdowns and text areas were filled grey, which read as "switched off". They are now white with the theme's tested border, as the contrast test already assumed: on the sign-in pages, checkout, search and My account alike. Dark mode is unchanged. | this commit |
| "Sign in" on one line on phones | On phones the header's "Sign in" wrapped onto two lines and pushed the Ferasha wordmark off centre. It is now the person icon alone on phones (screen readers still hear "Sign in"), with the word from tablet up. New story: Commerce / HeaderActions / Guest On Phone. | this commit |
| Forest green theme | The whole site now wears the green of the Finvo and Housiq templates: headings and body text in a green-black ink instead of charcoal, a faint mint page ground so white cards and fields lift off it, and every grey, border and soft fill carrying a trace of green (they leaned olive, and one even leaned violet). The footer is now a deep forest green, like Housiq's. Buttons stay Kausar Dezine Studio's own green and gold stays the accent: Housiq's teal button and Finvo's lime were declined, the first because the shop already has a real brand green, the second because gold does the same job on dark green and suits a luxury house. The sign-in pages' silk now weaves green over a mint ground with gold as the cross thread. Every colour pair is held to the accessibility contrast rules; the focus ring and the error red were darkened a touch to keep passing on the mint. The admin's greys follow the new ink automatically. New story: UI / Palette / Forest. | this commit |

Stories run for this change: Palette, Account forms, Account recovery, Header actions, Checkout flow and Button (31 of 31 pass); unit tests 343 of 343, including the contrast and admin-colour sync checks. Checked in a real browser at laptop and phone widths.

### 9 November 2026

| Enhancement | What it does, and why | Commit |
|---|---|---|
| Security pass on sign-in | **Pages can't be framed**: on the live site no other website can show our pages inside its own (the trick of hiding a real "Place order" or sign-in page under fake buttons), and browsers are told to use HTTPS only. Every page also refuses plugin content and forms posting elsewhere, and keeps full page addresses (which can carry reset links) from leaking to other sites. **A password change now signs out everywhere at once**: before, a stolen sign-in could keep working for up to 30 minutes after the password changed; now it stops immediately. Shipping this signs everyone out once (old sign-ins lack the new marker). The AI service still accepts a sign-in until it expires (at most 30 minutes). **No slow build-up**: every active visitor added two database rows every 30 minutes, forever; expired ones are now deleted daily, and signing out every device takes two database steps however many there are (it took one per device). Still to do: a full script-level content security policy (needs its own careful pass so no page breaks). | this commit |
| Email settings reach the server | Password-reset and confirmation emails were working but only printed to the server log in development: the mail settings in `.env` were never passed to the backend container, so real sending could not be switched on at all. They are now passed through, an empty setting no longer breaks sending, and `.env.example` explains both the log (development) and real sending (Gmail app password for testing; a transactional provider for launch). | this commit |
| No more invisible sections after a fast scroll | Headings and sections that fade in as you scroll could stay invisible for good if you scrolled past them quickly (a fling on a phone, a "back to top" jump, the back button): the browser only reports when something *crosses* into view, and a short heading can jump from below the screen to above it in one frame. Seen on the homepage ("The Edit") and under product pages ("Complete the look"). Now anything you have scrolled past counts as seen and appears. One shared fix (`frontend/hooks/use-seen.ts`) covers every fade-in on the site, and number counters can reuse it so a figure never sits at "0". Checked in a real browser: jumping straight to the bottom of the homepage and a product page leaves nothing hidden (12 sections stayed hidden before). New story: Motion / Reveal After Fast Scroll, which failed before the fix and passes now (all 9 motion stories pass). | this commit |
| Rounded drawers everywhere | The bag and the filters now use the theme's rounded, floating drawer on every screen: it rises from the bottom on phones and slides in from the right from tablet up, inset from the edges, frosted, and closes by swiping, the X, Escape or the backdrop. The phone menu, the dashboard's phone sidebar and "Select your fit" float with the same rounded corners, so no panel on the site has a sharp edge. Fixed on the way: "Select your fit" opened under the sticky header on laptops (it was trapped inside the page-fade layer); it now opens above everything, like every other dialog. Checked in a real browser at phone, tablet and laptop widths. New story: Glass & feedback / Desktop drawer. The Storybook runner could not start its browser on this machine this time (connection timeout, no story ran); the story's checks were run against the live site instead and pass. | this commit |
| Sign-in and registration, rebuilt | **Google**: "Continue with Google" on both pages, shown only once the owner adds Google keys (see below), so never a dead button. Returning Google users are recognised by their Google account even if they change email there; an existing Ferasha account is joined only when Google runs that inbox (Gmail or a company Google domain), and if someone had registered that email first without confirming it, their password is cancelled. Staff and admin accounts keep password-only sign-in; linked Google accounts show on each customer in Django admin. **Safer passwords and sign-in**: passwords found in known data breaches are refused (checked privately: only 5 characters of a scrambled code leave the server; if the checking service is down, sign-up still works). Ten wrong passwords used to be limited only per internet address; now five wrong tries lock that one account for 15 minutes from anywhere, which stops guessing spread across many devices (unknown emails lock the same way, so it reveals nothing). **Easier forms**: an eye on every password box (hides again on submit), a Caps Lock warning, "Did you mean gmail.com?" for common email typos, a live password checklist, mistakes shown when you leave a box and cleared as soon as they are fixed, and the cursor taken to the first problem. Registering asks for four things instead of six (no confirm-password, no mobile; mobile is asked at checkout). "Keep me signed in on this device": un-ticked, closing the browser signs you out, for shared family phones. My account asks unconfirmed customers to confirm their email, with a one-tap resend. **Look**: one centred card on a soft gold-and-green wash, with "Forgot password?" beside the password label (inspired by the Housiq and Finvo templates the owner shared). Not taken from them: a greyed-out button until terms are ticked (it hides why; we say why), GitHub sign-in, a second logo under the shop header. Not built yet: two-step codes, passkeys, Apple and Meta sign-in. | this commit |
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
4. **Sign-in, round two**: passkeys (fingerprint/face sign-in, no password), two-step codes for the owner and staff accounts first, an email when an account signs in from a new device, and Apple sign-in once there is an Apple Developer account.
5. **Payment gateway** (Razorpay) - deliberately last; the backend is largely ready.

## Later, when upgrading

- Next.js 16 with ESLint 10: ESLint 9 is marked deprecated, but Next 15's lint rules support only up to 9, so both move together.
- React's View Transitions, once stable: the photo flowing from a product card into its page.

## Waiting on the owner

- **Google sign-in keys**: in Google Cloud console, create an OAuth client (type "Web application") with the redirect address `https://<shop domain>/api/session/oauth/google/callback`, publish the consent screen with the shop name and logo, then set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`. Until then the button stays hidden.
- Confirm with the accountant: the stitching surcharge is taxed with the garment, at the garment's GST rate (one composite supply). That is how checkout charges it now.
- In Django admin, every bespoke product needs a "Made to measure" variant (size CUSTOM, stock 0); without one the product page falls back to "call the atelier".

- Photography and vector logos.
- Policy details shown in each page's draft box: return window and refunds, dispatch times and couriers, grievance officer, customer-care email, opening hours, legal name and GSTIN, record retention. A lawyer should read Privacy and Terms.
- Email sending settings (`EMAIL_HOST` and related) before launch.
- Changing the owner account's weak password.
