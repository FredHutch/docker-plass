FROM alpine:3.8
RUN apk add --no-cache gcc g++ cmake musl-dev vim git ninja zlib-dev bzip2-dev \
                       gawk bash grep libstdc++ libgomp zlib libbz2 bats \
                       python3 curl && \
    pip3 install awscli

RUN mkdir /opt && \
    cd /opt && \
    git clone https://github.com/soedinglab/plass.git && \
    cd plass && \
    git checkout d4071700cba48fd6551173329f3b71629cbf829e && \
    git submodule update --init

RUN cd /opt/plass && \
    ls -lhtr && \
    mkdir build_sse && \
    cd build_sse && \
    cmake -G Ninja -DHAVE_SSE4_1=1 -DCMAKE_BUILD_TYPE=Release /opt/plass && \
    ninja && ninja install

RUN cd /opt/plass && \
    mkdir build_avx && \
    cd build_avx && \
    cmake -G Ninja -DHAVE_AVX2=1 -DCMAKE_BUILD_TYPE=Release .. && \
    ninja && ninja install

RUN cp /opt/plass/build_sse/src/plass /usr/local/bin/plass_sse42 && \
    cp /opt/plass/build_avx/src/plass /usr/local/bin/plass_avx2 && \
    echo -e '#!/bin/bash\n\
    if $(grep -q -E "^flags.+avx2" /proc/cpuinfo); then\n\
    exec /usr/local/bin/plass_avx2 "$@"\n\
    else\n\
    exec /usr/local/bin/plass_sse42 "$@"\n\
    fi'\
    >> /usr/local/bin/plass
RUN chmod +x /usr/local/bin/plass

# Add the run script
ADD run.py /usr/local/bin/

# Run tests and then remove the folder
ADD tests /usr/plass/tests
RUN bats /usr/plass/tests/ && rm -r /usr/plass/tests/

