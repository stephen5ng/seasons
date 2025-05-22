#!/bin/bash

curl -X POST http://seasons-uno.local/json/settings -H "Content-Type: application/json" -d '{"live":true}'

amixer sset 'Speaker' 90%

cd /home/dietpi/seasons/seasons
. ./env/bin/activate

while true; do
    ./seasons.py --led 300
    sleep 60
done
