#!/usr/bin/env python
"""Wrapper script for Plass, handles transfer of inputs and outputs to and from AWS S3."""

import os
import sys
import uuid
import json
import shutil
import logging
import argparse
import traceback
import subprocess


def get_sra(accession_string, temp_folder):
    """Get the FASTQ for an SRA accession."""
    logging.info("Downloading {} from SRA".format(accession_string))

    local_path = os.path.join(temp_folder, "reads.fastq")
    logging.info("Local path: {}".format(local_path))

    # Download via fastq-dump
    for accession in accession_string.split(","):
        logging.info("Downloading {} via fastq-dump".format(accession))

        accession_joined_fp = os.path.join(
            temp_folder, accession + ".all.fastq")

        run_cmds([
            "prefetch", accession
        ])
        # Output the _1.fastq and _2.fastq files
        run_cmds([
            "fastq-dump", "--split-files",
            "--defline-seq", "@$ac.$si.$sg/$ri",
            "--defline-qual", "+",
            "--outdir", temp_folder, accession
        ])
        r1 = os.path.join(temp_folder, accession + "_1.fastq")
        r2 = os.path.join(temp_folder, accession + "_2.fastq")
        assert os.path.exists(r1)

        # If there are two reads created, interleave them
        if os.path.exists(r2):
            r1_paired = os.path.join(
                temp_folder, accession + "_1.fastq.paired.fq")
            r2_paired = os.path.join(
                temp_folder, accession + "_2.fastq.paired.fq")

            # Isolate the properly paired filed
            run_cmds([
                "fastq_pair", r1, r2
            ])
            assert os.path.exists(r1_paired)
            assert os.path.exists(r2_paired)
            logging.info("Removing raw downloaded FASTQ files")
            os.remove(r1)
            os.remove(r2)

            # Interleave the two paired files
            logging.info("Interleaving the paired FASTQ files")
            interleave_fastq(r1_paired, r2_paired, accession_joined_fp)
            assert os.path.exists(accession_joined_fp)
            logging.info("Removing split and filtered FASTQ files")
            os.remove(r1_paired)
            os.remove(r2_paired)
        else:
            # Otherwise, just make the _1.fastq file the output
            logging.info("Using {} as the output file".format(r1))
            run_cmds(["mv", r1, accession_joined_fp])

        # Remove the cache file, if any
        logging.info("Removing cached SRA files")
        run_cmds(["find", temp_folder, "-name", "*.sra", "-delete"])

        # Append this set of reads to the total
        logging.info("Adding reads from {} to the total".format(accession))
        with open(local_path, "at") as fo:
            for line in open(accession_joined_fp, "rt"):
                fo.write(line)
        logging.info("Removing temporary file " + accession_joined_fp)
        os.remove(accession_joined_fp)

    # Compress the FASTQ file
    logging.info("Compress the FASTQ file")
    run_cmds(["pigz", local_path])
    local_path = local_path + ".gz"

    # Return the path to the file
    logging.info("Done fetching " + accession_string)
    return local_path


def interleave_fastq(fwd_fp, rev_fp, comb_fp):
    fwd = open(fwd_fp, "rt")
    rev = open(rev_fp, "rt")
    nreads = 0
    with open(comb_fp, "wt") as fo:
        while True:
            fwd_read = [fwd.readline() for ix in range(4)]
            rev_read = [rev.readline() for ix in range(4)]
            if any([l == '' for l in fwd_read]):
                break
            assert any([l == '' for l in rev_read]) is False
            nreads += 1
            fo.write(''.join(fwd_read))
            fo.write(''.join(rev_read))
    fwd.close()
    rev.close()
    logging.info("Interleaved {:,} pairs of reads".format(nreads))


def get_reads_from_url(input_str, temp_folder):
    """Get a set of reads from a URL -- return the downloaded filepath."""
    logging.info("Getting reads from {}".format(input_str))

    filename = input_str.split('/')[-1]
    local_path = os.path.join(temp_folder, filename)

    if not input_str.startswith(('s3://', 'sra://', 'ftp://', 'https://', 'http://')):
        logging.info("Treating as local path")
        assert os.path.exists(input_str)
        logging.info("Making symbolic link in temporary folder")
        os.symlink(input_str, local_path)
        return local_path

    # Make sure the temp folder ends with '/'
    if not temp_folder.endswith("/"):
        temp_folder = "{}/".format(temp_folder)

    logging.info("Filename: " + filename)
    logging.info("Local path: " + local_path)

    # Get files from AWS S3
    if input_str.startswith('s3://'):
        logging.info("Getting reads from S3")
        run_cmds([
            'aws',
            's3',
            'cp',
            '--quiet',
            '--sse',
            'AES256',
            input_str,
            temp_folder
        ])
        return local_path

    # Get files from an FTP server or HTTP
    elif input_str.startswith(('ftp://', 'https://', 'http://')):
        logging.info("Getting reads from FTP / HTTP(S)")
        run_cmds(['wget', '-P', temp_folder, input_str])
        return local_path

    # Get files from SRA
    elif input_str.startswith('sra://'):
        accession = filename
        logging.info("Getting reads from SRA: " + accession)
        local_path = get_sra(accession, temp_folder)

        return local_path

    else:
        msg = "Did not recognize prefix to fetch reads: " + input_str
        raise Exception(msg)


