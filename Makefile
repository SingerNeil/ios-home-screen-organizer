PYTHON ?= /opt/homebrew/bin/python3.12
OUTPUT_APP ?= $(CURDIR)/build/理屏.app
INSTALL_APP ?= $(CURDIR)/dist/理屏.app

.PHONY: bootstrap build verify test install clean

bootstrap:
	./scripts/bootstrap.sh "$(PYTHON)"

build: bootstrap
	./scripts/build.sh "$(OUTPUT_APP)"

test:
	PYTHONPATH=backend "$(PYTHON)" -m unittest discover -s tests -v

verify: test
	./scripts/verify.sh "$(OUTPUT_APP)"

install: build verify
	./scripts/install-local.sh "$(OUTPUT_APP)" "$(INSTALL_APP)"

clean:
	rm -rf "$(CURDIR)/build" "$(CURDIR)/dist"
