/**
 *  Hub
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
metadata {
    definition (name: "SmartPi Switch", namespace: "randuhmm", author: "Jonny Morrill") {
        capability "Actuator"
        capability "Switch"
        capability "Sensor"
    }

    simulator {
        status "on": "on/off: 1"
        status "off": "on/off: 0"
        
        reply "zcl on-off on": "on/off: 1"
        reply "zcl on-off off": "on/off: 0"
    }

    tiles {
        standardTile("switch", "device.switch", width: 2, height: 2, canChangeIcon: true) {
            state "off", label: '${name}', action: "switch.on", icon: "st.switches.switch.off", backgroundColor: "#ffffff"
            state "on", label: '${name}', action: "switch.off", icon: "st.switches.switch.on", backgroundColor: "#79b821"
        }
        main "switch"
        details "switch"
    }
}

// parse events into attributes
def parse(String rawEvent) {
    log.debug "Parsing '${rawEvent}'"
    def parsedEvent = parseLanMessage(rawEvent)
    //log.debug "parsedEvent: ${parsedEvent}"
    
    def result = []
    if (parsedEvent.json) {
 		if(parsedEvent.json.switch) {
        	result << createEvent(name: "switch", value: parsedEvent.json.switch)
        }
    }
    result
}

// handle hub response
// TODO

// handle commands
def on() {
    log.debug "Executing 'on'"
    /*
    String host = getHostAddress()
    String http_request = """POST /on?param=123 HTTP/1.1\r\nHOST: $host\r\n\r\n"""
    def result = new physicalgraph.device.HubAction(
        http_request,
        physicalgraph.device.Protocol.LAN,
        host,
        [
            callback: handleOn
        ]
    )
    sendHubCommand(result)
    */
    def result = new physicalgraph.device.HubAction(
        method: "POST",
        path: "/on",
        headers: [
            HOST: getHostAddress()
        ],
        query: [param1: "value1", param2: "value2"]
    )
    return result
}

def handleOn(physicalgraph.device.HubResponse hubResponse) {
    log.debug "handleOn(): $hubResponse"
    sendEvent(name: "switch", value: "on")
}

def off() {
	/*
    log.debug "Executing 'off'"
    String host = getHostAddress()
    String http_request = """POST /off?param=123 HTTP/1.1\r\nHOST: $host\r\n\r\n"""
    def result = new physicalgraph.device.HubAction(
        http_request,
        physicalgraph.device.Protocol.LAN,
        host,
        [
            callback: handleOff
        ]
    )
    sendHubCommand(result)
    */
    def result = new physicalgraph.device.HubAction(
        method: "POST",
        path: "/off",
        headers: [
            HOST: getHostAddress()
        ],
        query: [param1: "value1", param2: "value2"]
    )
    return result
}

def handleOff(physicalgraph.device.HubResponse hubResponse) {
    log.debug "handleOff()"
    sendEvent(name: "switch", value: "off")
}

def sync(ip, port) {
    log.debug "sync():"
    def existingIp = getDataValue("ip")
    def existingPort = getDataValue("port")
    if (ip && ip != existingIp) {
        updateDataValue("ip", ip)
    }
    if (port && port != existingPort) {
        updateDataValue("port", port)
    }
}

// gets the address of the hub
private getCallBackAddress() {
    return device.hub.getDataValue("localIP") + ":" + device.hub.getDataValue("localSrvPortTCP")
}

// gets the address of the device
private getHostAddress() {
    def ip = getDataValue("ip")
    def port = getDataValue("port")

    if (!ip || !port) {
        def parts = device.deviceNetworkId.split(":")
        if (parts.length == 2) {
            ip = parts[0]
            port = parts[1]
        } else {
            log.warn "Can't figure out ip and port for device: ${device.id}"
        }
    }

    log.debug "Using IP: $ip and port: $port for device: ${device.id}"
    return convertHexToIP(ip) + ":" + convertHexToInt(port)
}

private Integer convertHexToInt(hex) {
    return Integer.parseInt(hex,16)
}

private String convertHexToIP(hex) {
    return [convertHexToInt(hex[0..1]),convertHexToInt(hex[2..3]),convertHexToInt(hex[4..5]),convertHexToInt(hex[6..7])].join(".")
}