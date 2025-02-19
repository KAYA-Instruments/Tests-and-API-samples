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
guiUtils.log("Set index of: comboBoxGrabbers: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex
guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")

guiUtils.triggerAction("menuDeviceControl.actionDetect_cameras")
guiUtils.triggerAction("defaultToolButton_menuDetectCameras.actionDetect_cameras")
guiUtils.waitForEvent("camera(s) detection completed")

guiUtils.waitForEvent("camera(s) opened")


guiUtils.log("Clicking: defaultToolButton_actionDetectCameras_1")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras_1"))

guiUtils.log("Set property 'Width' of: 'kayaPropertyBrowser_Camera_0' to: '512'")
guiUtils.findObject("kayaPropertyBrowser_Camera_0").set('Width', 200)

guiUtils.log("Set property 'Height' of: 'kayaPropertyBrowser_Camera_0' to: '512'")
guiUtils.findObject("kayaPropertyBrowser_Camera_0").set('Height', 200)



guiUtils.log("Set property 'UserSetLoad' of: 'kayaPropertyBrowser_Camera_0' to: 'false'")
guiUtils.findObject("kayaPropertyBrowser_Camera_0").set('UserSetLoad', false)
guiUtils.msleep(5000)
//guiUtils.log("Clicking: cameraOpenCloseButton")
//guiUtils.clickTo(guiUtils.findObject("cameraOpenCloseButton"))
//guiUtils.log("Clicking: cameraOpenCloseButton")
//guiUtils.clickTo(guiUtils.findObject("cameraOpenCloseButton"))
//guiUtils.waitForEvent("camera(s) opened")
var currentWidth = guiUtils.findObject("kayaPropertyBrowser_Camera_0").get('Width')
var currentHeight = guiUtils.findObject("kayaPropertyBrowser_Camera_0").get('Height')
guiUtils.log("currentWidth = " + currentWidth)
guiUtils.log("currentHeight = " + currentHeight)
if (currentWidth == 512){
    guiUtils.log("Case return code: 1")
} else if (currentHeight == 512){
    guiUtils.log("Case return code: 1")
} else {
    guiUtils.log("Case return code: 0")
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
