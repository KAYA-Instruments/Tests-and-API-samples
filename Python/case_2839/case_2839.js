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
var camera = scriptParametersMap["camera"]
var camera_index;
guiUtils.waitForEvent("InitDialogShown")
guiUtils.log("Set index of: comboBoxGrabbers: " + deviceIndex)
guiUtils.findObject("comboBoxGrabbers").currentIndex = deviceIndex
guiUtils.log("Clicking: pushButtonNewProject")
guiUtils.clickTo(guiUtils.findObject("pushButtonNewProject"))

guiUtils.waitForEvent("newProjectCreated")



guiUtils.triggerAction("defaultToolButton_menuDetectCameras.actionDetect_cameras")
guiUtils.log("Clicking: defaultToolButton_actionDetectCameras_1")
guiUtils.clickTo(guiUtils.findObject("defaultToolButton_actionDetectCameras_1"))
guiUtils.waitForEvent("camera(s) detection completed")

guiUtils.waitForEvent("camera(s) opened")
var number_of_cameras = 4

for (var i = 0; i < number_of_cameras; i++){
    var camera_model_name = guiUtils.findObject("kayaPropertyBrowser_Camera_" + i).get('DeviceModelName')
    guiUtils.log("camera_model_name = " + camera_model_name)
    if (camera_model_name === undefined){
        guiUtils.log("Camera not found")
        guiUtils.log("Case return code: 2")
        guiUtils.triggerAction("menuFile.actionClose")
        guiUtils.log("Clicking: Project close")
        guiUtils.clickTo(guiUtils.findObject("_20"))

        guiUtils.waitForEvent("InitDialogShown")

        guiUtils.log("Clicking: pushButtonCloseProgram_1")
        guiUtils.clickTo(guiUtils.findObject("pushButtonCloseProgram_1"))

        guiUtils.triggerAction("menuFile.actionQuit")
        guiUtils.triggerAction("menuService.actionQuit")
        guiUtils.log("Script finished")
    } else if (camera_model_name.startsWith(camera)) {
        guiUtils.log("Required camera Found")
        camera_index = i
        break
    } else {
        guiUtils.log("Unsuitable camera")
    }
}
// FUNCTIONS
function set_get_camera_param(camera_index, param, value){
    guiUtils.log("Set property '" + param + "' of: 'kayaPropertyBrowser_Camera " + camera_index + "' to: '" + value + "'")
    guiUtils.findObject("kayaPropertyBrowser_Camera_" + camera_index).set(param, value)
    guiUtils.log(param + " = " + guiUtils.findObject("kayaPropertyBrowser_Camera_" + camera_index).get(param))
    if (guiUtils.findObject("kayaPropertyBrowser_Camera_" + camera_index).get(param) != value){
        guiUtils.log("error_count++")
        return false
    }
    return true
}
function set_get_grabber_param(param, value){
    guiUtils.log("Set property '" + param + "' of: 'kayaPropertyBrowser_Grabber' to: '" + value + "'")
    guiUtils.findObject("kayaPropertyBrowser_Grabber").set(param, value)
    guiUtils.log(param + " = " + guiUtils.findObject("kayaPropertyBrowser_Grabber").get(param))
    if (guiUtils.findObject("kayaPropertyBrowser_Grabber").get(param) != value){
        guiUtils.log("error_count++")
        return false
    }
    return true
}

var error_count = 0

// Camera stress test
guiUtils.log("camera_index = " + camera_index)
if (!set_get_camera_param(camera_index, 'Width', 512)){error_count++}
if (!set_get_camera_param(camera_index, 'Height', 512)){error_count++}
if (!set_get_camera_param(camera_index, 'WidthMax', 4000)){error_count++}
if (!set_get_camera_param(camera_index, 'HeightMax', 4000)){error_count++}
if (!set_get_camera_param(camera_index, 'OffsetX', 10)){error_count++}
if (!set_get_camera_param(camera_index, 'OffsetY', 10)){error_count++}
if (!set_get_camera_param(camera_index, 'PixelFormat', 25)){error_count++}
if (!set_get_camera_param(camera_index, 'ScanMode', 1)){error_count++}
if (!set_get_camera_param(camera_index, 'AcquisitionMode', 1)){error_count++}
if (!set_get_camera_param(camera_index, 'AcquisitionFrameCount', 1)){error_count++}
if (!set_get_camera_param(camera_index, 'VideoSourceType', 1)){error_count++}
if (!set_get_camera_param(camera_index, 'VideoSourcePatternType', 1)){error_count++}
if (!set_get_camera_param(camera_index, 'SimulationTriggerMode', 1)){error_count++}
if (!set_get_camera_param(camera_index, 'SimulationTriggerActivation', 1)){error_count++}


// Grabber stress test

guiUtils.log("Set index of: ProjectWindow to: 1")
guiUtils.findObject("ProjectWindow").currentIndex = 1


if (!set_get_grabber_param("Width", 512)) {error_count++}
if (!set_get_grabber_param("SegmentsPerBuffer", 10)) {error_count++}
if (!set_get_grabber_param("PixelFormat", 6)) {error_count++}
if (!set_get_grabber_param("Height", 1000)) {error_count++}
if (!set_get_grabber_param("DebayerMode", 1)) {error_count++}
if (!set_get_grabber_param("PackedDataMode", 1)) {error_count++}
if (!set_get_grabber_param("DecimationVertical", 2)) {error_count++}
if (!set_get_grabber_param("FramesPerStream", 20)) {error_count++}
if (!set_get_grabber_param("TransferControlMode", 1)) {error_count++}
if (!set_get_grabber_param("ColorTransformationRG", 1)) {error_count++}
if (!set_get_grabber_param("ColorTransformationRB", 2)) {error_count++}
if (!set_get_grabber_param("ColorTransformationR0", 3)) {error_count++}
if (!set_get_grabber_param("ColorTransformationGR", 4)) {error_count++}
if (!set_get_grabber_param("ColorTransformationGB", 5)) {error_count++}
if (!set_get_grabber_param("ColorTransformationG0", 1)) {error_count++}
if (!set_get_grabber_param("ColorTransformationBR", 2)) {error_count++}
if (!set_get_grabber_param("ColorTransformationBG", 3)) {error_count++}
if (!set_get_grabber_param("ColorTransformationBB", 4)) {error_count++}
if (!set_get_grabber_param("TriggerActivation", 1)) {error_count++}
if (!set_get_grabber_param("TriggerSource", 16)) {error_count++}
if (!set_get_grabber_param("TriggerDelay", 1)) {error_count++}
if (!set_get_grabber_param("TriggerEventMode", 3)) {error_count++}

guiUtils.log("error_count = " + error_count)
if (error_count == 0) {
    guiUtils.log("Case return code: 0")
} else {
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
