#!/usr/bin/env python
# hot_drinks.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Written by Peter Claydon
#

# Default values:
config = {
    "hot_drinks": True,
    "name": "A Human Being",
    "alert": True,
    "ignore_time": 120,
    "window": 360,
    "threshold": 10,
    "daily_report_time": "02:00",
    "data_send_delay": 1
}

import sys
import os.path
import time
from cbcommslib import CbApp, CbClient
from cbconfig import *
import requests
import json
from twisted.internet import reactor
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from cbutils import nicetime
#from cbutils import timeCorrect
# Can be removed after all bridges are at a version that supports timeCorrect()
def timeCorrect():
    if time.time() < 32000000:
        return False
    else:
        return True

CONFIG_FILE                       = CB_CONFIG_DIR + "hot_drinks.config"
STATE_FILE                        = CB_CONFIG_DIR + "hot_drinks.state"
CID                               = "CID164"  # Client ID

class HotDrinks():
    def __init__(self):
        self.bridge_id = "unconfigured"
        self.kettleOn = False
        self.kettleOffTime = 0
        self.s = []
        self.waiting = False
        self.triggered = False
        self.power = None
        self.binary = []
        self.sensorOnTimes = {}
        self.counts = {
            "drinksInDay": 0,
            "kettlesInDay": 0
        }

    def initIDs(self, bridge_id, idToName):
        self.idToName = idToName
        self.bridge_id = bridge_id
        self.startMonitor()

    def addSensor(self, characteristic, sensorID):
        if characteristic == "power":
            self.power = sensorID
        elif characteristic == "binary":
            self.binary.append(sensorID)
        self.sensorOnTimes[sensorID] = 0
        self.cbLog("debug", "addSensor, sensorOnTimes: " + str(self.sensorOnTimes))

    def monitor(self):
        try:
            values = {
                "name": self.bridge_id + "/hot_drinks_in_day",
                "points": [[int(now*1000), self.counts["drinksInDay"]]]
            }
            self.storeValues(values)
            values = {
                "name": self.bridge_id + "/kettles_in_day",
                "points": [[int(now*1000), self.counts["kettlesInDay"]]]
            }
            self.storeValues(values)
            self.counts["drinksInDay"] = 0
            self.counts["kettlesInDay"] = 0
            self.startMonitor()
        except Exception as ex:
            self.cbLog("warning", "monitor failed. Exception. Type: " + str(type(ex)) + "exception: " +  str(ex.args))

    def startMonitor(self):
        try:
            if not timeCorrect():
                reactor.callLater(60, self.startMonitor)
            now = time.strftime("%Y %b %d %H:%M", time.localtime()).split()
            now[3] = config["daily_report_time"]
            midnight_e = time.mktime(time.strptime(" ".join(now), "%Y %b %d %H:%M")) + 86400
            wait = midnight_e - time.time() + 60
            self.cbLog("debug", "monitor set for " + str(int(wait)) + " seconds")
            reactor.callLater(wait, self.monitor)
        except Exception as ex:
            self.cbLog("warning", "startMonitor failed. Exception. Type: " + str(type(ex)) + "exception: " +  str(ex.args))

    def loadMonitor(self):
        try:
            if os.path.isfile(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    self.counts = json.load(f)
            self.cbLog("debug", "Loaded saved counts: " + str(self.counts))
        except Exception as ex:
            self.cbLog("warning", "Problem loading stored counts. Exception. Type: " + str(type(ex)) + "exception: " +  str(ex.args))
        finally:
            try:
                os.remove(STATE_FILE)
            except Exception as ex:
                self.cbLog("debug", "Cannot remove stored counts file. Exception. Type: " + str(type(ex)) + "exception: " +  str(ex.args))

    def saveMonitor(self):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.counts, f)
                self.cbLog("info", "Saved counts")
        except Exception as ex:
            self.cbLog("warning", "Problem saving counts. Type: " + str(type(ex)) + "exception: " +  str(ex.args))

    def onChange(self, sensor, timeStamp, value):
        try:
            #self.cbLog("debug", "onChange. sensor: " + self.idToName[sensor] + ", value: " + str(value) + ", time: " + nicetime(timeStamp) + ", kettleOn: " + str(self.kettleOn))
            if not timeCorrect():
                self.cbLog("info", "Data not processed as time is not correct")
                return 
            if sensor == self.power:
                if value > config["threshold"] and not self.kettleOn:
                    if timeStamp - self.kettleOffTime > config["ignore_time"]:
                        self.sensorOnTimes[sensor] = timeStamp
                        self.kettleOn = True
                        self.cbLog("debug", "kettle on")
                        values = {
                            "name": self.bridge_id + "/kettle",
                            "points": [[int(timeStamp*1000), 1]]
                        }
                        self.storeValues(values)
                        self.counts["kettlesInDay"] += 1
                        self.cbLog("debug", "kettlesInDay: " + str(self.counts["kettlesInDay"]))
                elif value < config["threshold"] and self.kettleOn:
                    self.kettleOn = False
                    self.triggered = False
                    self.kettleOffTime = timeStamp
                    self.cbLog("debug", "kettle off")
            elif sensor in self.binary and value == "on":
                self.sensorOnTimes[sensor] = timeStamp
            now = time.time()
            trigger = True
            #self.cbLog("debug", "onChange, sensorOnTimes: " + str(self.sensorOnTimes))
            for t in self.sensorOnTimes:
                if now - self.sensorOnTimes[t] > config["window"]:
                    trigger = False
            if trigger and not self.triggered:
                self.cbLog("debug", "triggered")
                self.triggered = True
                self.counts["drinksInDay"] += 1
                self.cbLog("debug", "drinksInDay: " + str(self.counts["drinksInDay"]))
                if config["alert"]:
                    msg = {"m": "alert",
                           "a": "Hot drinks being made by " + config["name"] + " at " + nicetime(now),
                           "t": now
                          }
                    self.client.send(msg)
                    self.cbLog("debug", "msg send to client: " + str(json.dumps(msg, indent=4)))
                values = {
                    "name": self.bridge_id + "/hot_drinks",
                    "points": [[int(now*1000), 1]]
                }
                self.storeValues(values)
        except Exception as ex:
            self.cbLog("warning", "HotDrinks onChange encountered problems. Exception: " + str(type(ex)) + str(ex.args))

    def sendValues(self):
        msg = {"m": "data",
               "d": self.s
               }
        self.cbLog("debug", "sendValues. Sending: " + str(json.dumps(msg, indent=4)))
        self.client.send(msg)
        self.s = []
        self.waiting = False

    def storeValues(self, values):
        self.s.append(values)
        if not self.waiting:
            self.waiting = True
            reactor.callLater(config["data_send_delay"], self.sendValues)

