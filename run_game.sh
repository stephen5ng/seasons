#!/bin/bash

curl -X POST http://wled-e56890.local/json/settings -H "Content-Type: application/json" -d '{"live":true}'

curl -X POST http://wled-f4afec.local/json/settings -H "Content-Type: application/json" -d '{"live":true}'

. ./env/bin/activate
./seasons.py --led 300
