import pytest
import os
import time
import threading
from unittest.mock import MagicMock, patch

from run_loop import run_loop # Assuming run_loop.py is in the root or PYTHONPATH

# Fixture to provide a stop event for tests
@pytest.fixture
def stop_event():
    return threading.Event()

# Fixture to mock environment variables
@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("ZOOM_TOKEN", "test_zoom_token")
    monkeypatch.setenv("MEETING_ID", "test_meeting_id")

def test_run_loop_successful_execution(stop_event, mock_env_vars, mocker):
    """
    Test normal execution: MeetingRecorder is initialized, started, and stopped.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_class = mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    
    device_name = "test_device"

    # Run run_loop in a separate thread so we can stop it
    loop_thread = threading.Thread(target=run_loop, args=(device_name, stop_event))
    loop_thread.start()

    # Give some time for the loop to start and recorder to be initialized
    time.sleep(0.2) 
    stop_event.set() # Signal the loop to stop
    loop_thread.join(timeout=2) # Wait for the thread to finish

    assert not loop_thread.is_alive(), "run_loop thread did not terminate"

    mock_recorder_class.assert_called_once_with(device_name=device_name)
    assert mock_recorder_instance.on_poll_created is not None, "on_poll_created callback was not set"
    mock_recorder_instance.start_recording.assert_called_once()
    mock_recorder_instance.stop_recording.assert_called_once()
    mock_recorder_instance.close.assert_called_once()

def test_run_loop_stop_event_handling(stop_event, mock_env_vars, mocker):
    """
    Test that setting the stop_event gracefully terminates the loop and cleans up.
    This is largely covered by test_run_loop_successful_execution, but explicitly tested.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_class = mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    device_name = "test_device_stop_event"

    # Set the event before starting the loop (or very quickly after)
    # For this test, let's set it quickly after to ensure the loop runs at least once
    
    def run_and_stop():
        run_loop(device_name, stop_event)

    loop_thread = threading.Thread(target=run_and_stop)
    loop_thread.start()
    
    time.sleep(0.1) # Allow run_loop to start MeetingRecorder
    assert mock_recorder_instance.start_recording.called, "MeetingRecorder start_recording was not called"
    
    stop_event.set()
    loop_thread.join(timeout=2)

    assert not loop_thread.is_alive(), "run_loop thread did not terminate after stop_event"
    mock_recorder_instance.stop_recording.assert_called_once()
    mock_recorder_instance.close.assert_called_once()


