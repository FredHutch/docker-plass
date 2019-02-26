FROM ubuntu:16.04

# Install prerequisites
RUN apt update && \
    apt-get install -y build-essential wget unzip python2.7 \
    python-dev git python-pip bats awscli curl ncbi-blast+ \
    lbzip2 pigz autoconf autogen libssl-dev cmake

RUN cd /usr/local && \
    git clone https://github.com/soedinglab/plass.git && \
    cd plass && \
    git checkout 005a5c53a8c2c8da3aa1b716f886d15dbb5caf72 && \
    git submodule update --init && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=. .. && \
    make -j 4 && make install && \
    export PATH="$(pwd)/bin/:$PATH"
