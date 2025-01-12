# Multiple time-synced GPIO triggers


## Purpose
Verify there are no drop frames while using GPIO triggers set up to receive time-synced frames from the cameras.
---

## Test Preparation

Connect at least 2 cameras with Trigger Mode support.
Connect GPIO cable to the frame grabber.

---
# GPIO Trigger Test Procedure

This document outlines the steps to verify GPIO-based triggering and frame acquisition functionality on a frame grabber.

---

## Test Procedure

### Steps

1. **Initialize Frame Grabber:**
   - Open the frame grabber.
   - Detect all connected cameras.

2. **Configure GPIO Output:**
   - Set the following parameters:
     ```c
     LineSelector = KY_TTL_0;
     LineMode = Output;
     LineSource = KY_USER_OUT_0;
     ```

3. **Retrieve Camera List:**
   - Get the list of connected cameras.

4. **Configure Each Camera:**
   - For each camera in the list, set the following:
     ```c
     CameraTriggerMode = On;
     CameraTriggerActivation = AnyEdge;
     CameraTriggerSource = KY_TTL_0;
     ```

5. **Trigger Loop Execution:**
   - Perform a loop for the required `number_of_frames`:
     1. Turn on GPIO output:
        ```c
        UserOutputValue = KYTRUE;
        ```
     2. For each camera in the list:
        - Turn on trigger mode:
          - Trigger activation: Rising Edge
          - Trigger source:
            - Use `CameraTrigger` for Chameleon cameras.
            - Use `LinkTrigger0` for Iron cameras.
        - Start acquisition and capture a frame.
     3. Switch off GPIO output:
        ```c
        UserOutputValue = KYFALSE;
        ```

## Parametrization

--number_of_frames 100

E.g. 100 frames.

---

## Test Pass Criteria

1. The test passes if:
   - The number of frames received matches the `number_of_frames` parameter for **all cameras**.
2. Any discrepancy indicates a failure or misconfiguration.

--


## Notes

- Ensure proper synchronization of GPIO signals and camera configuration.  
- Verify hardware compatibility with the test requirements before execution.
- The test requires a stable environment and camera with precise trigger handling.  
- Any deviation beyond the error margins indicates potential misconfiguration or hardware limitations.
