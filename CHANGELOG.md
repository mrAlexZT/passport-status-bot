# 0.2.1
- Added `/authors` command with detailed information about:
  - Project authors and contributors
  - Contact information and social links
  - Project details and technical stack
  - Improved formatting and organization
- Added "Command not found" handler with helpful `/help` suggestion
- Added proper error logging for notification sending
- Improved version handling with better error messages
- Fixed Markdown formatting in various messages

# 0.2.0
- Added admin commands and improvements:
  - `/users` - List all users and their subscriptions with detailed statistics
  - `/cleanup` - Remove invalid data from database with interactive confirmation
  - Added inline buttons for safer database operations
  - Added multi-stage data validation and progress tracking
  - Improved admin permission checks for both commands and callbacks

- Database improvements:
  - Added cleanup for users without telegram_id
  - Added cleanup for users with invalid session_id
  - Added cleanup for subscriptions without telegram_id
  - Added cleanup for subscriptions without session_id
  - Added cleanup for orphaned subscriptions
  - Added data integrity validation
  - Added statistics tracking for invalid records

- User Interface improvements:
  - Added progress indicators for long operations:
    - "🔍 Аналіз бази даних..."
    - "⏳ Аналіз даних..."
    - "🗑 Видалення даних..."
  - Added detailed statistics in user lists
  - Added confirmation buttons with clear actions
  - Added operation cancellation support
  - Added Markdown formatting for better readability
  - Added proper error messages with emoji indicators

- Error handling and safety:
  - Added stale data detection
  - Added operation cancellation support
  - Added safe message editing with fallbacks
  - Added detailed error logging
  - Added validation before destructive operations
  - Added proper error messages for all failure cases
  - Added permission checks at multiple stages

- Code quality improvements:
  - Centralized all message constants
  - Split large functions into smaller, focused ones
  - Added proper type hints and validation
  - Improved function documentation
  - Added consistent error handling patterns
  - Added unified logging format
  - Added reusable utility functions:
    - Message editing utilities
    - Permission checking utilities
    - Data validation utilities
    - Progress tracking utilities

# 0.1.2
- Added `/dump` `/time` `/ping` commands to the commands of the bot.
- Added `/version` command and versioning of the bot.
# 0.1.1
- Added rate limit
- Added subscription on many applications via 1 command
![Subscriptions](assets/many_subs.gif)

- New `/dump` command which dumps all data from DB about subscriptions and applications
![Dump](assets/dump.gif)

# 0.1.0
- Added QR-code scanner:

![QR-code scanner](assets/qr_scanner.gif)