def test_run_loop_exception_during_recorder_start(stop_event, mock_env_vars, mocker, caplog):
    """
    Test how run_loop handles an exception when MeetingRecorder.start_recording fails.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_instance.start_recording.side_effect = Exception("Failed to start recording")
    mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    
    device_name = "test_device_start_fail"

    run_loop(device_name, stop_event) # Run directly, no thread needed as it should exit

    assert "Failed to start MeetingRecorder" in caplog.text # Check logs for error
    # Depending on implementation, stop_recording/close might still be called in a finally block
    # In current run_loop.py, if start_recording fails, it returns, and finally block calls stop/close.
    mock_recorder_instance.stop_recording.assert_called_once() 
    mock_recorder_instance.close.assert_called_once()


def test_run_loop_missing_env_vars(stop_event, mocker, monkeypatch, caplog):
    """
    Test run_loop behavior when essential environment variables are missing.
    """
    # Ensure one of the critical env vars is missing
    monkeypatch.delenv("ZOOM_TOKEN", raising=False)
    
    mock_recorder_class = mocker.patch('run_loop.MeetingRecorder') # Patch to check calls
    
    device_name = "test_device_no_env"
    run_loop(device_name, stop_event)

    assert "Missing ZOOM_TOKEN or MEETING_ID" in caplog.text
    mock_recorder_class.assert_not_called() # MeetingRecorder should not be initialized

def test_run_loop_recorder_init_fails(stop_event, mock_env_vars, mocker, caplog):
    """
    Test run_loop behavior when MeetingRecorder initialization fails.
    """
    mocker.patch('run_loop.MeetingRecorder', side_effect=ValueError("Device init error"))
    
    device_name = "test_device_init_fail"
    run_loop(device_name, stop_event)

    assert "ValueError during MeetingRecorder initialization" in caplog.text
    assert "Device init error" in caplog.text
    # Ensure stop_recording or close are not called on the class if __init__ failed
    # (since no instance would be successfully created and assigned to `recorder`)

def test_run_loop_poll_callback_fires(stop_event, mock_env_vars, mocker, caplog):
    """
    Test that the on_poll_created callback is set and can be (theoretically) called.
    Also tests the poll posting logic within the callback.
    """
    mock_recorder_instance = MagicMock()
    # Simulate the on_poll_created attribute being set
    mock_recorder_instance.on_poll_created = None 
    mock_recorder_class = mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    
    # Mock the post_poll_to_zoom function that the callback will call
    mock_post_poll = mocker.patch('run_loop.post_poll_to_zoom', return_value=True)
    
    device_name = "test_device_callback"

    # --- Simulate run_loop execution flow ---
    run_loop(device_name, stop_event) # Call run_loop to set the callback

    # Assert the callback was set
    assert mock_recorder_instance.on_poll_created is not None
    
    # --- Directly invoke the assigned callback to test its internal logic ---
    # This is more of a unit test for the callback itself once assigned.
    sample_poll_data = {'title': 'CB Test Poll', 'question': 'Q?', 'options': ['A', 'B']}
    
    # Check if on_poll_created is callable (it should be after run_loop assigns it)
    if callable(mock_recorder_instance.on_poll_created):
        mock_recorder_instance.on_poll_created(sample_poll_data)
    else:
        pytest.fail("on_poll_created was not set as a callable by run_loop")

    # Assert that post_poll_to_zoom was called by the callback
    mock_post_poll.assert_called_once_with(
        title='CB Test Poll',
        question='Q?',
        options=['A', 'B'],
        meeting_id="test_meeting_id", # from mock_env_vars
        token="test_zoom_token"       # from mock_env_vars
    )
    assert "Poll 'CB Test Poll' posted to Zoom successfully." in caplog.text

def test_run_loop_poll_callback_post_fails(stop_event, mock_env_vars, mocker, caplog):
    """
    Test the poll callback's error handling when post_poll_to_zoom fails.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_instance.on_poll_created = None
    mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    mock_post_poll = mocker.patch('run_loop.post_poll_to_zoom', return_value=False) # Simulate failure
    
    device_name = "test_device_callback_fail"
    run_loop(device_name, stop_event) # Sets the callback

    assert mock_recorder_instance.on_poll_created is not None
    
    sample_poll_data = {'title': 'CB Fail Poll', 'question': 'Q Fail?', 'options': ['X', 'Y']}
    if callable(mock_recorder_instance.on_poll_created):
        mock_recorder_instance.on_poll_created(sample_poll_data)
    else:
        pytest.fail("on_poll_created was not set as a callable by run_loop")

    mock_post_poll.assert_called_once()
    assert "Failed to post poll 'CB Fail Poll' to Zoom." in caplog.text

