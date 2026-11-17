import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = process.cwd();
const chatInterface = readFileSync(resolve(root, 'components/chat/ChatInterface.tsx'), 'utf8');
const chatMessage = readFileSync(resolve(root, 'components/chat/ChatMessage.tsx'), 'utf8');
const processingTrace = readFileSync(resolve(root, 'components/chat/ChatProcessingTrace.tsx'), 'utf8');
const emptyState = readFileSync(resolve(root, 'components/chat/ChatEmptyState.tsx'), 'utf8');
const providerSelector = readFileSync(resolve(root, 'components/chat/ProviderSelector.tsx'), 'utf8');
const sidebar = readFileSync(resolve(root, 'components/chat/Sidebar.tsx'), 'utf8');
const proxyRoute = readFileSync(resolve(root, 'app/api/chat/route.ts'), 'utf8');

for (const label of [
  'Đang phân tích câu hỏi',
  'Đang tra cứu căn cứ pháp lý',
  'Đang chọn lọc thông tin phù hợp',
  'Đang tổng hợp câu trả lời',
]) {
  if (!processingTrace.includes(label)) {
    throw new Error(`Missing processing label: ${label}`);
  }
}

if (!processingTrace.includes('animate-thinking-shimmer')) {
  throw new Error('Processing trace must use animate-thinking-shimmer class for thinking text effect');
}

for (const obsolete of ['Tra cứu hoàn tất', 'Xem quá trình', 'Ẩn quá trình', '<ol', 'ChevronDown']) {
  if (processingTrace.includes(obsolete)) {
    throw new Error(`Obsolete boxed/table elements should be removed from processing trace: ${obsolete}`);
  }
}

if (!chatMessage.includes('!message.content?.trim()')) {
  throw new Error('ChatMessage must only render processing trace when there is no streaming content yet (!message.content?.trim())');
}

if (chatInterface.includes('isLoading && !streamingText')) {
  throw new Error('Large loading skeleton should not be used for active chat processing');
}

if (!chatInterface.includes("event.type === 'context'") || !chatInterface.includes('setStreamingContext(fullContext)')) {
  throw new Error('Context events must render sources before answer completion');
}

if (!chatInterface.includes("event.type === 'token'") || !chatInterface.includes("setProcessingStage('generating')")) {
  throw new Error('Token events must move processing into generation stage');
}

if (!chatInterface.includes('abortControllerRef.current.abort()') || !proxyRoute.includes('signal: req.signal')) {
  throw new Error('Cancel must abort the client stream and proxy fetch');
}

// Verification: LegalSourcesTrigger and side panel are removed
if (chatMessage.includes('LegalSourcesTrigger')) {
  throw new Error('Legal sources trigger should be removed from assistant message footer');
}

if (chatInterface.includes('id="legal-sources-panel"')) {
  throw new Error('Side drawer for legal sources should be removed');
}

// Verification: Inline citation modal is preserved
if (!chatMessage.includes('selectedCitation') || !chatMessage.includes('setSelectedCitation')) {
  throw new Error('Assistant message must preserve inline citation modal interaction');
}

// Verification: Brand logo mascot is integrated
if (!sidebar.includes('/logo.png') || !chatMessage.includes('/logo.png') || !emptyState.includes('/logo.png')) {
  throw new Error('Brand logo mascot must be used in sidebar, chat messages, and empty state');
}

// Verification: Delete confirmation modal rendered via portal to document.body
if (!sidebar.includes('createPortal') || !sidebar.includes('document.body')) {
  throw new Error('Delete confirmation modal must be rendered via portal to document.body');
}

if (!processingTrace.includes("stage === 'completed'") || !processingTrace.includes('return null')) {
  throw new Error('Processing trace must return null when completed to remove the trace from the DOM');
}

if (processingTrace.includes('onCancel') || processingTrace.includes('Dừng trả lời')) {
  throw new Error('Processing trace must not render a duplicate stop control');
}

if (!chatInterface.includes('abortControllerRef.current.abort()') || !chatInterface.includes('aria-label="Dừng trả lời"')) {
  throw new Error('Composer stop control must remain available');
}

if (chatInterface.includes('Tùy chọn') || chatInterface.includes('isComposerSettingsOpen')) {
  throw new Error('Composer must show inference controls directly, without a Tùy chọn gate');
}

if (!providerSelector.includes('Gemini 3.1 Flash-Lite')) {
  throw new Error('Composer must expose fixed Google AI Studio Gemini 3.1 Flash-Lite badge');
}

if (chatInterface.includes('AdvancedSettings') || chatInterface.includes('InferenceSetupModal')) {
  throw new Error('Composer must not include advanced tuning or setup modal components');
}

if (!emptyState.includes('Tra cứu pháp luật dễ dàng hơn')) {
  throw new Error('Empty state must use the legal search onboarding copy');
}

for (const forbidden of [
  'VietLaw BGE-M3',
  'đang embedding',
  'đang reranking',
  'đang gọi Qdrant',
  'chain-of-thought',
  'suy luận nội bộ',
  'retrieval score',
  'reranker score',
]) {
  const haystack = [processingTrace, emptyState, chatMessage].join('\n');
  if (haystack.includes(forbidden)) {
    throw new Error(`User-facing chat UI contains forbidden technical text: ${forbidden}`);
  }
}

// Verification: Icon-only toolbar and true regeneration
if (!chatMessage.includes('RotateCcw') || !chatMessage.includes('title="Tạo lại câu trả lời"')) {
  throw new Error('ChatMessage toolbar must have a Regenerate button with tooltip "Tạo lại câu trả lời"');
}

if (!chatMessage.includes('title="Câu trả lời hữu ích"') || !chatMessage.includes('title="Báo cáo câu trả lời chưa chuẩn"')) {
  throw new Error('ChatMessage toolbar must have Thumbs Up/Down buttons with Vietnamese tooltips');
}

if (!chatMessage.includes('Pencil') || !chatMessage.includes('title="Chỉnh sửa câu hỏi"')) {
  throw new Error('User message toolbar must have an edit prompt button with Pencil icon');
}

if (chatMessage.includes('<span>Giải thích lại</span>') || chatMessage.includes('<span>Sao chép</span>')) {
  throw new Error('Redundant text labels (Sao chép, Giải thích lại) must be removed for a clean icon-only toolbar');
}

if (!chatInterface.includes('handleRegenerate') || !chatInterface.includes('handleEditPrompt')) {
  throw new Error('ChatInterface must implement handleRegenerate and handleEditPrompt handlers');
}

if (!chatInterface.includes('onRegenerate={handleRegenerate}') || !chatInterface.includes('onEditPrompt={handleEditPrompt}')) {
  throw new Error('ChatInterface must pass onRegenerate and onEditPrompt callbacks to ChatMessage');
}

console.log('Chat UX verification passed.');
