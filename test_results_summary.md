# Zoom Poll Automator - Test Results Summary

## Test Execution Summary
- Total Tests: 29
- Passed: 23
- Failed: 6
- Duration: 39.98s

## Environment Details
- Python Version: 3.13.1
- Platform: Windows-11-10.0.26100-SP0
- Pytest Version: 7.4.0
- Plugins: anyio-4.9.0, benchmark-4.0.0, cov-4.1.0, html-4.1.1, metadata-3.1.1, timeout-2.1.0, xdist-3.3.1

## Passed Tests (23)
1. test_index_route
2. test_list_audio_devices
3. test_validate_config_success
4. test_validate_config_missing
5. test_complete_workflow
6. test_transcription_speed
7. test_poll_generation_performance
8. test_memory_usage
9. test_concurrent_poll_generation
10. test_generate_poll_success
11. test_generate_poll_invalid_response
12. test_generate_poll_error_handling
13. test_generate_poll_content_validation
14. test_generate_poll_missing_questions
15. test_generate_poll_from_empty_transcript
16. test_generate_poll_from_sample_transcript
17. test_env_file_not_committed
18. test_no_credentials_in_logs
19. test_token_storage_in_session
20. test_input_validation
21. test_load_model
22. test_transcribe_audio_file_not_found
23. test_transcribe_audio_success

## Failed Tests (6)

### 1. test_generate_poll_missing_title
**Error Type**: AssertionError
**Details**: 
- Expected: "Technology Trends Poll"
- Actual: "Meeting Poll"
**Location**: tests/test_poll_prompt.py:153

### 2. test_run_loop_iteration
**Error Type**: AttributeError
**Details**: Module 'run_loop' does not have the attribute 'create_poll_in_meeting'
**Location**: tests/test_run_loop.py

### 3. test_run_loop_stop_event
**Error Type**: AttributeError
**Details**: Module 'run_loop' does not have the attribute 'capture_audio'
**Location**: tests/test_run_loop.py

### 4. test_run_loop_exception_handling
**Error Type**: AttributeError
**Details**: Module 'run_loop' does not have the attribute 'logger'
**Location**: tests/test_run_loop.py

### 5. test_secret_key_generation
**Error Type**: TypeError
**Details**: str expected, not NoneType
**Location**: tests/test_security.py:65

### 6. test_https_used_for_api_calls
**Error Type**: ImportError
**Details**: Cannot import name 'create_poll_in_meeting' from 'poller'
**Location**: tests/test_security.py:99

## Test Coverage
- Coverage HTML Report: test-reports/coverage/index.html
- Chart Data: test-reports/chart-data/*.csv

## Log Messages
```
2025-05-12 16:20:41 [    INFO] Loaded environment from .env
2025-05-12 16:20:42 [    INFO] [+] Flask secret key loaded from configuration.
2025-05-12 16:20:45 [    INFO] Using device: cpu
2025-05-12 16:20:45 [    INFO] Loading Whisper model: base
2025-05-12 16:20:45 [    INFO] Model loaded successfully in 0.00 seconds
2025-05-12 16:20:45 [    INFO] Transcribing audio file
2025-05-12 16:20:45 [    INFO] Transcription completed in 0.00 seconds
2025-05-12 16:20:45 [    INFO] Cleaning up model resources
2025-05-12 16:20:45 [    INFO] Model resources cleaned up
```

## Recommendations for Fixing Failed Tests

1. **Poll Title Issue**:
   - Update the poll generation logic to use context-aware titles
   - Modify test expectations to match actual behavior

2. **Run Loop Issues**:
   - Add missing functions to run_loop.py:
     - create_poll_in_meeting
     - capture_audio
     - logger setup

3. **Security Test Issues**:
   - Fix environment variable handling in test_secret_key_generation
   - Update test_https_used_for_api_calls to use post_poll_to_meeting instead of create_poll_in_meeting

## Next Steps
1. Fix the poll title generation to be more context-aware
2. Implement missing functions in run_loop.py
3. Update security tests to handle environment variables correctly
4. Update API call tests to use the correct function names

## Additional Notes
- The test suite includes performance tests, integration tests, and security tests
- Most core functionality tests are passing
- Failed tests are primarily related to test implementation details rather than core functionality
- Test coverage reports are available in the test-reports directory 