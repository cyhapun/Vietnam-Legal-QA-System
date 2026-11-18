# Spec: Responsive Mobile & Tablet UI

## Purpose

Deliver a reliable, ergonomic chat interface across smartphones (360–430px), tablets (640–1023px), and desktops (≥ 1024px) with safe-area viewport sizing, touch-accessible controls, overflow-free toolbars and Markdown tables, and dark-mode parity.

## Requirements

### Requirement: Dynamic viewport and safe-area shell

The application MUST use dynamic viewport height (`h-dvh`), declare Next.js `Viewport` metadata with `viewportFit: 'cover'` and `interactiveWidget: 'resizes-content'`, and respect `env(safe-area-inset-bottom)` / `env(safe-area-inset-top)` so mobile browser toolbars, notches, and virtual keyboards do not clip the composer or sidebar footer.

#### Scenario: Viewing on mobile Safari or Chrome with browser bars and virtual keyboard

- **WHEN** the user opens the chat on a smartphone and focuses the message composer
- **THEN** the root shell fits the dynamic viewport (`h-dvh`) without double scrollbars or clipping
- **AND** the composer and sidebar footer include bottom safe-area inset padding

### Requirement: Adaptive sidebar drawer and edge-locked touch gestures

The sidebar MUST default to closed on viewports narrower than `1024px` (`< lg`) as an overlay drawer with backdrop, default to open inline (`lg:relative lg:w-64`) on desktop (`≥ 1024px`), auto-close after selecting a session or creating a new chat on `< 1024px`, and use axis-locked edge swipe gestures that do not trigger during vertical scrolling.

#### Scenario: Initial load on mobile or tablet portrait

- **WHEN** a user loads the app on a viewport narrower than `1024px`
- **THEN** the sidebar is closed by default so the full chat welcome or conversation area is unobstructed
- **AND** a clearly tappable menu toggle button (`PanelLeft`) is visible in the top header

#### Scenario: Starting a new chat or choosing a session on mobile/tablet

- **WHEN** the user opens the sidebar drawer on a viewport `< 1024px` and taps "Đoạn chat mới" or selects an existing conversation
- **THEN** the sidebar drawer closes automatically so the user immediately sees the active conversation

#### Scenario: Vertical scrolling with slight diagonal drift on touch screens

- **WHEN** the user scrolls vertically through messages or drags horizontally inside the middle of the screen
- **THEN** the sidebar drawer does not open unexpectedly; opening via swipe requires starting near the left screen edge (`≤ 36px`) and moving predominantly horizontally (`|deltaX| > 64` and `|deltaX| > |deltaY| * 1.8`)

### Requirement: Full-width mobile composer without overflow or iOS auto-zoom

The message composer MUST span the full available width on mobile and tablet (without desktop avatar alignment spacers), fit the law category picker and model badge cleanly without horizontal overflow on `360px` viewports, and use at least `16px` (`text-base`) font size on mobile text inputs to prevent iOS Safari auto-zoom.

#### Scenario: Typing on a 375px smartphone

- **WHEN** the user views the composer on a `375px` viewport
- **THEN** the composer is centered across the full width with balanced horizontal padding
- **AND** the law category button truncates cleanly alongside a compact model badge (`Gemini 3.1 Lite` on `< sm`, `Google AI Studio: Gemini 3.1 Flash-Lite` on `sm+`) with zero horizontal overflow
- **AND** focusing the textarea or sidebar search input does not trigger iOS Safari page zoom

### Requirement: Touch-accessible actions and Portal bottom-sheet modals

All interactive controls (session delete, message copy/edit/regenerate/feedback) MUST remain visible and easily tappable on touch devices (not gated behind desktop-only `hover`), and both `CitationModal` and the negative feedback form MUST render through `createPortal(..., document.body)` as bottom sheets on mobile (`< sm`) and centered dialogs on `sm+`.

#### Scenario: Deleting a session or copying/editing a prompt on a touch device

- **WHEN** a user views the sidebar or a user message on a mobile or tablet device (`< lg`)
- **THEN** the session delete button and user message copy/edit buttons are visible without requiring pointer hover

#### Scenario: Opening citation details or negative feedback form on mobile

- **WHEN** the user taps an inline legal citation link or the negative feedback (`ThumbsDown`) button on a smartphone
- **THEN** the modal renders via `createPortal` to `document.body` as a bottom-aligned sheet (`max-h-[82dvh]`, safe-area padded) that never clips behind the composer or overflows the screen edge

### Requirement: Responsive reading ergonomics and dark-mode consistency

Markdown tables and code blocks MUST scroll horizontally within their own container without widening the page; assistant messages on mobile MUST maximize reading width; the header storage indicator MUST stay single-line on mobile; the History Mini-map MUST appear only on `xl+` viewports with full dark-mode styling; and the initial loading splash MUST respect dark mode.

#### Scenario: Reading legal responses with tables on mobile in dark mode

- **WHEN** an assistant response contains a Markdown table or code block on a `375px` viewport in dark mode
- **THEN** only the table/code wrapper scrolls horizontally while the rest of the chat layout remains fixed to the viewport width
- **AND** the loading splash and History Mini-map (on `xl+`) render with dark surfaces and readable contrast
