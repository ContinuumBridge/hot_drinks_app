# hot_drinks_app
App to detect the making of hot drinks and report, AID29
--------------------------------------------------------
This app has the following configuration (default values):

config = {
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
