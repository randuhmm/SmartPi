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
	definition (name: "SmartPi", namespace: "randuhmm", author: "Jonny Morrill") {
		capability "Polling"
		capability "Refresh"
		capability "Temperature Measurement"
        capability "Switch"
        capability "Sensor"
        capability "Actuator"
        capability "Contact Sensor"
        
        attribute "cpuPercentage", "string"
        attribute "memory", "string"
        attribute "diskUsage", "string"
        
        command "restart"
	}

	simulator {
		// TODO: define status and reply messages here
	}

	tiles {
		valueTile("temperature", "device.temperature", width: 1, height: 1) {
            state "temperature", label:'${currentValue}° CPU', unit: "F",
            backgroundColors:[
                [value: 25, color: "#153591"],
                [value: 35, color: "#1e9cbb"],
                [value: 47, color: "#90d2a7"],
                [value: 59, color: "#44b621"],
                [value: 67, color: "#f1d801"],
                [value: 76, color: "#d04e00"],
                [value: 77, color: "#bc2323"]
            ]
        }
        standardTile("button", "device.switch", width: 1, height: 1, canChangeIcon: true) {
			state "off", label: 'Off', icon: "st.Electronics.electronics18", backgroundColor: "#ffffff", nextState: "on"
			state "on", label: 'On', icon: "st.Electronics.electronics18", backgroundColor: "#79b821", nextState: "off"
		}
        valueTile("cpuPercentage", "device.cpuPercentage", inactiveLabel: false) {
        	state "default", label:'${currentValue}% CPU', unit:"Percentage",
            backgroundColors:[
                [value: 31, color: "#153591"],
                [value: 44, color: "#1e9cbb"],
                [value: 59, color: "#90d2a7"],
                [value: 74, color: "#44b621"],
                [value: 84, color: "#f1d801"],
                [value: 95, color: "#d04e00"],
                [value: 96, color: "#bc2323"]
            ]
        }
        valueTile("memory", "device.memory", width: 1, height: 1) {
        	state "default", label:'${currentValue} MB', unit:"MB",
            backgroundColors:[
                [value: 353, color: "#153591"],
                [value: 287, color: "#1e9cbb"],
                [value: 210, color: "#90d2a7"],
                [value: 133, color: "#44b621"],
                [value: 82, color: "#f1d801"],
                [value: 26, color: "#d04e00"],
                [value: 20, color: "#bc2323"]
            ]
        }
        valueTile("diskUsage", "device.diskUsage", width: 1, height: 1) {
        	state "default", label:'${currentValue}% Disk', unit:"Percent",
            backgroundColors:[
                [value: 31, color: "#153591"],
                [value: 44, color: "#1e9cbb"],
                [value: 59, color: "#90d2a7"],
                [value: 74, color: "#44b621"],
                [value: 84, color: "#f1d801"],
                [value: 95, color: "#d04e00"],
                [value: 96, color: "#bc2323"]
            ]
        }
        standardTile("contact", "device.contact", width: 1, height: 1) {
			state("closed", label:'${name}', icon:"st.contact.contact.closed", backgroundColor:"#79b821", action: "open")
			state("open", label:'${name}', icon:"st.contact.contact.open", backgroundColor:"#ffa81e", action: "close")
		}
        standardTile("restart", "device.restart", inactiveLabel: false, decoration: "flat") {
        	state "default", action:"restart", label: "Restart", displayName: "Restart"
        }
        standardTile("refresh", "device.refresh", inactiveLabel: false, decoration: "flat") {
        	state "default", action:"refresh.refresh", icon: "st.secondary.refresh"
        }
        main "button"
        details(["button", "temperature", "cpuPercentage", "memory" , "diskUsage", "contact", "restart", "refresh"])
	}
}

// parse events into attributes
def parse(String rawEvent) {
    def parsedEvent = parseLanMessage(rawEvent)
    if(parsedEvent.headers.containsKey('Device-Id')) {
    	def childId = parsedEvent.headers['Device-Id']
    	parent.dispatchEvent(childId, parsedEvent, rawEvent)
    }
}

// handle commands
def on() {
	log.debug "Executing 'on'"
	// TODO: handle 'on' command
}

def off() {
	log.debug "Executing 'off'"
	// TODO: handle 'off' command
}

def sync(ip, port) {
	def existingIp = getDataValue("ip")
	def existingPort = getDataValue("port")
	if (ip && ip != existingIp) {
		updateDataValue("ip", ip)
	}
	if (port && port != existingPort) {
		updateDataValue("port", port)
	}
}

def restart() {
    subscribeAction("/path/of/event")
}

private subscribeAction(path, callbackPath="") {
    log.trace "subscribe($path, $callbackPath)"
    def address = getCallBackAddress()
    def ip = getHostAddress()

    def result = new physicalgraph.device.HubAction(
        method: "SUBSCRIBE",
        path: path,
        headers: [
            HOST: ip,
            CALLBACK: "<http://${address}/notify$callbackPath>",
            NT: "upnp:event",
            TIMEOUT: "Second-28800"
        ]
    )

    log.trace "SUBSCRIBE $path"

    return result
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
