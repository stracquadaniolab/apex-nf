## base container
FROM python:3.9 as base_container

# Install R
RUN apt-get update && \
    apt-get install --yes \
    rename procps curl zsh git editorconfig pandoc r-base && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Installing R packages
RUN R -e "install.packages(c('tidyverse', 'rjson', 'png', 'tinytex'), dependencies=TRUE, repos='http://cran.rstudio.com/')"

# Install TinyTeX via tinytex R package
RUN R -e "tinytex::install_tinytex()"

CMD ["/bin/bash"]

## main container
FROM base_container
# adding opencontainer labels to link registry to github repository
LABEL org.opencontainers.image.title="apex-nf"
LABEL org.opencontainers.image.description="APEX: Automated Protein EXpression in Escherichia coli"
LABEL org.opencontainers.image.url="https://github.com/stracquadaniolab/apex-nf"
LABEL org.opencontainers.image.documentation="https://github.com/stracquadaniolab/apex-nf"
LABEL org.opencontainers.image.source="https://github.com/stracquadaniolab/apex-nf"
LABEL org.opencontainers.image.vendor="stracquadaniolab"
LABEL org.opencontainers.image.authors="Martyna Kasprzyk"
LABEL org.opencontainers.image.revision="v0.2.0"
COPY requirements.txt requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt