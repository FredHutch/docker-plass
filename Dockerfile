FROM ubuntu:16.04

# Install prerequisites
RUN apt update && \
    apt-get install -y build-essential wget unzip python2.7 \
    python-dev git python-pip bats awscli curl ncbi-blast+ \
    lbzip2 pigz autoconf autogen libssl-dev cmake

RUN cd /usr/local && \
    git clone https://github.com/soedinglab/plass.git && \
    cd plass && \
    git checkout 53a2eff54d26d24ec3c9486020ebf15add15af9f && \
    git submodule update --init && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=. .. && \
    make -j 4 && \
    make install && \
    ln -s "$(pwd)/build/bin/plass" /usr/local/bin/
