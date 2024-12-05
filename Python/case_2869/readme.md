# Trigger Mode Acquisition Test
Test procedure to verify image acquisition functionality in trigger mode and ensure no frames are dropped.

## Purpose
Verify that the acquisition operates correctly in trigger mode and confirm there are no dropped frames during the test.

---

## Test Preparation

Connect a camera that supports Trigger Mode.

---

## Test Procedure

### Steps

1. **Open Frame Grabber**
   - Open the frame grabber device.

2. **Detect Camera**
   - Ensure the connected camera is detected by the frame grabber.

3. **Determine Frame Rate:**
   - Read the camera's maximum supported frame rate using:
     ```c
     FRAME_FPS = KYFG_GetCameraValueFloat("AcquisitionFrameRateMax") * 0.9;
     ```
   - Calculate the frame period to generate triggers:
     ```c
     FRAME_PERIOD_USEC = 1000000 / FRAME_FPS;
     ```

4. **Enable Camera Trigger Mode:**
   - Set the camera to trigger mode:
     ```c
     KYFG_SetCameraValueEnum_ByValueName("TriggerMode", "On");
     ```

5. **Configure Timer for Trigger Generation:**
   - Set the timer control parameters:
     ```c
     KYFG_SetGrabberValueEnum_ByValueName("TimerSelector", "Timer0");
     KYFG_SetGrabberValueEnum_ByValueName("TimerTriggerSource", "KY_DISABLED"); // Disable initially
     KYFG_SetGrabberValueFloat("TimerDelay", FRAME_PERIOD_USEC / 2); // Both delay and duration construct the full signal period
     KYFG_SetGrabberValueFloat("TimerDuration", FRAME_PERIOD_USEC / 2);
     ```

6. **Enable Camera Trigger:**
   - Configure the camera to respond to timer triggers:
     ```c
     KYFG_SetGrabberValueEnum_ByValueName("CameraTriggerSource", "KY_TIMER_ACTIVE_0");
     KYFG_SetGrabberValueEnum_ByValueName("CameraTriggerActivation", "AnyEdge");
     KYFG_SetGrabberValueEnum_ByValueName("CameraTriggerMode", "On");
     ```

7. **Start Acquisition and Trigger Generation:**
   - Begin camera acquisition and enable the timer:
     ```c
     KYFG_CameraStart();
     KYFG_SetGrabberValueEnum_ByValueName("TimerTriggerSource", "KY_CONTINUOUS");
     ```
	 
8. **Stop Acquisition and Trigger:**
   - After the test duration, stop the timer and acquisition:
     ```c
     KYFG_SetGrabberValueEnum_ByValueName("TimerTriggerSource", "KY_DISABLED");
     KYFG_CameraStop();
     ```

---

## Test Results Qualification

1. **Trigger FPS Validation:**
   - Ensure the acquired frame rate matches the calculated FPS:
     ```c
     KYFG_StreamGetInfo(KY_STREAM_INFO_INSTANTFPS) == FRAME_FPS // within a 0.1% error margin
     ```

2. **Frame Count Verification:**
   - Confirm the total frames match the expected count:
     ```c
     FRAMES_ACQUIRED == FRAME_FPS * <test_duration_in_seconds> // within a 1% error margin
     ```

3. **Dropped Frames Check:**
   - Verify no frames are dropped and triggers stopped successfully.

---

## Notes

- The test requires a stable environment and camera with precise trigger handling.  
- Any deviation beyond the error margins indicates potential misconfiguration or hardware limitations.
