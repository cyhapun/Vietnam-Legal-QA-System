# Proposal: Responsive Mobile & Tablet UI Overhaul

## Why

An end-to-end audit of `frontend/` revealed 13 real UI/UX defects affecting mobile phones (360–430px, iOS/Android) and tablets (640–1023px), as well as several dark-mode and layout inconsistencies on desktop:

1. **Broken initial mobile/tablet layout**: `Sidebar` defaults to open (`useState(true)`), covering ~75% of mobile screens on load, and switches to inline at `md:` (768px), squeezing tablet-portrait chat to ~500px.
2. **Mobile viewport & keyboard clipping**: Using `h-screen` (`100vh`) without `viewportFit: 'cover'`, `interactiveWidget: 'resizes-content'`, or `safe-area-inset` causes the bottom composer to be clipped by mobile browser toolbars, virtual keyboards, and iOS home indicators.
3. **Cramped & misaligned mobile composer**: A desktop-only `w-8` + `gap-4` (48px) spacer stays visible on mobile, shifting the input box right and shrinking usable width; meanwhile the category picker + full `"Google AI Studio: Gemini 3.1 Flash-Lite"` badge exceed 430px on one row.
4. **Unusable hover-only actions & conflicting touch gestures**: Session delete buttons and user message copy/edit buttons use `opacity-0 group-hover:opacity-100` (invisible on touch screens); horizontal swipe detection ignores vertical `deltaY` and edge origin, firing accidentally while scrolling.
5. **iOS auto-zoom, overflowing popups, dark-mode mismatches, and Markdown overflow**: `< 16px` inputs trigger Safari iOS zoom; the negative-feedback popover overflows right edges and hides behind the composer; `CitationModal` lacks `createPortal` and mobile bottom-sheet ergonomics; the History Mini-map hardcodes light `bg-white` in dark mode and crowds tablet viewports; Markdown tables/code blocks lack horizontal scroll wrappers; and splash loading flashes `#F8FAFC` in dark mode.

## What Changes

- **Adaptive 3-tier responsive shell** (Mobile `< 640px`, Tablet `640–1023px`, Desktop `≥ 1024px` `lg:`):
  - Default `Sidebar` closed on viewports `< 1024px` (overlay drawer with backdrop & auto-close on selecting session or starting new chat); inline `lg:w-64` on desktop.
  - Replace `h-screen` with `h-dvh`, configure Next.js `Viewport` metadata (`viewportFit: 'cover'`, `interactiveWidget: 'resizes-content'`), and apply `safe-area-inset` padding.
  - Replace naive horizontal touch tracking with edge-initiated, axis-locked swipe (`|deltaX| > 64 && |deltaX| > |deltaY| * 1.8`, open only when starting within 36px of left edge, mobile/tablet only).
- **Full-width mobile/tablet composer & compact toolbar**:
  - Hide the desktop avatar alignment spacer on `< lg` screens and allow full-width composer with `max-w-3xl` centering.
  - Make `ProviderSelector` compact on mobile (`Gemini 3.1 Lite` on `< sm`, full `Google AI Studio: Gemini 3.1 Flash-Lite` on `sm+`) and prevent toolbar overflow with proper `min-w-0` / `truncate`.
  - Use `text-base` (16px) on mobile inputs/textareas to eliminate iOS Safari auto-zoom.
- **Touch-first controls, Portal Bottom Sheets & accessible tap targets**:
  - Show delete button in `Sidebar` and user copy/edit actions in `ChatMessage` persistently on touch/smaller screens (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100`) with comfortable tap padding (`min-h-[36px] min-w-[36px]` / `40px` for primary controls).
  - Render `CitationModal` and the Negative Feedback form via `createPortal(..., document.body)` as responsive Bottom Sheets on mobile (`items-end`, `rounded-t-2xl`, `max-h-[82dvh]`) and centered modals on `sm+`.
- **Reading ergonomics, Dark Mode polish & CSS cleanup**:
  - Wrap Markdown `table` and `pre` blocks in `overflow-x-auto` containers and optimize mobile assistant message padding/avatar layout so legal text uses maximum readable width.
  - Compact header storage badge on mobile (`Lưu cục bộ` on `< sm`, full text on `sm+`) to keep header height consistent.
  - Move History Mini-map to `xl:flex` with full `dark:` styling.
  - Fix splash loader dark-mode background (`bg-slate-50 dark:bg-[#171717]`) and deduplicate `.typing-cursor` / `@keyframes blink` in `globals.css`.
  - Add responsive verification checks to `frontend/scripts/verify-chat-ux.mjs` and verify across Mobile (390×844), Tablet (768×1024 & 1024×768), and Desktop (1440×900) viewports.

## Capabilities

### New Capabilities
- `responsive-mobile-tablet-ui`: Adaptive mobile, tablet, and desktop layout system covering `h-dvh` safe-area shell, drawer breakpoints, axis-locked edge swipe, touch-visible actions, Portal bottom-sheet modals, iOS zoom prevention, responsive Markdown tables, and dark-mode consistency.

### Modified Capabilities
- `refined-chat-ui`: Adjust desktop inline sidebar breakpoint to `lg:` (`1024px`) so tablets get a spacious drawer layout, and require `createPortal` rendering for `CitationModal`.

## Impact

- **Frontend files**: `frontend/app/layout.tsx`, `frontend/app/globals.css`, `frontend/components/chat/layout.ts`, `frontend/components/chat/ChatInterface.tsx`, `frontend/components/chat/Sidebar.tsx`, `frontend/components/chat/ChatMessage.tsx`, `frontend/components/chat/ChatEmptyState.tsx`, `frontend/components/chat/ProviderSelector.tsx`, `frontend/scripts/verify-chat-ux.mjs`.
- **Backend**: No backend changes required.
- **Dependencies**: Zero new npm packages required.