def run_cmds(commands, retry=0, catchExcept=False):
    """Run commands and write out the log, combining STDOUT & STDERR."""
    logging.info("Commands:")
    logging.info(' '.join(commands))
    p = subprocess.Popen(commands,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate()
    exitcode = p.wait()
    if stdout:
        logging.info("Standard output of subprocess:")
        for line in stdout.split('\n'):
            logging.info(line)
    if stderr:
        logging.info("Standard error of subprocess:")
        for line in stderr.split('\n'):
            logging.info(line)

    # Check the exit code
    if exitcode != 0 and retry > 0:
        msg = "Exit code {}, retrying {} more times".format(exitcode, retry)
        logging.info(msg)
        run_cmds(commands, retry=retry - 1)
    elif exitcode != 0 and catchExcept:
        msg = "Exit code was {}, but we will continue anyway"
        logging.info(msg.format(exitcode))
    else:
        assert exitcode == 0, "Exit code {}".format(exitcode)


def upload_file(local_fp, remote_fp):
    """Copy a file from inside the container to the output path."""

    assert local_fp.endswith("/") is False
    assert remote_fp.endswith("/") is False

    if remote_fp.startswith('s3://'):
        # Copy to S3
        run_cmds(
            ['aws', 's3', 'cp', '--quiet',
             '--sse', 'AES256',
             local_fp, remote_fp])
    else:
        # Copy to local folder
        run_cmds(['mv', local_fp, remote_fp])


def exit_and_clean_up(temp_folder):
    """Log the error messages and delete the temporary folder."""
    # Capture the traceback
    logging.info("There was an unexpected failure")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for line in traceback.format_tb(exc_traceback):
        logging.info(line)

    # Delete any files that were created for this sample
    logging.info("Removing temporary folder: " + temp_folder)
    shutil.rmtree(temp_folder)

    # Exit
    logging.info("Exit type: {}".format(exc_type))
    logging.info("Exit code: {}".format(exc_value))
    sys.exit(exc_value)


def set_up_sra_cache_folder(temp_folder):
    """Set up the fastq-dump cache folder within the temp folder."""
    logging.info("Setting up fastq-dump cache within {}".format(temp_folder))

    cache_folder = os.path.join(temp_folder, "sra_cache")
    os.mkdir(cache_folder)

    run_cmds([
        "vdb-config", "--root", "-s", "/repository/user/main/public/root={}".format(
            cache_folder)
    ], catchExcept=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Wrapper script for Plass, handles transfer of inputs and outputs to and from AWS S3.
    """)

    parser.add_argument("--input",
                        type=str,
                        required=True,
                        help="""Location for input file(s). Comma-separated.
                                (Supported: sra://, s3://, or ftp://).""")
    parser.add_argument("--output-fastp",
                        type=str,
                        required=True,
                        help="""Path to write assembly in FASTP format.
                                (Supported: s3:// or local path).""")
    parser.add_argument("--output-log",
                        type=str,
                        required=True,
                        help="""Path to write logs.
                                (Supported: s3:// or local path).""")
    parser.add_argument("--assembly-type",
                        type=str,
                        default="unpaired",
                        help="""'paired' or 'unpaired'""")
    parser.add_argument("--temp-folder",
                        type=str,
                        default='/scratch',
                        help="Folder used for temporary files.")

    args = parser.parse_args()

    # Set up logging
    log_fp = '{}.log.txt'.format(uuid.uuid4())
    fmt = '%(asctime)s %(levelname)-8s [PLASS] %(message)s'
    logFormatter = logging.Formatter(fmt)
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    # Write to file
    fileHandler = logging.FileHandler(log_fp)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    # Also write to STDOUT
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    # Set up a temporary folder
    temp_folder = os.path.join(args.temp_folder, str(uuid.uuid4()))
    assert os.path.exists(temp_folder) is False
    os.mkdir(temp_folder)

    try:
        set_up_sra_cache_folder(temp_folder)
    except:
        exit_and_clean_up(temp_folder)

    # Get the input file
    try:
        input_file = get_reads_from_url(args.input, temp_folder)
    except:
        exit_and_clean_up(temp_folder)

    # Run Plass
    assembly_fp = os.path.join(temp_folder, "output.fastp")
    try:
        run_cmds([
            "plass", "assemble", input_file, assembly_fp, temp_folder
        ])
    except:
        exit_and_clean_up(temp_folder)

    # Return the results
    try:
        upload_file(assembly_fp, args.output_fastp)
        upload_file(log_fp, args.output_log)
    except:
        exit_and_clean_up(temp_folder)

    # Stop logging
    logging.info("Done")
    logging.shutdown()

    # Delete the temporary folder
    shutil.rmtree(temp_folder)
