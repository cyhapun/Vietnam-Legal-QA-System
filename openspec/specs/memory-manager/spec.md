# Memory Manager

## Purpose
TBD: The conversational memory manager reduces LLM context window bloat and latency by maintaining a compressed session summary in PostgreSQL and fetching it on-the-fly, rather than passing raw interaction histories to the RAG LLM.
## Requirements
### Requirement: Session Summary Storage
The system SHALL store and update a summary of the conversation context for a given `session_id`.

#### Scenario: New session
- **WHEN** a chat interaction occurs for a new session_id
- **THEN** a new chat session record is implicitly tracked or created with an empty summary

#### Scenario: Updating summary
- **WHEN** a background task finishes generating a new summary for a session
- **THEN** the system updates the `summary` and `turn_count` tracking for that session in the storage backend

### Requirement: Sliding Window Context Construction
The system SHALL combine the stored session summary with a sliding window of the most recent messages to form the prompt.

#### Scenario: Summarized context injection
- **WHEN** the chat endpoint receives a prompt request for a session with multiple previous turns
- **THEN** it retrieves the summary from the database and prefixes the chat history string with the summary, followed by the verbatim last N messages

### Requirement: Asynchronous Summarizer Task
The system SHALL automatically summarize past conversation history asynchronously without blocking the user response. When a runtime summarizer provider/model is configured in the chat request, the summarizer SHALL use that runtime role configuration for the background summarization task.

#### Scenario: Triggering summarization
- **WHEN** the streaming generation finishes or a non-streaming endpoint completes
- **THEN** an async background task is launched to invoke a lightweight LLM to summarize the newly appended messages into the existing summary

#### Scenario: Runtime summarizer role is configured
- **WHEN** a chat request includes a valid runtime provider/model for the summarizer role and memory is enabled
- **THEN** the background summarizer uses the configured summarizer role model for that request.

#### Scenario: Summarizer role is unavailable
- **WHEN** memory is enabled but no summarizer role can be created from runtime or server fallback configuration
- **THEN** the system logs a non-secret warning and skips summary update without failing the user response.

