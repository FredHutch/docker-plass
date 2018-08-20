FROM ubuntu:16.04
MAINTAINER sminot@fredhutch.org

# Install prerequisites
RUN apt update && \
    apt-get install -y build-essential wget unzip python2.7 python-dev git python-pip bats awscli curl g++ cmake zlib1g-dev libbz2-dev pigz && \
    pip install awscli==1.15.54

# Install Plass
RUN cd /usr/local && \
    wget https://mmseqs.com/plass/plass-static_sse41.tar.gz && \
    tar xvzf plass-static_sse41.tar.gz && \
    export PATH=$(pwd)/plass/bin/:$PATH && \
    rm plass-static_sse41.tar.gz

# Install the SRA toolkit
RUN cd /usr/local/bin && \
    wget https://ftp-trace.ncbi.nlm.nih.gov/sra/sdk/2.8.2/sratoolkit.2.8.2-ubuntu64.tar.gz && \
    tar xzvf sratoolkit.2.8.2-ubuntu64.tar.gz && \
    ln -s /usr/local/bin/sratoolkit.2.8.2-ubuntu64/bin/* /usr/local/bin/ && \
    rm sratoolkit.2.8.2-ubuntu64.tar.gz

# Install CMake3.11
RUN cd /usr/local/bin && \
    wget https://cmake.org/files/v3.11/cmake-3.11.0-Linux-x86_64.tar.gz && \
    tar xzvf cmake-3.11.0-Linux-x86_64.tar.gz && \
    ln -s $PWD/cmake-3.11.0-Linux-x86_64/bin/cmake /usr/local/bin/

# Install fastq-pair
RUN cd /usr/local && \
    git clone https://github.com/linsalrob/fastq-pair.git && \
    cd fastq-pair && \
    git checkout 4ae91b0d9074410753d376e5adfb2ddd090f7d85 && \
    mkdir build && \
    cd build && \
    cmake ../ && \
    make && \
    make install

# Add the run script
ADD run.py /usr/local/bin/

# Run tests and then remove the folder
ADD tests /usr/plass/tests
RUN bats /usr/plass/tests/ && rm -r /usr/plass/tests/

