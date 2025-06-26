# Test case #3396: Acquisition on 2 and more cameras using trigger mode

This test case verifies the simultaneous triggering of two connected cameras using a configured timer on the frame grabber side.

---

## Test Steps

### Initialization
- Open frame grabber
- Detect all connected cameras
- Open all detected cameras

---

### Grabber Preparation
- TimerSelector = Timer0
- FrameTime = 1e+6 / ExpectedFPS
- TimerDelay = FrameTime / 2
- TimerDuration = FrameTime / 2
- TimerTriggerSource = 0 (Disabled)

### Camera grabber preparation:
- CameraSelector = camera index
- CameraTriggerMode = 1
- CameraTriggerActivation = AnyEdge
- CameraTriggerSource = KY_TIMER_ACTIVE_0

### Camera preparation:
- TriggerMode = 1
- TriggerSource = LinkTrigger0
- ExposureTime = 5000.0

### Streaming and logging:
- Register callback function
- In callback, retrieve and save timestamp
- Start stream
- Start trigger generation
- Stop stream and trigger generation
- Print frame counter and drop frame counter
- Compare and print acquired frame timestamps
- Close grabber
