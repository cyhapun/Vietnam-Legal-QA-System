## ADDED Requirements

### Requirement: Session Metadata Startup
The system SHALL fetch only chat session metadata (id, title, timestamp, message_count) during application startup. The system SHALL NOT fetch messages for any historical session on startup. It MUST initialize a new empty chat state without immediately rendering a placeholder session in the historical list. The new session SHALL only be persisted to the sidebar list once a message is generated.

#### Scenario: User opens the application
- **WHEN** the application mounts and fetches `/api/chat/sessions`
- **THEN** it does NOT automatically fetch messages for any historical session
- **AND** it sets the active session to a new empty state, leaving the historical list exactly as returned by the server.

### Requirement: Lazy Loading Chat Messages
The system SHALL fetch messages for historical sessions on-demand when the user selects them, rather than preemptively.

#### Scenario: User clicks an unloaded session
- **WHEN** the user selects a session in the sidebar whose messages have not yet been loaded
- **THEN** the system sets a loading state and makes a single API request to `/api/chat/session/[id]/messages`.

#### Scenario: User clicks an already loaded session
- **WHEN** the user selects a session in the sidebar whose messages were previously loaded in this browser session
- **THEN** the system instantly displays the cached messages without making a redundant API request.

### Requirement: Chat Skeleton Loader
The system SHALL display a skeleton loading UI in the main chat interface while a newly selected session's messages are being fetched from the server.

#### Scenario: Session messages are loading
- **WHEN** the `isSessionLoading` state is active
- **THEN** the main chat window displays placeholder visual elements (skeletons) representing generic user and assistant message bubbles.

### Requirement: Session list includes message count
API `GET /chat/sessions` SHALL trả về danh sách sessions trong đó mỗi session object PHẢI bao gồm trường `message_count` kiểu integer biểu thị số lượng messages thuộc session đó. Trường này PHẢI được tính toán server-side thông qua SQL COUNT, không phải client-side.

#### Scenario: Sessions returned with message count
- **WHEN** client gọi `GET /chat/sessions`
- **THEN** mỗi object trong mảng kết quả có trường `message_count` kiểu số nguyên không âm

#### Scenario: Empty session has zero message count
- **WHEN** session tồn tại trong `chat_sessions` nhưng không có rows nào trong `chat_messages`
- **THEN** `message_count` = 0 cho session đó

#### Scenario: Frontend filters empty sessions from sidebar
- **WHEN** `useChatSessions` nhận danh sách sessions từ API
- **THEN** chỉ những session có `message_count > 0` HOẶC là `currentSessionId` hiện tại mới được hiển thị trong sidebar
