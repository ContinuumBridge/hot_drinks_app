# hot_drinks_app
App to detect the making of hot drinks and report, AID29
--------------------------------------------------------
This app has the following configuration (default values):

{
    "hot_drinks": true,
    "name": "A Human Being",
    "alert": false,
    "ignore_time": 120,
    "window": 360,
    "threshold": 10,
    "data_send_delay": 1
}

The fields have the following use:

|Field                  | Use                                                                                     |
|-----------------------|-----------------------------------------------------------------------------------------|
|hot_drinks             |Set to true to enable, false to disable |
|name                   |The name of a location or person. Used in alert emails and texts |
|alert                  |If set to true, an email and/or text will be sent when a hot drink is made |
|ignore_time            |No new report if the kettle is switched on again within this number of seconds of being switched off |
|window                 |All connected sensors must be triggered within window seconds for a hot drink to be reported |
|threshold              |The power drawn by the kettle for it to be considered to be on |
|data_send_delay        |Internal use. It is best to leave as 1 |

Function
--------
The app works as follows:

* A power sensor (eg: power meter socket) must be connected. A "kettle" is plugged into this, but in practice the "kettle" can be a coffee machine or any other electical appliance.
* Optionally, one or more binary sensors may be connected.
* As soon as the power drawn rises above the threshold, a "kettle" message will be sent to the ContinuumBridge data client.
* If binary sensors are connected, if the kettle and all the binary sensors are triggered within the window, then a "hot_drink" message will be sent.
* Once the kettle is turned off, no events will be reported again until after the ignore_time. This is to cater for the fact that some people will let a kettle boil and then reboil it before making a hot drink.
* If alerts are enabled, depending on the data client settings, emails and texts with the following form of message will be sent: "Hot drinks being made by A Human Being at 15:00:19, 07-10-2015".
