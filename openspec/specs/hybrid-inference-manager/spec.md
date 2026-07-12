# Hybrid Inference Manager

## Purpose

This capability manages the fallback strategies and configuration for inference models (LLM, Embeddings, Reranking) to ensure fault tolerance by automatically switching between primary and fallback modes (remote and local).
## Requirements
### Requirement: Fallback Mode Configuration
The system SHALL support configuring a primary and secondary inference mode via the `INFERENCE_STRATEGY` environment variable (e.g., `remote_first`, `local_first`).

#### Scenario: Inference strategy initialization
- **WHEN** the backend application starts
- **THEN** it reads the `INFERENCE_STRATEGY` variable and prioritizes initialization of the respective Primary and Fallback model instances.

### Requirement: LLM Fallback Execution
The LLM integration (for rewriting, memory summarization, and answer generation) SHALL automatically fallback through the configured provider chain if the current provider throws a timeout, rate limit, authentication, or connection exception. When a runtime user provider/model is configured for a role, that runtime provider/model SHALL be used as the role's primary LLM before configured server fallbacks are considered. When Google final fallback is enabled and configured, the provider chain SHALL include Google AI Studio after the existing configured providers unless it duplicates the selected runtime provider/model.

#### Scenario: Primary LLM fails
- **WHEN** the primary LLM API throws an exception
- **THEN** the system catches the exception and immediately routes the prompt to the next fallback LLM instance.

#### Scenario: Runtime selected provider fails
- **WHEN** a role uses a user-selected runtime provider/model and that provider throws an exception
- **THEN** the system routes the same prompt to the next configured fallback provider when fallback is enabled.

#### Scenario: Existing providers fail with Google fallback configured
- **WHEN** both the HuggingFace-backed and Ollama-backed LLM instances fail
- **THEN** the system routes the same prompt to the configured Google AI Studio fallback model.

#### Scenario: Duplicate Google fallback model
- **WHEN** the selected model is already the same Google model as `GOOGLE_FALLBACK_MODEL`
- **THEN** the system MUST NOT retry the same Google model twice in the fallback chain.

#### Scenario: Deployed usage without local provider
- **WHEN** the deployed environment has no reachable local Ollama provider and a remote runtime provider is configured
- **THEN** answer generation, rewriting, and summarization can run without requiring Ollama.

### Requirement: Complete Inference Failure Handling
The system SHALL raise a clear HTTP error if every configured inference provider in the fallback chain fails sequentially.

#### Scenario: All configured LLM providers fail
- **WHEN** the final fallback model also throws an exception after all earlier providers have failed
- **THEN** the API returns an error response indicating that all inference providers are unavailable.

### Requirement: Google final fallback configuration
The system SHALL support an optional Google AI Studio final LLM fallback controlled by environment variables.

#### Scenario: Google fallback enabled with key
- **WHEN** `ENABLE_GOOGLE_FALLBACK` is `true` and `GOOGLE_API_KEY` is configured
- **THEN** the LLM fallback chain includes a Google AI Studio chat client using `GOOGLE_FALLBACK_MODEL`.

#### Scenario: Google fallback disabled
- **WHEN** `ENABLE_GOOGLE_FALLBACK` is `false`
- **THEN** the LLM fallback chain does not include a Google AI Studio chat client.

#### Scenario: Google API key missing
- **WHEN** `ENABLE_GOOGLE_FALLBACK` is `true` but `GOOGLE_API_KEY` is empty
- **THEN** the system skips Google fallback initialization and logs that Google fallback is unavailable.

### Requirement: Runtime provider credential handling
The LLM integration SHALL accept validated runtime provider credentials for supported providers and use them only for the current request workflow.

#### Scenario: Runtime credential overrides environment key
- **WHEN** a chat request includes a valid runtime API key for the selected provider
- **THEN** the LLM client for that provider uses the runtime API key for that request.

#### Scenario: Runtime credential is missing
- **WHEN** a selected runtime provider requires an API key and neither a runtime key nor an environment fallback key is available
- **THEN** the backend returns a clear provider setup error or falls back according to the configured fallback policy.

#### Scenario: Runtime credential is redacted
- **WHEN** the backend logs provider routing or reports an inference error
- **THEN** the provider API key value MUST be redacted.

