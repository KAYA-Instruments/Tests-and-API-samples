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
var number_of_tests = +scriptParametersMap['number_of_tests']
var caemraIndex = +scriptParametersMap['cameraIndex']
guiUtils.log("number_of_tests = " + number_of_tests)

guiUtils.log("Set index of: comboBoxGrabbers: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex
guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")

guiUtils.log("Clicking: defaultToolButton_actionDetectCameras")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras"))

//guiUtils.triggerAction("menuDeviceControl.actionDetect_cameras")
guiUtils.waitForEvent("camera(s) detection completed")
guiUtils.log("camera(s) detected")
var error_count = 0
guiUtils.waitForEvent("camera(s) opened")
guiUtils.log("START_LOOP")
for (var i = 0; i < number_of_tests; i++){
    guiUtils.log("Clicking: defaultToolButton_actionSingle_frame")
//    guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionSingle_frame"))
    guiUtils.triggerAction("defaultToolButton_menuSingle_frame.actionSingle_frameCamera0")
    guiUtils.msleep(5000)
    number_of_frames = guiUtils.findObject("kayaPropertyBrowser_Grabber").get('RXFrameCounter')
    guiUtils.log("RXFrameCounter")
    guiUtils.log(number_of_frames)
    if(number_of_frames != 1) {
    error_count++
}
}
guiUtils.log("error_count")
guiUtils.log(error_count)
if (error_count == 0) {
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
