/*
Built-in stuff automatically provided to the script by VisionPoint application:

guiUtils - main js object for get access to Qt GUI elements

Methods of guiUtils object:

log(message) - add log message to main application log file and optionaly to:
    console                     - if "internal.VisionPoint._conf.GUI.GUITester.Logging.Console" configuration is set to 1"
    "<script_full_path>out.txt" - if "internal.VisionPoint._conf.GUI.GUITester.Logging.ScriptTxt" configuration is set to 1"
scriptParametersString() - returns string with parameters passed to Vision Point via option '--guiscriptParameters'
   Example: --guiscript <some_path>/guiTestScript.js --guiscriptParameters "--foo fooValue1 --bar --opt 55"
scriptParametersMap() - returns map (JS array) of parameters and their valuespassed to Vision Point via option '--guiscriptParameters'
findByName(sourceElement, name) - returns Qt GUI element object found in sourceElement by name
findObject(name) - returns Qt GUI element object found in root (Qt MainWindow) by name
clickTo(sourceElement) - simulate mouse left button click to Qt GUI element object
setProperty(objectName, propertyName, propertyValue) - set value of given property of given object
   For example, the following two lines are functionaly equialent:
   guiUtils.findObject("ProjectWindow").currentIndex = 1
   guiUtils.setProperty("ProjectWindow", "currentIndex", 1)
   but in case of "setProperty" guiUtils will return after additional waiting time specified by the configuration "visualActionsDelay" (default 2000 ms"
msleep(mstime) - script sleep for mstime (milliseconds)
waitForEvent(eventName) - waiting app event

APP EVENTS:

"InitDialogShown" - event triggered when initial dialog for PCI device selection is shown
"newProjectCreated" - event triggered when application finished initializing(creating or openning) of a project (see code 'pGlobalEventVpNewProjectCreated->waitCondition.wakeAll();')
SCRIPT:
*/

var scriptParams = guiUtils.scriptParametersString()
guiUtils.log("scriptParams: '" + scriptParams + "'")

var scriptParametersMap = guiUtils.scriptParametersMap()
for (var param in scriptParametersMap) 
{
	guiUtils.log("scriptParameter: " + param + " = '" + scriptParametersMap[param] + "'");
}
var deviceIndex = +scriptParametersMap["deviceIndex"]
guiUtils.waitForEvent("InitDialogShown")

guiUtils.log("Set index of: comboBoxGrabbers to: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex

guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")

//guiUtils.triggerAction("menuDeviceControl.actionDetect_cameras")

guiUtils.triggerAction("defaultToolButton_menuDetectCameras.actionDetect_cameras")
guiUtils.log("Clicking: defaultToolButton_actionDetectCameras_1")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras_1"))
guiUtils.waitForEvent("camera(s) detection completed")
guiUtils.waitForEvent("camera(s) opened")

number_of_tests = +scriptParametersMap["number_of_tests"]
var error_count = 0
for (var i = 0; i < number_of_tests; i++){
    guiUtils.log("Iteration number " + (i+1))
    guiUtils.triggerAction("defaultToolButton_menuStart.actionStartAllCameras")
    guiUtils.log("Clicking: defaultToolButton_actionStart")
    guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionStart"))

    guiUtils.triggerAction("defaultToolButton_menuStop.actionStopAllCameras")
    guiUtils.log("Clicking: defaultToolButton_actionStop")
    guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionStop"))
    var number_of_frames = guiUtils.findObject("kayaPropertyBrowser_Grabber").get('RXFrameCounter')
    guiUtils.log("RXFrameCounter: " + number_of_frames)
    var drop_frames = guiUtils.findObject("kayaPropertyBrowser_Grabber").get('DropFrameCounter')
    guiUtils.log("DropFrameCounter: " + drop_frames)
    if (number_of_frames == 0 ){
        error_count++
    } else if (drop_frames != 0) {
        error_count++
    }
    guiUtils.triggerAction("defaultToolButton_menuSingle_frame.actionSingle_frameAllCameras")
    guiUtils.log("Clicking: defaultToolButton_actionSingle_frame")
    guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionSingle_frame"))
    var number_of_frames_2 = guiUtils.findObject("kayaPropertyBrowser_Grabber").get('RXFrameCounter')
    guiUtils.log("RXFrameCounter: " + number_of_frames_2)
    var drop_frames_2 = guiUtils.findObject("kayaPropertyBrowser_Grabber").get('DropFrameCounter')
    guiUtils.log("DropFrameCounter: " + drop_frames_2)
    if (number_of_frames_2 == 0 ){
        error_count++
    } else if (drop_frames_2 != 0) {
        error_count++
    }
}
if (error_count == 0){
    guiUtils.log("Case return code: 0")
} else {
    guiUtils.log("Case return code: 1")
    }
guiUtils.log("Clicking: cameraOpenCloseButton")
guiUtils.clickTo(guiUtils.findObject("cameraOpenCloseButton"))

guiUtils.triggerAction("menuFile.actionClose")
guiUtils.log("Clicking: Project close")
guiUtils.clickTo(guiUtils.findObject("_20"))

guiUtils.waitForEvent("InitDialogShown")

guiUtils.log("Clicking: pushButtonCloseProgram_1")
guiUtils.clickTo(guiUtils.findObject("pushButtonCloseProgram_1"))

guiUtils.triggerAction("menuFile.actionQuit")
guiUtils.triggerAction("menuService.actionQuit")
guiUtils.log("Script finished")
