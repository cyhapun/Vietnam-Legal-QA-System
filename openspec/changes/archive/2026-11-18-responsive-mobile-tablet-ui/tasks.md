# Implementation Tasks: Responsive Mobile & Tablet UI Overhaul

## 1. Viewport, Safe Area & CSS Foundations
- [x] 1.1 Export Next.js `viewport: Viewport` (`viewportFit: 'cover'`, `interactiveWidget: 'resizes-content'`) in `frontend/app/layout.tsx`.
- [x] 1.2 Clean up duplicate `@keyframes blink` / `.typing-cursor::after` in `frontend/app/globals.css`, add `overscroll-behavior-y: none`, and keep scrollbar/shimmer styles clean.
- [x] 1.3 Update `frontend/components/chat/layout.ts` so `CHAT_CONTENT_WIDTH_CLASS` uses full width on mobile/tablet (`w-full lg:max-w-3xl`).

## 2. Adaptive Shell, Sidebar Drawer & Edge-Locked Swipe
- [x] 2.1 Update `frontend/components/chat/ChatInterface.tsx` to use `h-dvh`, dark-mode-safe splash loader (`bg-slate-50 dark:bg-[#171717]`), and default `isSidebarOpen` based on desktop breakpoint (`window.innerWidth >= 1024`).
- [x] 2.2 Shift Sidebar inline breakpoint from `md:` to `lg:` (`1024px`), auto-close drawer on `< 1024px` for both `onSelectSession` and `onNewChat`, and refactor touch swipe to ref-based axis-locked edge swipe (`startX <= 36`, `|deltaX| > 64`, `|deltaX| > |deltaY| * 1.8`).
- [x] 2.3 Update `frontend/components/chat/Sidebar.tsx` to use `h-full`, safe-area footer padding, `16px` mobile search input (`text-base sm:text-[13px]`), and touch-visible delete button (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100`) with comfortable tap padding.

## 3. Responsive Header, Empty State, Mini-map & Composer
- [x] 3.1 Refine top header in `frontend/components/chat/ChatInterface.tsx` (show brand title on `< lg`, compact `Lưu cục bộ` storage badge on `< sm` to prevent wrapping, comfortable tap target on menu toggle).
- [x] 3.2 Update History Mini-map in `frontend/components/chat/ChatInterface.tsx` to `hidden xl:flex` with full dark-mode styling (`dark:bg-[#1f1f1f]`, `dark:border-white/10`, `dark:text-gray-200`).
- [x] 3.3 Fix composer alignment & width in `frontend/components/chat/ChatInterface.tsx` (hide desktop avatar spacer on `< lg`, add `safe-area-inset-bottom`, use `text-base sm:text-[15px]` on textarea, scrollable category dropdown `max-h-[55dvh]`, and clean wrapping/truncation).
- [x] 3.4 Make `frontend/components/chat/ProviderSelector.tsx` compact on mobile (`Gemini 3.1` on `< sm`, full `Google AI Studio: Gemini 3.1 Flash-Lite` on `sm+`) while preserving `verify-chat-ux.mjs` compatibility.
- [x] 3.5 Refine `frontend/components/chat/ChatEmptyState.tsx` spacing, logo sizing, and suggestion card grid for mobile (375px), tablet (768px), and desktop.

## 4. Chat Messages, Markdown Overflow & Portal Bottom Sheets
- [x] 4.1 Optimize `frontend/components/chat/ChatMessage.tsx` for mobile reading width (compact top avatar+name header on `< sm`, side avatar on `sm+`, `break-words`, horizontally scrollable `table` and `pre` Markdown renderers).
- [x] 4.2 Make user message copy/edit actions visible on touch screens (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100`) and ensure comfortable touch target sizes (`p-2`) across all toolbar buttons.
- [x] 4.3 Migrate `CitationModal` and the Negative Feedback form in `frontend/components/chat/ChatMessage.tsx` to `createPortal(..., document.body)` with mobile Bottom Sheet presentation (`items-end sm:items-center`, `rounded-t-2xl sm:rounded-2xl`, `max-h-[85dvh]`, safe-area padding) and `Escape` key dismissal.

## 5. Verification & Visual QA
- [x] 5.1 Extend `frontend/scripts/verify-chat-ux.mjs` with checks for `h-dvh`, `createPortal` in `ChatMessage.tsx`, `viewportFit`, and run all `npm run verify:*` scripts + `npx tsc --noEmit`.
- [ ] 5.2 Visually verify the running app at `http://localhost:3000` across Mobile (`390x844`), Tablet Portrait (`768x1024`), Tablet Landscape (`1024x768`), and Desktop (`1440x900`) viewports (both Light and Dark mode) — *pending manual check in Chrome DevTools / phone because Chrome remote debugging was not active*.
