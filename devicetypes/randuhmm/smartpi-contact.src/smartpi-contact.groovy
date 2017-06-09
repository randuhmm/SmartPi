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
    definition (name: "SmartPi Contact", namespace: "randuhmm", author: "Jonny Morrill") {
        capability "Contact Sensor"
		capability "Refresh"
		capability "Sensor"
    }

    simulator {
        // TODO: define status and reply messages here
    }

	tiles(scale: 2) {

        standardTile("contact", "device.contact", width: 2, height: 2, canChangeIcon: true) {
            state "open", label: '${name}', icon:"st.contact.contact.open", backgroundColor:"#ffa81e"
            state "closed", label: '${name}', icon:"st.contact.contact.closed", backgroundColor:"#79b821"
        }

		standardTile("refresh", "device.refresh", inactiveLabel: false, decoration: "flat", width: 2, height: 2) {
			state "default", action:"refresh.refresh", icon:"st.secondary.refresh"
		}

		main (["contact"])
		details(["contact","refresh"])
	}
    
}

// parse events into attributes
def parse(String rawEvent) {
    def parsedEvent = parseLanMessage(rawEvent)
    log.debug "parsedEvent: ${parsedEvent}"
    
    if(parsedEvent?.json?.state == 1) {
        sendEvent(name: "contact", value: "open")
    } else {
        sendEvent(name: "contact", value: "closed")
    }
}

// Handle device data update
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

def refresh() {
	log.debug "Executing WeMo Motion 'subscribe', then 'timeSyncResponse', then 'getStatus'"
	subscribe()
}

def subscribe(hostAddress) {
    log.debug "Executing 'subscribe()'"
    def address = getCallBackAddress()
    new physicalgraph.device.HubAction("""SUBSCRIBE /upnp/event/basicevent1 HTTP/1.1
HOST: ${hostAddress}
CALLBACK: <http://${address}/>
NT: upnp:event
TIMEOUT: Second-4200


""", physicalgraph.device.Protocol.LAN)
}

def subscribe() {
	subscribe(getHostAddress())
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
