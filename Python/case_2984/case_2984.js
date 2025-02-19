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

var deviceIndex = scriptParametersMap["deviceIndex"]
var instance = scriptParametersMap["instance"]
var number_of_cameras = scriptParametersMap["number_of_cameras"]
guiUtils.waitForEvent("InitDialogShown")

guiUtils.log("Set index of: comboBoxGrabbers to: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex


guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")




guiUtils.log("Set index of: qt_tabwidget_stackedwidget_1 to: 2")
guiUtils.findObject("qt_tabwidget_stackedwidget_1").currentIndex = 2

guiUtils.log("Set index of: qt_tabwidget_tabbar_1 to: 2")
guiUtils.findObject("qt_tabwidget_tabbar_1").currentIndex = 2

guiUtils.log("Clicking: defaultToolButton_actionDetectCameras")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras"))
guiUtils.waitForEvent("camera(s) detection completed")
guiUtils.waitForEvent("camera(s) opened")

// Turn off next camera for next instance

for (var i = 0; i<number_of_cameras; i++){
    if (i != instance){
        guiUtils.log("Set index of: stackedWidget to: " + i)
        guiUtils.findObject("stackedWidget").currentIndex = i
        guiUtils.log("Set index of: cameraSelectorCombo to: " + i)
        guiUtils.findObject("cameraSelectorCombo").currentIndex = i
        guiUtils.log("Clicking: cameraOpenCloseButton")
        guiUtils.clickTo(guiUtils.findObject("cameraOpenCloseButton"))
        guiUtils.msleep(1000)
    }

}
var last_frame_count = 0
var test_passed = "true"
guiUtils.triggerAction("defaultToolButton_menuStart.actionStartCamera" + instance)
if (instance == 0) {
    for (var i = 0; i < 40*number_of_cameras; i++) {
    guiUtils.msleep(1000)
    var new_frame_count = guiUtils.findObject("kayaPropertyBrowser_Grabber").get('RXFrameCounter')
    guiUtils.log("last_frame_count = " + last_frame_count)
    guiUtils.log("new_frame_count = " + new_frame_count)
    if (new_frame_count == last_frame_count) {
    var test_passed = "false"
        guiUtils.log("RXFrameCounter = " + new_frame_count)
    }
    last_frame_count = new_frame_count
    }

} else {
    guiUtils.msleep(20000)
}

guiUtils.triggerAction("defaultToolButton_menuStop.actionStopCamera" + instance)
if (instance == 0) {
    if (test_passed == "true"){
        guiUtils.log("Case return code: 0")
    } else {
        guiUtils.log("Case return code: 1")
    }

}

guiUtils.triggerAction("menuFile.actionClose")
guiUtils.log("Clicking: actionClose")
guiUtils.clickTo(guiUtils.findObject("_20"))

guiUtils.waitForEvent("InitDialogShown")

guiUtils.log("Clicking: pushButtonCloseProgram_1")
guiUtils.clickTo(guiUtils.findObject("pushButtonCloseProgram_1"))

guiUtils.triggerAction("menuFile.actionQuit")
guiUtils.triggerAction("menuService.actionQuit")

guiUtils.log("Script finished")
