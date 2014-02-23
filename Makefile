# Copyright (C) 2013 Craig Phillips.  All rights reserved.
#
# GSync top level makefile.

all:
	@echo "Run make with the following targets:"
	@echo "    install        Install the GSync application in this system"
	@echo "    uninstall      Remove the GSync application from this system"

reverse = $(if $(1),$(call reverse,\
	$(wordlist 2,$(words $(1)),$(1)))) $(firstword $(1)\
)
reverse = $(shell printf "%s\n" $(strip $1) | tac)

MANIFEST:= $(if $(wildcard MANIFEST),$(shell cat MANIFEST),)
RM_MANIFEST:= $(addprefix uninstall_,\
	$(filter-out \
		%/bin/ \
		%/dist-packages/ \
		,$(wildcard $(MANIFEST) $(call reverse,$(sort $(dir $(MANIFEST))))),\
	)\
)

.PHONY: $(RM_MANIFEST)

$(RM_MANIFEST): uninstall_% : %
	@[ -e "$<" ] || { \
	    echo >&2 "Error: GSync is not installed" ; \
		exit 1 ; \
	}
	@[ $(shell id -u) -eq 0 ] || { \
		echo >&2 "Error: You must be root" ; \
		exit 1 ; \
	}
	@if [ -d $< ] ; then \
		rmdir -v $< ; \
	else \
		rm -vf $< ; \
	fi

uninstall: $(RM_MANIFEST)
	@echo "Uninstall complete"

install: setup.py
	@[ $(shell id -u) -eq 0 ] || { \
		echo >&2 "Error: You must be root" ; \
		exit 1 ; \
	}
	./setup.py install --record MANIFEST
	find /usr/local/lib/python2.7/dist-packages/ ! -perm -o=r -exec chmod o+r {} \;
