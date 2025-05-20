#!/bin/bash

curl -X POST http://seasons-uno.local/json/settings -H "Content-Type: application/json" -d '{"live":true}'

curl -X POST http://seasons-quad.local/json/settings -H "Content-Type: application/json" -d '{"live":true}'

amixer sset 'Speaker' 90%

cd /home/dietpi/seasons/seasons
. ./env/bin/activate

while true; do
    ./seasons.py --led 300
    echo "Game ended. Restarting in 3 seconds..."
done
