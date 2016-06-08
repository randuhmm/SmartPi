/**
 *  My Test Service Manager
 *
 *  Copyright 2016 Jonny Morrill
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 */
definition(
    name: "My Test Service Manager",
    namespace: "randuhmm",
    author: "Jonny Morrill",
    description: "A Service Manager for Randuhmm hubs and devices.",
    category: "My Apps",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    singleInstance: true
)


preferences {
  page(name:"firstPage", title:"Randuhmm Device Setup", content:"firstPage")
}

private discoverRanduhmmHub()
{
  sendHubCommand(new physicalgraph.device.HubAction("lan discovery urn:Randuhmm:device:hub:1", physicalgraph.device.Protocol.LAN))
}

def firstPage()
{
  if(canInstallLabs())
  {
    int refreshCount = !state.refreshCount ? 0 : state.refreshCount as int
    state.refreshCount = refreshCount + 1
    def refreshInterval = 5

    log.debug "REFRESH COUNT :: ${refreshCount}"

        if(!state.subscribe) {
          log.debug "subscribe to location"
          subscribe(location, null, locationHandler, [filterEvents:false])
          state.subscribe = true
        }

    //ssdp request every 25 seconds
    if((refreshCount % 5) == 0) {
      log.debug "discoverRanduhmmThings() called"
            discoverRanduhmmHub()
    }

        def logs = getLogs()

    //setup.xml request every 5 seconds except on discoveries
    if(((refreshCount % 1) == 0) && ((refreshCount % 5) != 0)) {
      logs << [refreshCount:"Refresh ${refreshCount}"]
    }

    def hubsDiscovered = getDevices()//hubsDiscovered()

    return dynamicPage(name:"firstPage", title:"Discovery Started!", nextPage:"", refreshInterval: refreshInterval, install:true, uninstall: true) {
      section("Select a hub...") {
        input "selectedHubs", "enum", required:false, title:"Select Randuhmm Hubs \n(${hubsDiscovered.size() ?: 0} found)", multiple:true, options:hubsDiscovered
      }
      section("Logs") {
        input "logs", "enum", required:false, title:"Logs \n(${logs.size() ?: 0} found)", multiple:true, options:logs
      }
    }
  }
  else
  {
    def upgradeNeeded = """To use SmartThings Labs, your Hub should be completely up to date.

To update your Hub, access Location Settings in the Main Menu (tap the gear next to your location name), select your Hub, and choose "Update Hub"."""

    return dynamicPage(name:"firstPage", title:"Upgrade needed!", nextPage:"", install:false, uninstall: true) {
      section("Upgrade") {
        paragraph "$upgradeNeeded"
      }
    }
  }
}

def hubsDiscovered() {
  def hubs = getRanduhmmHubs().findAll { it?.value?.verified == true }
  def map = [:]
  hubs.each {
    def value = it.value.name ?: "Randuhmm Hub ${it.value.ssdpUSN.split(':')[1][-3..-1]}"
    def key = it.value.mac
    map["${key}"] = value
  }
  map
}

def getRanduhmmHubs()
{
  if (!state.hubs) { state.hubs = [:] }
  state.hubs
}

def getLogs()
{
  if(!state.hasProperty('logs')) { state.logs = [:] }
    state.logs
}

def installed() {
  log.debug "Installed with settings: ${settings}"

  initialize()
}

def updated() {
  log.debug "Updated with settings: ${settings}"
  initialize()
}

def initialize() {
  // TODO: subscribe to attributes, devices, locations, etc.
  unsubscribe()
    unschedule()
  subscribe(location, null, locationHandler, [filterEvents:false])

  if (selectedSwitches)
    log.debug "addSwitches() called"

  if (selectedMotions)
    log.debug "addMotions() called"

  if (selectedLightSwitches)
    log.debug "addLightSwitches() called"

  runIn(5, "subscribeToDevices") //initial subscriptions delayed by 5 seconds
  runIn(10, "refreshDevices") //refresh devices, delayed by 10 seconds
    runEvery5Minutes("refresh")
}

def resubscribe() {
  log.debug "Resubscribe called, delegating to refresh()"
  refresh()
}

def refresh() {
  log.debug "refresh() called"
    log.debug "doDeviceSync() called"
  refreshDevices()
}

def refreshDevices() {
  log.debug "refreshDevices() called"
  //def devices = getAllChildDevices()
  //devices.each { d ->
  //  log.debug "Calling refresh() on device: ${d.id}"
  //  d.refresh()
  //}
}

def subscribeToDevices() {
  log.debug "subscribeToDevices() called"
  //def devices = getAllChildDevices()
  //devices.each { d ->
  //  d.subscribe()
  //}
}

def locationHandler(evt) {
    def description = evt.description
    def hub = evt?.hubId

    def parsedEvent = parseEventMessage(description)
    parsedEvent << ["hub":hub]

    if (parsedEvent?.ssdpTerm?.contains("urn:Randuhmm:device:hub:1")) {
      def devices = getDevices()
      if (!(devices."${parsedEvent.ssdpUSN.toString()}")) {
        devices << ["${parsedEvent.ssdpUSN.toString()}":parsedEvent]
      }
    }
 }

def getDevices() {
  if (!state.devices) {
      state.devices = [:]
  }
  state.devices
}

/*
private def parseDiscoveryMessage(String description) {
  def device = [:]
  def parts = description.split(',')
  parts.each { part ->
    part = part.trim()
    if (part.startsWith('devicetype:')) {
      def valueString = part.split(":")[1].trim()
      device.devicetype = valueString
    }
    else if (part.startsWith('mac:')) {
      def valueString = part.split(":")[1].trim()
      if (valueString) {
        device.mac = valueString
      }
    }
    else if (part.startsWith('networkAddress:')) {
      def valueString = part.split(":")[1].trim()
      if (valueString) {
        device.ip = valueString
      }
    }
    else if (part.startsWith('deviceAddress:')) {
      def valueString = part.split(":")[1].trim()
      if (valueString) {
        device.port = valueString
      }
    }
    else if (part.startsWith('ssdpPath:')) {
      def valueString = part.split(":")[1].trim()
      if (valueString) {
        device.ssdpPath = valueString
      }
    }
    else if (part.startsWith('ssdpUSN:')) {
      part -= "ssdpUSN:"
      def valueString = part.trim()
      if (valueString) {
        device.ssdpUSN = valueString
      }
    }
    else if (part.startsWith('ssdpTerm:')) {
      part -= "ssdpTerm:"
      def valueString = part.trim()
      if (valueString) {
        device.ssdpTerm = valueString
      }
    }
    else if (part.startsWith('headers')) {
      part -= "headers:"
      def valueString = part.trim()
      if (valueString) {
        device.headers = valueString
      }
    }
    else if (part.startsWith('body')) {
      part -= "body:"
      def valueString = part.trim()
      if (valueString) {
        device.body = valueString
      }
    }
  }
  device
}
*/


private String convertHexToIP(hex) {
  [convertHexToInt(hex[0..1]),convertHexToInt(hex[2..3]),convertHexToInt(hex[4..5]),convertHexToInt(hex[6..7])].join(".")
}

private Integer convertHexToInt(hex) {
  Integer.parseInt(hex,16)
}

private Boolean canInstallLabs() {
  return hasAllHubsOver("000.011.00603")
}

private Boolean hasAllHubsOver(String desiredFirmware) {
  return realHubFirmwareVersions.every { fw -> fw >= desiredFirmware }
}

private List getRealHubFirmwareVersions() {
  return location.hubs*.firmwareVersionString.findAll { it }
}
