# Week 1 Report: Wireframe to Static Web Page

**Project:** Fieldnote Coffee Roasters landing page
**Files:** `index.html`, `styles.css`, `screenshots/`

## 1. Wireframe analysis
I split the wireframe into six regions and gave each one a purpose before writing any code:

| Region | Purpose | HTML element |
|---|---|---|
| Header + navigation | Brand and page-level links | `header`, `nav` |
| Hero (text left, image right) | Core message and primary action | `section`, `figure` |
| Three-item feature row | Reasons to trust the brand | `section`, `ul` |
| Product card grid | Main content: what to buy | `section`, `article` in `li` |
| Story + sidebar | Long-form content with related links | `article`, `aside` |
| Newsletter + footer | Secondary action and site info | `form`, `footer` |

*(Note: no wireframe image was supplied with the brief, so this layout is a standard landing-page wireframe. Section names and proportions are easy to change in the CSS tokens and grid rules.)*

## 2. Semantic HTML decisions
- Landmarks (`header`, `nav`, `main`, `aside`, `footer`) give screen-reader users quick navigation. Two `nav` elements are distinguished by `aria-label`.
- One `h1`, then `h2` per section and `h3` per item, with no skipped levels. The sidebar heading is an `h2` styled smaller with a `.h3` class, so the outline stays correct while the look matches the hierarchy.
- Product cards are `article` elements inside a `ul`, so a screen reader announces "list, 3 items".
- The form has a real `<label for>`, `type="email"`, `autocomplete`, and `required`.
- Every "Add to basket" button has hidden text naming the product, so links are meaningful out of context.
- Illustrations are one inline SVG `<symbol>` reused with `<use>`, so no extra HTTP requests and colours can be changed with CSS `currentColor`.
- A skip link and visible `:focus-visible` outlines support keyboard users.

## 3. CSS organisation
`styles.css` has a table of contents and follows this order: design tokens, reset/base, layout helpers, components, sections, responsive, print.
- **Tokens:** colours, fonts, spacing, and radius live in `:root` custom properties, so a re-theme means editing one block.
- **Naming:** classes describe role (`.feature-grid`, `.story-side`), not appearance (`.green-box`).
- **Low specificity:** almost everything is a single class selector, which avoids override battles. The only compound selector is `.card p:not(.price)`.
- **Reusable components:** `.btn` with `-outline` and `-small` modifiers.

## 4. Layout strategy
- **CSS Grid** for 2D layouts: hero, feature row, story + sidebar, newsletter.
- **Flexbox** for 1D rows: header, nav, footer, button row, signup field.
- **`repeat(auto-fit, minmax(240px, 1fr))`** makes the product cards reflow from 3 → 2 → 1 columns with no breakpoint at all.
- **`clamp()`** scales headings fluidly between phone and desktop.
- **`min(100% - 2rem, 1100px)`** on `.container` gives a centred column with side gutters on small screens.
- The sticky header uses `scroll-padding-top` so anchor links are not hidden under it.

## 5. Responsiveness and testing
Breakpoints: **900px** (two-column grids become one column) and **560px** (header, form, and footer stack).
I tested with Playwright (Chromium) at **375px, 768px, and 1440px** and measured horizontal overflow: **0px at all three**. Screenshots are in `screenshots/`. I also confirmed the HTML tags balance with no unclosed elements.

## 6. Challenges and how I solved them
| Challenge | Solution |
|---|---|
| Sidebar's left border looked wrong once stacked on mobile | Inside the media query, swapped it for a top border and removed left padding |
| Paragraphs stretched uncomfortably wide on large screens | Capped at `60ch` for readable line length |
| Sidebar needed to be visually small but still a correct `h2` | Added a `.h3` utility so semantics and appearance are decoupled |
| Sticky header covered anchor targets | Added `scroll-padding-top` on `html` |
| Sticky header takes up too much of a small phone screen | Made it static below 560px |
| Needed images without external files | Drew a coffee bag and cup as inline SVG; one symbol reused in three colours |
| Screen readers saying "Add to basket" three times with no context | Added visually-hidden product names inside each button |

## 7. Accessibility and quality checks
Text/background contrast is above WCAG AA (dark ink on off-white, white on moss green). Keyboard focus is visible everywhere, motion is disabled under `prefers-reduced-motion`, and a print stylesheet hides the header, form, and buttons.

## 8. What I would improve next
Add real photography with `srcset`, a mobile menu toggle, and run Lighthouse and axe audits for a final accessibility score.
