#!/bin/bash

if [[ -n log.txt ]]; then
	rm log.txt
fi

for site in $(cat tistories.txt); do
	python3 ./tty.py "$site" --test >> log.txt
done
