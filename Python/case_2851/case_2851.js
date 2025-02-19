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
function get_all_frame_counter(){
    guiUtils.log('Entering in function')
    guiUtils.findObject("kayaPropertyBrowser_Grabber").set("CameraSelector", 0)
    guiUtils.msleep(3000)
    var frame_counter = guiUtils.findObject("kayaPropertyBrowser_Grabber").get("RXFrameCounter")
    var drop_frame_counter = guiUtils.findObject("kayaPropertyBrowser_Grabber").get("DropFrameCounter")
    guiUtils.log("frame_counter = " + frame_counter + " drop_frame_counter = " + drop_frame_counter)
    return drop_frame_counter + frame_counter
}
guiUtils.waitForEvent("InitDialogShown")
guiUtils.log("Set index of: comboBoxGrabbers to: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex
guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")

guiUtils.triggerAction("defaultToolButton_menuDetectCameras.actionDetect_cameras")
guiUtils.log("Clicking: defaultToolButton_actionDetectCameras_1")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras_1"))
guiUtils.waitForEvent("camera(s) detection completed")
guiUtils.waitForEvent("camera(s) opened")

guiUtils.triggerAction("defaultToolButton_menuStart.actionStartAllCameras")
guiUtils.log("Clicking: defaultToolButton_actionStart")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionStart"))

guiUtils.triggerAction("defaultToolButton_menuStop.actionStopAllCameras")
guiUtils.log("Clicking: defaultToolButton_actionStop")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionStop"))
var first_all_frame_counter = get_all_frame_counter()
guiUtils.msleep(3000)
guiUtils.log("Clicking: Buffer replay mode on")
guiUtils.clickTo(guiUtils.findObject("_491"))
guiUtils.msleep(3000)
guiUtils.log("Set value of: FPS to: 5")
guiUtils.setValue("_505", 5)
guiUtils.msleep(3000)
guiUtils.log("Clicking: play recorded stream")
guiUtils.clickTo(guiUtils.findObject("_496"))
guiUtils.msleep(3000)
// Maxim you need to add some delay here to let "play recorded stream" state activate before clicking buttons that appear only after reply has started
guiUtils.log("Clicking: stop replaying")
guiUtils.clickTo(guiUtils.findObject("_497"))
guiUtils.msleep(3000)
guiUtils.log("Set value of: FPS to: 20")
guiUtils.setValue("_505", 20)
guiUtils.msleep(3000)
guiUtils.log("Clicking: play recorded stream")
guiUtils.clickTo(guiUtils.findObject("_496"))
guiUtils.msleep(3000)
guiUtils.log("Clicking: stop replaying")
guiUtils.clickTo(guiUtils.findObject("_497"))
guiUtils.msleep(3000)
guiUtils.log("Buffer replay mode off")
guiUtils.clickTo(guiUtils.findObject("_491"))
guiUtils.msleep(3000)
var second_all_frame_counter = get_all_frame_counter()
if (first_all_frame_counter == second_all_frame_counter){
    guiUtils.log('Case return code: 0')
} else {
    guiUtils.log('Case return code: 1')
}
guiUtils.msleep(3000)
guiUtils.triggerAction("menuFile.actionClose")
guiUtils.log("Clicking: Project close")
guiUtils.clickTo(guiUtils.findObject("_20"))

guiUtils.waitForEvent("InitDialogShown")

guiUtils.log("Clicking: pushButtonCloseProgram_1")
guiUtils.clickTo(guiUtils.findObject("pushButtonCloseProgram_1"))

guiUtils.triggerAction("menuFile.actionQuit")
guiUtils.triggerAction("menuService.actionQuit")
guiUtils.log("Script finished")
