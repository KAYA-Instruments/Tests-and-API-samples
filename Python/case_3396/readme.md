# Test case #3396: Multi-camera synchronization using grabber timer trigger

This test case verifies the simultaneous triggering of two connected cameras using a configured timer on the frame grabber side.

## Test Steps
1. Scan and select the grabber.
2. Verify at least two cameras are connected.
3. Open the grabber and configure Timer0 for periodic triggering based on `--expectedFPS`.
4. For each camera:
   - Open and validate trigger control support.
   - Configure grabber and camera trigger settings.
   - Set exposure time to 90% of the frame interval.
   - Allocate streaming buffers.
   - Register a callback for timestamp collection.
   - Start streaming.
5. Enable continuous timer trigger on the grabber.
6. Let the cameras stream for `--streamDuration` seconds.
7. Disable the timer and stop all streams.
8. Collect and print RX/drop frame statistics for each camera.
9. Unregister callbacks, release streams, and close devices.
10. Compare per-frame timestamps between the cameras if needed.

## Expected Result
- Compare RX counters and callbacks, verify no dropped frames.
- The difference between timestamps from both cameras is calculated.