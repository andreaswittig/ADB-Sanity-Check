ADB-Sanity-Check
================

Check if all connected devices are visible in ADB

# Usage

Start server
```bash
nohup ./check_adb.py --listen 1234 > check_adb.out &
```
A server listen to `http://localhost:1234` is started.

# Response

Example Response
```json
{
  "adb": [
    "015d43ecbf24181c"
  ],
  "usb": {
    "015d43ecbf24181c": {
      "vendorID": "1004",
      "productID": "61f9",
      "description": "LG Electronics, Inc. Optimus (Various Models) MTP Mode",
      "productModel": "LG-P880",
      "adb": "someAdbId",
      "osVersion": "4.0.3",
      "name": "LG-P880"
    }
  },
  "missing": [
    "252d41exhd54180c"
  ]
}
```
