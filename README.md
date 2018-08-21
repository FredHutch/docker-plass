# docker-plass
Docker image running the protein-level assembler Plass

[![Docker Repository on Quay](https://quay.io/repository/fhcrc-microbiome/plass/status "Docker Repository on Quay")](https://quay.io/repository/fhcrc-microbiome/plass)

```

> run.py -h
usage: run.py [-h] --input INPUT --output-fastp OUTPUT_FASTP --output-log
              OUTPUT_LOG [--assembly-type ASSEMBLY_TYPE]
              [--genetic-code GENETIC_CODE] [--temp-folder TEMP_FOLDER]
              [--threads THREADS]

Wrapper script for Plass, handles transfer of inputs and outputs to and from
AWS S3.

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Location for input file. (Supported: sra:// or
                        ftp://).
  --output-fastp OUTPUT_FASTP
                        Path to write assembly in FASTP format. (Supported:
                        s3:// or local path).
  --output-log OUTPUT_LOG
                        Path to write logs. (Supported: s3:// or local path).
  --assembly-type ASSEMBLY_TYPE
                        'paired' or 'unpaired'. If 'paired', assume an
                        interleaved FASTQ input
  --genetic-code GENETIC_CODE
                        Genetic code to use for translation
  --temp-folder TEMP_FOLDER
                        Folder used for temporary files.
  --threads THREADS     Number of threads to use.
```