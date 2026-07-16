import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = process.cwd();
const chatInterface = readFileSync(resolve(root, 'components/chat/ChatInterface.tsx'), 'utf8');
const chatMessage = readFileSync(resolve(root, 'components/chat/ChatMessage.tsx'), 'utf8');
const processingTrace = readFileSync(resolve(root, 'components/chat/ChatProcessingTrace.tsx'), 'utf8');
const legalSources = readFileSync(resolve(root, 'components/chat/LegalSources.tsx'), 'utf8');
const emptyState = readFileSync(resolve(root, 'components/chat/ChatEmptyState.tsx'), 'utf8');
const proxyRoute = readFileSync(resolve(root, 'app/api/chat/route.ts'), 'utf8');

for (const label of [
  'Đang phân tích câu hỏi',
  'Đang tra cứu căn cứ pháp lý',
  'Đang chọn lọc thông tin phù hợp',
  'Đang tổng hợp câu trả lời',
  'Tra cứu hoàn tất',
  'Dừng trả lời',
]) {
  if (!processingTrace.includes(label)) {
    throw new Error(`Missing processing label: ${label}`);
  }
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

if (!chatMessage.includes('LegalSources') || !legalSources.includes('Căn cứ pháp lý')) {
  throw new Error('Assistant messages must render legal sources with the dedicated component');
}

if (legalSources.includes('contextUsed.length') || legalSources.includes('retrieval score') || legalSources.includes('reranker score')) {
  throw new Error('Legal sources UI must not expose counts or scores');
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
  const haystack = [processingTrace, legalSources, emptyState, chatMessage].join('\n');
  if (haystack.includes(forbidden)) {
    throw new Error(`User-facing chat UI contains forbidden technical text: ${forbidden}`);
  }
}

console.log('Chat UX verification passed.');
