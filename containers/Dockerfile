## base container
FROM python:3.8 as base_container
RUN apt-get update \
    && apt-get install --yes rename procps curl zsh git editorconfig \
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
CMD ["/bin/bash"]

## main container
FROM base_container
# adding opencontainer labels to link registry to github repository
LABEL org.opencontainers.image.title="enzyme-screening-platform-opentrons"
LABEL org.opencontainers.image.description="End-to-end eznyme screening platform for argB."
LABEL org.opencontainers.image.url="https://github.com/stracquadaniolab/enzyme-screening-platform-opentrons"
LABEL org.opencontainers.image.documentation="https://github.com/stracquadaniolab/enzyme-screening-platform-opentrons"
LABEL org.opencontainers.image.source="https://github.com/stracquadaniolab/enzyme-screening-platform-opentrons"
LABEL org.opencontainers.image.vendor="stracquadaniolab"
LABEL org.opencontainers.image.authors="Martyna Kasprzyk"
LABEL org.opencontainers.image.revision="v0.0.0"

COPY containers/requirements.txt requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt
