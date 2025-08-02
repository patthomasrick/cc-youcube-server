#!make

VERSION=0.0.1
DATETIME=$(shell date +%Y%m%d%H%M%S)

run:
	python src/youcube/youcube.py

docker: docker-buildx docker-buildx-nvidia

docker-buildx:
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t youcube:latest \
		-t youcube:$(VERSION) \
		-t youcube:$(DATETIME) \
		src/.

docker-buildx-nvidia:
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t youcube:nvidia \
		-t youcube:nvidia-$(VERSION) \
		-t youcube:nvidia-$(DATETIME) \
		src/. \
		--file src/Dockerfile.nvidia

# Legacy
docker-build:
	docker build --platform linux/amd64 \
		-t youcube:latest \
		-t youcube:$(VERSION) \
		-t youcube:$(DATETIME) \
		src/.

# Legacy
docker-build-nvidia:
	docker build --platform linux/amd64 \
		-t youcube:nvidia \
		-t youcube:nvidia-$(VERSION) \
		-t youcube:nvidia-$(DATETIME) \
		src/. \
		--file src/Dockerfile.nvidia

pylint:
	pylint src/youcube/*.py

pyspelling:
	pyspelling

cleanup:
ifeq ($(OS), Windows_NT)
	del /s /q src\youcube\data src\data src\youcube\__pycache__ src\__pycache__
else
	rm src/youcube/data src/data src/youcube/__pycache__ src/__pycache__ -Rv || true
endif

install-pylint:
	pip install pylint

install-pyspelling:
	pip install pyspelling

install-requirements:
ifeq ($(OS), Windows_NT)
	pip install -r src\requirements.txt
else
	pip install -r src/requirements.txt
endif
