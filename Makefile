.PHONY: test

test:
	cd scripts && python3 -m unittest discover -s tests -t .
