PYTHON      ?= python3
VALIDATE    := $(PYTHON) validate.py
CORPUS_DIR  := iso7185-pascal-corpus
STAMP_DIR   := .validated

# -iname because source files come from upstream repos with mixed-case
# extensions (some ship as .PAS, matching validate.py's own case-insensitive
# suffix check).
PAS_FILES := $(shell find $(CORPUS_DIR) -iname '*.pas' | sort)

# Append ".ok" rather than substituting the .pas/.PAS suffix, so the
# mapping works regardless of extension case.
STAMPS := $(patsubst $(CORPUS_DIR)/%,$(STAMP_DIR)/%.ok,$(PAS_FILES))

.PHONY: all validate check clean list revalidate

all: validate

# Per-file, incremental validation: each .pas file gets its own stamp so
# `make validate` only re-runs validate.py on files that changed (or are
# new) since the last successful run. Safe to run with `make -j` for
# parallel checking, and `make -k validate` to see every failure in one
# pass instead of stopping at the first.
validate: $(STAMPS)
	@echo "$(words $(PAS_FILES)) files validated OK."

$(STAMP_DIR)/%.ok: $(CORPUS_DIR)/% validate.py
	@mkdir -p $(dir $@)
	$(VALIDATE) $< && touch $@

# Single aggregate pass over the whole corpus, matching plain
# `python3 validate.py iso7185-pascal-corpus` usage (no caching, always
# re-checks everything, prints every violation in one report).
check:
	$(VALIDATE) $(CORPUS_DIR)

# Drop all stamps and re-validate every file from scratch.
revalidate: clean validate

clean:
	rm -rf $(STAMP_DIR)

list:
	@echo "$(words $(PAS_FILES)) Pascal files under $(CORPUS_DIR)"
