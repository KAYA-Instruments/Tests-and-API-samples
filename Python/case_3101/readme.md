# Test case #3101: Linux: Verify no pipe descriptor leaks during repeated camera start/stop

This test ensures that camera start/stop operations on Linux do not leak pipe file descriptors over time.

## Test Steps
1. Scan and select the grabber.
2. Ensure the platform is Linux; otherwise, exit.
3. Open the selected grabber and retrieve device information.
4. Connect and open a camera.
5. Create a stream and register a buffer callback.
6. Allocate and announce a number of stream buffers.
7. Measure the number of open pipes before camera streaming.
8. Repeat camera start/stop operations in a loop (`--number_of_tests` times).
9. Measure the number of open pipes after all iterations.
10. Unregister callbacks, delete the stream, close the camera and grabber.

## Actual Result
The number of open pipes after the streaming loop does not change, confirming no pipe leak.

## Expected Result
Pipe count before and after camera streaming must match:
QTY of pipes at the start: N
QTY of pipes at the stop: N
If they differ, the test fails with an assertion error.