class App(CbApp):
    def __init__(self, argv):
        self.appClass = "monitor"
        self.state = "stopped"
        self.status = "ok"
        self.devices = []
        self.devServices = [] 
        self.idToName = {} 
        self.hotDrinks = HotDrinks()
        #CbApp.__init__ MUST be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        if action == "clear_error":
            self.state = "running"
        else:
            self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def onStop(self):
        self.hotDrinks.saveMonitor()
        self.client.save()

    def onConcMessage(self, message):
        #self.cbLog("debug", "onConcMessage, message: " + str(json.dumps(message, indent=4)))
        if "status" in message:
            if message["status"] == "ready":
                # Do this after we have established communications with the concentrator
                msg = {
                    "m": "req_config",
                    "d": self.id
                }
                self.client.send(msg)
        self.client.receive(message)

    def onClientMessage(self, message):
        self.cbLog("debug", "onClientMessage, message: " + str(json.dumps(message, indent=4)))
        global config
        if "config" in message:
            if "warning" in message["config"]:
                self.cbLog("warning", "onClientMessage: " + str(json.dumps(message["config"], indent=4)))
            else:
                try:
                    newConfig = message["config"]
                    copyConfig = config.copy()
                    copyConfig.update(newConfig)
                    if copyConfig != config or not os.path.isfile(CONFIG_FILE):
                        self.cbLog("debug", "onClientMessage. Updating config from client message")
                        config = copyConfig.copy()
                        with open(CONFIG_FILE, 'w') as f:
                            json.dump(config, f)
                        self.cbLog("info", "Config updated")
                        self.readLocalConfig()
                        # With a new config, send init message to all connected adaptors
                        for i in self.adtInstances:
                            init = {
                                "id": self.id,
                                "appClass": self.appClass,
                                "request": "init"
                            }
                            self.sendMessage(init, i)
                except Exception as ex:
                    self.cbLog("warning", "onClientMessage, could not write to file. Type: " + str(type(ex)) + ", exception: " +  str(ex.args))

    def onAdaptorData(self, message):
        #self.cbLog("debug", "onAdaptorData, message: " + str(json.dumps(message, indent=4)))
        if message["characteristic"] == "binary_sensor" or message["characteristic"] == "power":
            self.hotDrinks.onChange(message["id"], message["timeStamp"], message["data"])

    def onAdaptorService(self, message):
        #self.cbLog("debug", "onAdaptorService, message: " + str(json.dumps(message, indent=4)))
        if self.state == "starting":
            self.setState("running")
        self.devServices.append(message)
        serviceReq = []
        power = False
        biinary = False
        for p in message["service"]:
            if p["characteristic"] == "power":
                power = True
                self.hotDrinks.addSensor("power", message["id"])
            elif p["characteristic"] == "binary_sensor":
                binary = True
                self.hotDrinks.addSensor("binary", message["id"])
        if power:
            serviceReq.append({"characteristic": "power", "interval": 0})
        elif binary:
            serviceReq.append({"characteristic": "binary_sensor", "interval": 0})
        msg = {"id": self.id,
               "request": "service",
               "service": serviceReq}
        self.sendMessage(msg, message["id"])
        #self.cbLog("debug", "onAdaptorService, response: " + str(json.dumps(msg, indent=4)))

    def readLocalConfig(self):
        global config
        try:
            with open(CONFIG_FILE, 'r') as f:
                newConfig = json.load(f)
                self.cbLog("debug", "Read local config")
                config.update(newConfig)
        except Exception as ex:
            self.cbLog("warning", "Local config does not exist or file is corrupt. Exception: " + str(type(ex)) + str(ex.args))
        self.cbLog("debug", "Config: " + str(json.dumps(config, indent=4)))

    def onConfigureMessage(self, managerConfig):
        self.readLocalConfig()
        idToName2 = {}
        for adaptor in managerConfig["adaptors"]:
            adtID = adaptor["id"]
            if adtID not in self.devices:
                # Because managerConfigure may be re-called if devices are added
                name = adaptor["name"]
                friendly_name = adaptor["friendly_name"]
                self.cbLog("debug", "managerConfigure app. Adaptor id: " +  adtID + " name: " + name + " friendly_name: " + friendly_name)
                idToName2[adtID] = friendly_name
                self.idToName[adtID] = friendly_name.replace(" ", "_")
                self.devices.append(adtID)
        self.client = CbClient(self.id, CID, 10)
        self.client.onClientMessage = self.onClientMessage
        self.client.sendMessage = self.sendMessage
        self.client.cbLog = self.cbLog
        self.client.loadSaved()
        self.hotDrinks.cbLog = self.cbLog
        self.hotDrinks.client = self.client
        self.hotDrinks.initIDs(self.bridge_id, self.idToName)
        self.hotDrinks.loadMonitor()
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)
