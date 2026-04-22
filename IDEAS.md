# Ideas & Tasks

## Backlog

### `get_catchup` tool — network/catch-up group
Add filtering by event type to the existing `get_catchup` tool:
- [ ] Job changes
- [x] Birthdays — returns `{name, profile_url, birthday (0000-MM-DD), birthday_text, original_text, retrieved_at}`
- [ ] Work anniversaries
- [ ] Education updates

**Birthday tracking idea:** since LinkedIn only shows birthdays on the day (or week) they occur, visit the catch-up page regularly (daily or weekly) and accumulate birthday → date-of-birth mappings for connected people over time, building a local cache.
