import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const constants = readFileSync(resolve(process.cwd(), 'lib/constants.ts'), 'utf8');
const chatInterface = readFileSync(resolve(process.cwd(), 'components/chat/ChatInterface.tsx'), 'utf8');
const providerSelector = readFileSync(resolve(process.cwd(), 'components/chat/ProviderSelector.tsx'), 'utf8');

if (!constants.includes("DEFAULT_MODEL = 'gemini-3.1-flash-lite'")) {
  throw new Error('Default model must be fixed to gemini-3.1-flash-lite');
}

if (!providerSelector.includes('gemini-3.1-flash-lite') || !providerSelector.includes('Google AI Studio: Gemini 3.1 Flash-Lite')) {
  throw new Error('Provider selector must display fixed Google AI Studio Gemini 3.1 Flash-Lite');
}

if (chatInterface.includes('InferenceSetupModal') || chatInterface.includes('inferenceConfig:')) {
  throw new Error('ChatInterface must not include BYOK setup modal or client-side inferenceConfig');
}

console.log('Inference settings verification passed (server-authoritative fixed model).');
