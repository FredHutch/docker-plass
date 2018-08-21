#!/usr/bin/env python3
"""Wrapper script for Plass, handles transfer of inputs and outputs to and from AWS S3."""

import os
import sys
import uuid
import gzip
import json
import shutil
import logging
import argparse
import traceback
import subprocess


def get_reads_from_url(input_str, temp_folder):
    """Get a set of reads from a URL -- return the downloaded filepath."""
    logging.info("Getting reads from {}".format(input_str))

    filename = input_str.split('/')[-1]
    local_path = os.path.join(temp_folder, filename)

    if not input_str.startswith(('s3://', 'ftp://', 'https://', 'http://')):
        logging.info("Treating as local path")
        assert os.path.exists(input_str)
        logging.info("Making copy in temporary folder")
        shutil.copyfile(input_str, local_path)
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
        for line in stdout.decode("utf-8").split('\n'):
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


def deinterleave(input_fp):
    fwd_handle = open(input_fp + "_fwd.fastq", "wt")
    rev_handle = open(input_fp + "_rev.fastq", "wt")

    if input_fp.endswith("gz"):
        interleaved_handle = gzip.open(input_fp, "rt")
    else:
        interleaved_handle = open(input_fp, "rt")

    read_ix = 0
    buffer = []
    for line in interleaved_handle:
        buffer.append(line)

        if len(buffer) == 4:
            assert buffer[0][0] == '@'
            assert buffer[2][0] == '+'
            if read_ix % 2 == 0:
                fwd_handle.write("".join(buffer))
            else:
                rev_handle.write("".join(buffer))
            read_ix += 1
            buffer = []

    interleaved_handle.close()
    fwd_handle.close()
    rev_handle.close()

    return input_fp + "_fwd.fastq", input_fp + "_rev.fastq"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Wrapper script for Plass, handles transfer of inputs and outputs to and from AWS S3.
    """)

    parser.add_argument("--input",
                        type=str,
                        required=True,
                        help="""Location for input file.
                                (Supported: sra:// or ftp://).""")
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
                        help="""'paired' or 'unpaired'. If 'paired', assume an interleaved FASTQ input""")
    parser.add_argument("--genetic-code",
                        type=int,
                        default=11,
                        help="""Genetic code to use for translation""")
    parser.add_argument("--temp-folder",
                        type=str,
                        default='/scratch',
                        help="Folder used for temporary files.")
    parser.add_argument("--threads",
                        type=int,
                        default=1,
                        help="Number of threads to use.")

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

    assert args.genetic_code in [
        1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 
        21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
    ]

    # Set up a temporary folder
    temp_folder = os.path.join(args.temp_folder, str(uuid.uuid4()))
    assert os.path.exists(temp_folder) is False
    os.mkdir(temp_folder)

    # Get the input file
    try:
        input_file = get_reads_from_url(args.input, temp_folder)
    except:
        exit_and_clean_up(temp_folder)

    # Output file for assembly
    assembly_fp = os.path.join(temp_folder, "output.fastp")

    # If the assembly should be paired, deinterleave the input file
    if args.assembly_type == "paired":
        logging.info("Deinterleaving " + input_file)
        fwd, rev = deinterleave(input_file)

        # Run Plass in paired-end mode
        try:
            run_cmds([
                "plass", 
                "assemble", 
                "--use-all-table-starts",
                "--translation-table",
                str(args.genetic_code),
                "--threads", 
                str(args.threads), 
                "-k", 
                "0", 
                "--filter-proteins", 
                "0", 
                fwd,
                rev, 
                assembly_fp, 
                temp_folder + "/"
            ])
        except:
            exit_and_clean_up(temp_folder)

    else:
        # Run Plass in single-end mode
        try:
            run_cmds([
                "plass",
                "assemble",
                "--use-all-table-starts",
                "--translation-table",
                str(args.genetic_code),
                "--threads",
                str(args.threads),
                "-k",
                "0",
                "--filter-proteins",
                "0",
                input_file,
                assembly_fp,
                temp_folder + "/"
            ])
        except:
            exit_and_clean_up(temp_folder)

    try:
        assert os.path.exists(assembly_fp)
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
