# Design: Responsive Mobile & Tablet UI Overhaul

## Context

The frontend is a Next.js 15 App Router + React 19 + Tailwind CSS v4 single-page legal chat interface (`frontend/components/chat/`). Currently its breakpoints, viewport height, composer geometry, touch gestures, hover-gated controls, and overlays are tuned mainly for wide desktop monitors, causing severe ergonomics and layout defects on smartphones (360–430px) and tablets (640–1023px).

## Goals / Non-Goals

**Goals:**
- Smooth, zero-overflow layout across **Mobile** (`360–639px`), **Tablet** (`640–1023px`), and **Desktop** (`≥ 1024px`).
- True mobile viewport & keyboard support via `h-dvh`, `Viewport` metadata (`viewportFit: 'cover'`, `interactiveWidget: 'resizes-content'`), and `safe-area-inset` utilities.
- Touch-first ergonomics: no hover-hidden essential actions, comfortable tap targets, safe edge-initiated swipe gestures, and `16px` mobile inputs to prevent iOS Safari zoom.
- Portal-backed responsive Bottom Sheet / Modal overlays for `CitationModal`, Negative Feedback, and Delete Confirmation.
- Clean dark-mode parity (splash loader, History Mini-map) and horizontally scrollable Markdown tables/code blocks.
- Keep all existing `npm run verify:*` scripts and brand guidelines intact.

**Non-Goals:**
- Rewriting state management or adding new third-party UI libraries (e.g., Radix/Headless UI) — stay lightweight with Tailwind v4 + `createPortal`.
- Changing backend APIs or RAG pipeline behavior.
- Adding authentication or changing `CHAT_STORAGE_MODE` behavior.

## Decisions

### 1. Viewport Metadata, `h-dvh`, and Safe-Area Utilities

- **`frontend/app/layout.tsx`**: Export Next.js `viewport: Viewport`:
  ```ts
  export const viewport: Viewport = {
    width: 'device-width',
    initialScale: 1,
    viewportFit: 'cover',
    interactiveWidget: 'resizes-content',
  };
  ```
- **`frontend/app/globals.css`**:
  - Deduplicate the duplicate `@keyframes blink` and `.typing-cursor::after` blocks.
  - Add minimal utility classes or inline Tailwind arbitrary padding for safe areas (`env(safe-area-inset-bottom)`, `env(safe-area-inset-top)`), and ensure `html, body { overscroll-behavior-y: none; }` prevents rubber-band bounce behind fixed sheets.
- **Root containers**: Replace `h-screen` with `h-dvh` in `ChatInterface.tsx` (both splash screen and main wrapper) and `Sidebar.tsx` (`h-full` inside the `h-dvh` wrapper).

### 2. Three-Tier Breakpoint System (`< 640px` / `640–1023px` / `≥ 1024px`)

- **Sidebar state initialization** in `ChatInterface.tsx`:
  - Initialize `isSidebarOpen` lazily/via mount effect using `window.innerWidth >= 1024` (default `false` during SSR/mobile/tablet, auto-open on desktop `≥ 1024px` upon mount; also sync gracefully if resizing across `1024px`).
  - Use `lg:` (`1024px`) instead of `md:` (`768px`) for switching the sidebar between overlay drawer (`fixed inset-y-0 left-0 z-40 w-[82vw] max-w-[300px]`) and inline desktop rail (`lg:relative lg:z-20 lg:w-64`).
  - Backdrop button uses `lg:hidden`.
  - Auto-close sidebar on `< 1024px` when clicking **either** a session (`onSelectSession`) **or** "Đoạn chat mới" (`onNewChat`).
- **Safe edge-locked swipe gesture**:
  - Track `{ x, y }` on `touchstart` and `{ x, y }` on `touchmove` using refs (avoid re-rendering React state on every touchmove frame!).
  - Only act when `window.innerWidth < 1024`.
  - To **open** sidebar: `startX <= 36` (left screen edge), `deltaX > 64`, and `Math.abs(deltaX) > Math.abs(deltaY) * 1.8`.
  - To **close** sidebar when open: `deltaX < -64` and `Math.abs(deltaX) > Math.abs(deltaY) * 1.8`.

### 3. Composer Width, Compact Toolbar & iOS Zoom Prevention

- **`frontend/components/chat/layout.ts`**:
  - `CHAT_ROW_WIDTH_CLASS = 'max-w-4xl mx-auto'`
  - `CHAT_CONTENT_WIDTH_CLASS = 'w-full lg:max-w-3xl'` (full readable width on mobile/tablet; comfortable reading measure on desktop).
