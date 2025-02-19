/*
FUNCTIONS:

guiUtils - main js object for get access to Qt GUI elements

Functions of guiUtils object:

findByName(sourceElement, name) - function return Qt GUI element object found in sourceElement by name
findObject(name) - function return Qt GUI element object found in root (Qt MainWindow) by name
clickTo(sourceElement) - function simulate mouse left button click to Qt GUI element object
msleep(mstime) - script sleep for mstime (milliseconds)
waitForEvent(eventName) - waiting app event
log(message) - logging message to main application log file

APP EVENTS:

newProjectCreated - event triggered when application finishing creating new project (see code 'pGlobalEventVpNewProjectCreated->waitCondition.wakeAll();')
SCRIPT:
*/

guiUtils.waitForEvent("InitDialogShown")
var scriptParams = guiUtils.scriptParametersString()
var scriptParametersMap = guiUtils.scriptParametersMap()
for (var param in scriptParametersMap)
{
	guiUtils.log("scriptParameter: " + param + " = '" + scriptParametersMap[param] + "'");
}
var deviceIndex = +scriptParametersMap["deviceIndex"]
//var device_index = +deviceIndex
guiUtils.log("Set index of: comboBoxGrabbers: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex
guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")

guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras"))
guiUtils.waitForEvent("camera(s) detection completed")

guiUtils.waitForEvent("camera(s) opened")



guiUtils.log("Set index of: stackedWidget to: 1")
guiUtils.findObject("stackedWidget").currentIndex = 1

guiUtils.log("Set index of: cameraSelectorCombo to: 1")
guiUtils.findObject("cameraSelectorCombo").currentIndex = 1
var camera1_model_name = guiUtils.findObject("kayaPropertyBrowser_Camera_1").get('DeviceModelName')
guiUtils.log("CameraModel")
guiUtils.log(camera1_model_name)
guiUtils.log("Set index of: stackedWidget to: 0")
guiUtils.findObject("stackedWidget").currentIndex = 0

guiUtils.log("Set index of: cameraSelectorCombo to: 0")
guiUtils.findObject("cameraSelectorCombo").currentIndex = 0
var camera0_model_name = guiUtils.findObject("kayaPropertyBrowser_Camera_0").get('DeviceModelName')
guiUtils.log("CameraModel")
guiUtils.log(camera0_model_name)
guiUtils.log("Clicking: cameraOpenCloseButton")
guiUtils.clickTo(guiUtils.findObject("cameraOpenCloseButton"))
if (camera1_model_name != camera0_model_name){
    guiUtils.log("Case return code: 0")
}else {
    guiUtils.log("Case return code: 1")
}
guiUtils.triggerAction("menuFile.actionClose")
guiUtils.log("Clicking: Project close")
guiUtils.clickTo(guiUtils.findObject("_20"))

guiUtils.waitForEvent("InitDialogShown")

guiUtils.log("Clicking: pushButtonCloseProgram_1")
guiUtils.clickTo(guiUtils.findObject("pushButtonCloseProgram_1"))

guiUtils.triggerAction("menuFile.actionQuit")
guiUtils.triggerAction("menuService.actionQuit")
guiUtils.log("Script finished")