def test_run_loop_poll_callback_post_exception(stop_event, mock_env_vars, mocker, caplog):
    """
    Test the poll callback's error handling when post_poll_to_zoom raises an exception.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_instance.on_poll_created = None
    mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    # Simulate post_poll_to_zoom raising an exception
    mock_post_poll = mocker.patch('run_loop.post_poll_to_zoom', side_effect=Exception("Zoom API Error"))
    
    device_name = "test_device_callback_exception"
    run_loop(device_name, stop_event) # Sets the callback

    assert mock_recorder_instance.on_poll_created is not None
    
    sample_poll_data = {'title': 'CB Exception Poll', 'question': 'Q Ex?', 'options': ['E1', 'E2']}
    if callable(mock_recorder_instance.on_poll_created):
        mock_recorder_instance.on_poll_created(sample_poll_data)
    else:
        pytest.fail("on_poll_created was not set as a callable by run_loop")

    mock_post_poll.assert_called_once()
    assert "Error posting poll 'CB Exception Poll': Zoom API Error" in caplog.text

# Note: To run these tests, ensure pytest, pytest-mock, and pytest-cov are installed.
# You might need to adjust import paths based on your project structure.
# Example: `python -m pytest tests/test_run_loop.py`
# If run_loop.py is not in the root, you might need to add `sys.path.insert(0, 'path/to/your/src')`
# or configure PYTHONPATH.
# The `caplog` fixture is used to capture log output.
# The `mocker` fixture is from pytest-mock.
# The `monkeypatch` fixture is a built-in pytest fixture.
# The `stop_event` and `mock_env_vars` are custom fixtures defined above.
# The test `test_run_loop_successful_execution` uses a thread because run_loop has an infinite loop
# that only breaks when stop_event is set.
# The test `test_run_loop_stop_event_handling` further verifies this stop mechanism.
# Other tests might not need threading if the tested condition leads to run_loop exiting early.
# The `caplog.text` will contain all log messages captured during the test.
# Ensure `MeetingRecorder` methods like `start_recording`, `stop_recording`, `close` are mockable.
# If `post_poll_to_zoom` is in a different module, `mocker.patch` path should be adjusted.
# E.g. if `run_loop.py` has `from poller import post_poll_to_zoom`, then patch `'run_loop.post_poll_to_zoom'`.
# If `run_loop.py` has `import poller; poller.post_poll_to_zoom()`, then patch `'run_loop.poller.post_poll_to_zoom'`.
# Based on run_loop.py, it's `from poller import post_poll_to_zoom`, so `'run_loop.post_poll_to_zoom'` is correct.

# Added a simple test to ensure MeetingRecorder.start_recording returning False is handled
def test_run_loop_recorder_start_returns_false(stop_event, mock_env_vars, mocker, caplog):
    """
    Test how run_loop handles MeetingRecorder.start_recording() returning False.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_instance.start_recording.return_value = False # Simulate start_recording returning False
    mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    
    device_name = "test_device_start_false"

    run_loop(device_name, stop_event)

    assert "Failed to start MeetingRecorder. Exiting run_loop." in caplog.text
    # If start_recording returns False, the 'finally' block in run_loop should still execute.
    mock_recorder_instance.stop_recording.assert_called_once()
    mock_recorder_instance.close.assert_called_once()

# Test for the main execution path where run_loop keeps running until stop_event is set
def test_run_loop_main_loop_runs_and_stops(stop_event, mock_env_vars, mocker):
    """
    Test that the main while loop in run_loop runs and checks stop_event.
    """
    mock_recorder_instance = MagicMock()
    mock_recorder_class = mocker.patch('run_loop.MeetingRecorder', return_value=mock_recorder_instance)
    
    device_name = "test_device_main_loop"

    # Use a flag that can be checked by the thread
    # to see if the inner while loop has been entered.
    # This is a bit tricky as time.sleep(1) is inside the loop.
    # We can mock time.sleep to control the loop's execution speed for the test.
    
    entered_loop_flag = threading.Event()

    def target_run_loop():
        # Mock time.sleep inside the thread to signal loop entry and speed up exit
        with patch('time.sleep', side_effect=lambda s: (entered_loop_flag.set(), time.sleep(0.01)) if s == 1 else time.sleep(s)):
            run_loop(device_name, stop_event)

    loop_thread = threading.Thread(target=target_run_loop)
    loop_thread.start()

    # Wait for the flag to be set, indicating the while loop has started
    flag_set = entered_loop_flag.wait(timeout=1) # Wait up to 1 sec for the loop to start
    assert flag_set, "run_loop did not enter its main while loop"

    # Now signal the loop to stop
    stop_event.set()
    loop_thread.join(timeout=2)

    assert not loop_thread.is_alive(), "run_loop thread did not terminate"
    mock_recorder_class.assert_called_once_with(device_name=device_name)
    mock_recorder_instance.start_recording.assert_called_once()
    mock_recorder_instance.stop_recording.assert_called_once()
    mock_recorder_instance.close.assert_called_once()
