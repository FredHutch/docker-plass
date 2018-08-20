# docker-plass
Docker image running the protein-level assembler Plass

[![Docker Repository on Quay](https://quay.io/repository/fhcrc-microbiome/plass/status "Docker Repository on Quay")](https://quay.io/repository/fhcrc-microbiome/plass)

```

> run.py -h

usage: run.py [-h] --input INPUT --output-fastp OUTPUT_FASTP --output-log
              OUTPUT_LOG [--assembly-type ASSEMBLY_TYPE]
              [--temp-folder TEMP_FOLDER]

Wrapper script for Plass, handles transfer of inputs and outputs to and from
AWS S3.

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Location for input file(s). Comma-separated.
                        (Supported: sra://, s3://, or ftp://).
  --output-fastp OUTPUT_FASTP
                        Path to write assembly in FASTP format. (Supported:
                        s3:// or local path).
  --output-log OUTPUT_LOG
                        Path to write logs. (Supported: s3:// or local path).
  --assembly-type ASSEMBLY_TYPE
                        'paired' or 'unpaired'
  --temp-folder TEMP_FOLDER
                        Folder used for temporary files.
```