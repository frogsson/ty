#!/bin/bash

if [[ -n log.txt ]]; then
	rm log.txt
fi

for site in $(cat tistories.txt); do
	# python3 ./ty --debug "$site" | tee -a log.txt
	echo "__ RUNNING $site __"
	if [[ ! -d tytest ]]; then mkdir "tytest"; fi
	python3 ./ty -o "$site" "tytest" | tee -a log.txt
done
