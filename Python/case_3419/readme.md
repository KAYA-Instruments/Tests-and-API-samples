# GPIO Trigger Test for Image Acquisition
This test case outlines the process to test image acquisition using GPIO triggers on a frame grabber. To use this test case there is a GPIO loopback card should be inserted that redirects an output lines to an input lines.

## Purpose
Verify that the frame grabber can acquire images correctly using GPIO triggers.

---

## Test Procedure

### Steps

1. **Open Frame Grabber**
   - Open the frame grabber device.

2. **Detect Camera**
   - Ensure the connected camera is detected by the frame grabber.

3. **Configure Grabber Settings**
   - **Output Line Setting:**
     - `LineSelector` = Output Line  
     - `LineMode` = Output  
     - `LineInverter` = False  
     - `LineEventMode` = Disabled  
   - **Input Line Setting:**
     - `LineSelector` = Input Line  
     - `LineMode` = Input  
     - `LineInverter` = False  
     - `LineSource` = Disabled  
   - **Timer Setting**
     - `TimerSelector` = `Timer0`
	 - `Delay = Duration = 1e6 / expectedFPS / 2`  
	 - `TimerTriggerSource` = Disabled  

4. **For Each Camera:**
   - **Camera Trigger Settings:**
     - `TriggerMode` = ON  
     - `TriggerActivation` = Rising Edge  
     - `TriggerSource` = `LinkTrigger0` or `KY_CAM_TRIG` (for Iron and Chameleon)  
   - **Grabber Camera Settings:**
     - `CameraSelector` = Camera Index  
     - `CameraTriggerMode` = ON
     - `CameraTriggerActivation` = `Any Edge`
     - `CameraTriggerSource` = Input Line  
     - `CameraTriggerFilter` = 1.0  

6. **Stream and Trigger:**
   - Create a stream and start the camera.  
   - Start trigger generation: `TimerTriggerSource` = KY_CONTINUOUS.  
   - Wait for the test duration.  
   - Stop trigger generation: `TimerTriggerSource` = KY_DISABLED.  

7. **Stop and Close:**
   - Stop the stream.  
   - Close the frame grabber.

---

## Pass Criteria

- **Frame Counter Validation:**  
  - `FrameCounter` = `expectedFPS` * `Duration` (±1%)

---

## Configuration

{
"pytest_parametrize":
[
"--outputLine KY_TTL_0 --inputLine KY_TTL_2 --expectedFPS 40 --duration 10",
"--outputLine KY_TTL_1 --inputLine KY_TTL_3 --expectedFPS 40 --duration 10",
"--outputLine KY_LVTTL_0 --inputLine KY_LVTTL_1 --expectedFPS 40 --duration 10",
"--outputLine KY_LVTTL_2 --inputLine KY_LVTTL_3 --expectedFPS 40 --duration 10",
"--outputLine KY_LVDS_OUT_0 --inputLine KY_LVDS_IN_0 --expectedFPS 40 --duration 10",
"--outputLine KY_LVDS_OUT_1 --inputLine KY_LVDS_IN_1 --expectedFPS 40 --duration 10",
"--outputLine KY_OPTO_OUT_0 --inputLine KY_OPTO_IN_0 --expectedFPS 40 --duration 10",
"--outputLine KY_OPTO_OUT_1 --inputLine KY_OPTO_IN_1 --expectedFPS 40 --duration 10",
"--outputLine KY_OPTO_OUT_2 --inputLine KY_OPTO_IN_2 --expectedFPS 40 --duration 10",
"--outputLine KY_OPTO_OUT_3 --inputLine KY_OPTO_IN_3 --expectedFPS 40 --duration 10"
]
}
