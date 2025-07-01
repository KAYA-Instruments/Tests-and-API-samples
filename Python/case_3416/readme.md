# GPIO Trigger Test

## Test Purpose
Verify that GPIO triggers function correctly via AUX callbacks.

## Requirements
- Setup GPIO trigger cable to the grabber and power it using USB
- Connect at least one camera

##  Automation Steps

1. Open grabber  
2. Detect and open one camera  
3. Register AUX callback function  
4. **First Line Configuration**
   - `LineSelector = outputLine`
   - `LineMode = Output`
   - `LineInverter = False`
   - `LineSource = Timer0`
   - `LineEventMode = Disabled`
5. **Second Line Configuration (loopBack scheme)**
   - `LineSelector = inputLine`
   - `LineMode = Input`
   - `LineSource = Disabled`
   - `LineInverter = False`
   - `LineEventMode = Disabled`
6. **Timer Settings**
   - `TimerSelector = 0`
   - `TimerDelay = TimerDuration = 1e6 / expectedPulseRate / 2`
   - `TimerActivation = RisingEdge`
   - `TriggerSource = Disabled`
7. **Grabber Trigger Settings (VPII - Stream tab)**
   - `TriggerMode = On`
   - `TriggerSource = input line`
   - `TriggerFilter = 1.0`
   - `TriggerEventMode = RisingEdge`
8. Set Timer Trigger Source to `Continuous`  
9. Wait for the defined duration  
10. Set Timer Trigger Source to `Disabled`  
11. Set Grabber Trigger Mode to `Off` (VPII - Stream tab)  
12. Close camera  
13. Close grabber  

## Pass Criteria
AUX callback count must equal `expectedPulseRate * duration`
