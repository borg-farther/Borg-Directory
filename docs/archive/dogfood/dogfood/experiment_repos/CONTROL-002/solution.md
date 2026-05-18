# Solution for CONTROL-002

## Task
Rename all files in `src/` from camelCase to snake_case.

## Expected Renamed Files
| Original (camelCase) | New (snake_case) |
|---------------------|------------------|
| userAuth.py | user_auth.py |
| databaseConnection.py | database_connection.py |
| requestHandler.py | request_handler.py |
| sessionState.py | session_state.py |
| dataValidator.py | data_validator.py |
| cacheManager.py | cache_manager.py |
| apiClient.py | api_client.py |
| loggerConfig.py | logger_config.py |
| messageQueue.py | message_queue.py |
| fileUploadHandler.py | file_upload_handler.py |

## Solution
```bash
cd src/
mv userAuth.py user_auth.py
mv databaseConnection.py database_connection.py
mv requestHandler.py request_handler.py
mv sessionState.py session_state.py
mv dataValidator.py data_validator.py
mv cacheManager.py cache_manager.py
mv apiClient.py api_client.py
mv loggerConfig.py logger_config.py
mv messageQueue.py message_queue.py
mv fileUploadHandler.py file_upload_handler.py
```

Also need to update the import statements inside the files to use snake_case module names.
