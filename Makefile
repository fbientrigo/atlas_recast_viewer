PYTHON ?= .venv/bin/python
RELEASE := ../dihiggs_llp_recast-release-v1
DATASET := public/data/reference
SOURCE_CUTFLOW := $(RELEASE)/results/upstream/strong-bm1/cutflow.json

.PHONY: dataset local-dataset validate validate-local test frontend-test build check

dataset:
	$(PYTHON) -m preprocess.adapters.original_recast \
		--source-cutflow $(SOURCE_CUTFLOW) \
		--source-benchmark-manifest $(RELEASE)/benchmarks/upstream/strong-bm1/manifest.json \
		--source-benchmark $(RELEASE)/benchmarks/upstream/strong-bm1/benchmark.json \
		--source-checkout $(RELEASE)/external/recastingCodes \
		--output-dir $(DATASET)

validate:
	$(PYTHON) -m preprocess.validate_dataset \
		--dataset-dir $(DATASET) \
		--source-cutflow $(SOURCE_CUTFLOW) \
		--report validation/reference_validation.json

local-dataset:
	bash preprocess/instrumentation/run_local_reference.sh

validate-local:
	$(PYTHON) -m preprocess.validate_local_instrumentation \
		--dataset-dir public/data/local-reference \
		--upstream-log validation/local_reference/upstream.log \
		--instrumented-log validation/local_reference/instrumented.log \
		--report validation/local_instrumentation_validation.json

test:
	$(PYTHON) -m pytest

frontend-test:
	npm --prefix frontend test

build:
	npm --prefix frontend run build

check: validate validate-local test frontend-test build