- **Composer container (`ChatInterface.tsx`)**:
  - Hide the desktop avatar alignment spacer on `< lg`: `<div className="hidden lg:block h-8 w-8 shrink-0" aria-hidden="true" />`.
  - Use balanced padding `px-3 sm:px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))]`.
  - Category picker button: `min-w-0 flex-1 sm:flex-initial max-w-[200px] sm:max-w-[280px] md:max-w-[320px]`.
  - Category dropdown popover: `w-[min(320px,calc(100vw-2rem))] max-h-[55dvh] overflow-y-auto`.
- **`ProviderSelector.tsx`**:
  - Keep `"Gemini 3.1 Flash-Lite"` in markup to preserve `verify-chat-ux.mjs`, while showing a compact label on narrow phones:
    - `<span className="hidden sm:inline">Google AI Studio: </span><span className="sm:hidden">Gemini 3.1</span><span className="hidden sm:inline">Gemini 3.1 Flash-Lite</span>` (compact `shrink-0` pill so it never overflows on 360px screens!).
- **Font size ≥ 16px on mobile inputs**:
  - Composer textarea: `text-base sm:text-[15px]` (`16px` on mobile prevents iOS Safari auto-zoom).
  - Sidebar search input: `text-base sm:text-[13px]`.

### 4. Touch-First Controls, Portal Bottom Sheets & Reading Ergonomics

- **Touch-accessible actions**:
  - `Sidebar.tsx` delete button: `opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100` with `p-2` tap area (`min-h-[36px] min-w-[36px]`).
  - `ChatMessage.tsx` user action bar (Copy / Edit): `opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-within:opacity-100`.
  - Increase toolbar icon button padding to `p-2` (`min-h-[36px] min-w-[36px] flex items-center justify-center`).
- **Assistant message reading width on mobile (`ChatMessage.tsx`)**:
  - On mobile (`< sm`), render assistant avatar + compact `"VietLaw AI"` label in a horizontal header row above the response (`flex-col sm:flex-row gap-2 sm:gap-4`) so legal articles and lists span nearly 100% of mobile screen width rather than losing 48px to a left gutter. Keep user bubble compact on the right (`max-w-[88%] sm:max-w-[82%]`).
- **Markdown overflow protection (`ChatMessage.tsx`)**:
  - Add custom `ReactMarkdown` renderers for `table` (wrapped in `<div className="my-3 w-full overflow-x-auto rounded-lg border border-slate-200 dark:border-white/10">`) and `pre` (`overflow-x-auto max-w-full`). Add `break-words` on prose container so long legal codes/URLs never force horizontal page scroll.
- **Portal Bottom Sheets (`ChatMessage.tsx`)**:
  - Render **CitationModal** via `createPortal(..., document.body)` with `items-end sm:items-center` container, `w-full sm:w-[90%] sm:max-w-2xl rounded-t-2xl sm:rounded-2xl max-h-[85dvh] flex flex-col`, safe-area bottom footer, and `Escape` key support.
  - Render **Negative Feedback Form** via `createPortal(..., document.body)` as a clean mobile bottom sheet / desktop centered dialog (eliminating right-edge overflow and composer overlap completely!).
- **Header, EmptyState, Mini-map, Splash Loader**:
  - Header (`ChatInterface.tsx`): Show short label on `< sm` (`Lưu cục bộ`) and full text on `sm+` (`Lịch sử chỉ lưu trên thiết bị này`) with `shrink-0` and `whitespace-nowrap`. Show compact brand title on `< lg` (`lg:hidden`).
  - `ChatEmptyState.tsx`: Slightly tighter vertical spacing & logo size on mobile (`h-16 w-16 sm:h-24 sm:w-24`, `py-6 sm:py-10`, `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` or `sm:grid-cols-3`) so suggestions stay comfortably visible above the composer on mobile and look balanced on tablets.
  - History Mini-map (`ChatInterface.tsx`): Change `hidden md:flex` → `hidden xl:flex` and add full dark-mode classes (`dark:bg-[#1e1e1e] dark:border-white/10 dark:text-gray-200 dark:hover:bg-blue-500/15`).
  - Splash loader (`ChatInterface.tsx`): Replace `style={{ background: '#F8FAFC' }}` with `bg-slate-50 dark:bg-[#171717]` and `dark:text-gray-400`.

## Risks / Trade-offs

- **Hydration mismatch if initializing `isSidebarOpen` from `window.innerWidth` in `useState`**: Mitigated by initializing `useState(false)` safely and syncing to `window.innerWidth >= 1024` inside `useEffect` (since `ChatInterface` already gates render on `isMounted`, there is zero flash and zero hydration warning!).
- **`verify-chat-ux.mjs` string assertions**: Must preserve all checked tokens (`Gemini 3.1 Flash-Lite`, `selectedCitation`, `createPortal`, `RotateCcw`, `Pencil`, tooltips, etc.) and extend the verification script with responsive guard checks.
