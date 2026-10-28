PYTHON ?= .venv/bin/python
RELEASE := ../dihiggs_llp_recast-release-v1
DATASET := public/data/reference
SOURCE_CUTFLOW := $(RELEASE)/results/upstream/strong-bm1/cutflow.json
ATLAS_DIHIGGS_ROOT := ..
H2_MASSES := 130 150 170 200 250 300 330 345
MASS ?= 150

.PHONY: restore-data dataset local-dataset validate validate-local test frontend-test build check \
	h2-dataset h2-datasets validate-h2 catalog \
	h2-geometry-selection h2-geometry h2-geometries

# public/data and validation/h2_geometry_telemetry are not in git (594 MB); they live in lake commit
# LAKE_CID. Restore into a temp dir (the tracked files may be newer than the commit), copy only those two trees.
LAKE_CID := 20261013T002548Z-190699
restore-data:
	tmp=$$(mktemp -d) && python3 ../lake/lake.py restore $(LAKE_CID) $$tmp && \
	mkdir -p public validation && cp -a $$tmp/public/data public/ && \
	cp -a $$tmp/validation/h2_geometry_telemetry validation/ && rm -rf $$tmp

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

h2-dataset:
	$(PYTHON) -m preprocess.adapters.h2_mass_control \
		--atlas-dihiggs-root $(ATLAS_DIHIGGS_ROOT) \
		--mass $(MASS) \
		--output-dir public/data/h2-m$(MASS)

h2-datasets:
	for mass in $(H2_MASSES); do \
		$(PYTHON) -m preprocess.adapters.h2_mass_control \
			--atlas-dihiggs-root $(ATLAS_DIHIGGS_ROOT) \
			--mass $$mass \
			--output-dir public/data/h2-m$$mass; \
	done
	$(MAKE) catalog

validate-h2:
	for mass in $(H2_MASSES); do \
		$(PYTHON) -m preprocess.validate_h2_dataset \
			--atlas-dihiggs-root $(ATLAS_DIHIGGS_ROOT) \
			--dataset-dir public/data/h2-m$$mass \
			--mass $$mass \
			--report validation/h2_m$${mass}_validation.json || exit 1; \
	done

catalog:
	$(PYTHON) -m preprocess.generate_catalog --data-dir public/data

h2-geometry-selection:
	$(PYTHON) -m preprocess.geometry_selection --atlas-dihiggs-root $(ATLAS_DIHIGGS_ROOT) \
		$(foreach m,$(H2_MASSES),--mass $(m)) --output-dir validation/h2_geometry_selection

h2-geometry:
	ATLAS_DIHIGGS_ROOT=$(ATLAS_DIHIGGS_ROOT) bash preprocess/instrumentation/run_h2_geometry.sh $(MASS)

h2-geometries:
	for mass in $(H2_MASSES); do \
		ATLAS_DIHIGGS_ROOT=$(ATLAS_DIHIGGS_ROOT) bash preprocess/instrumentation/run_h2_geometry.sh $$mass || exit 1; \
	done

test:
	$(PYTHON) -m pytest

frontend-test:
	npm --prefix frontend test

build:
	npm --prefix frontend run build

check: validate validate-local validate-h2 test frontend-test build
