#!/usr/bin/env bats

@test "Python is present" {
  result="$(python3 -c 'print(2+2)')"
  [ "$result" -eq 4 ]
}

@test "AWS CLI" {
  v="$(aws --version 2>&1)"
  [[ "$v" =~ "aws-cli" ]]
}

@test "Curl is installed" {
  v="$(curl --version)"
}

@test "Plass in path" {
  v="$(plass -h)"
}

@test "Run script in path" {
  v="$(run.py -h)"
}

@test "Deinterleave function" {
  cd /usr/local/bin/
  
  python3 -c "from run import deinterleave; deinterleave('/usr/plass/tests/ERR1878174.100k.fastq.gz')"
  gunzip /usr/plass/tests/ERR1878174.100k.fastq.gz
  python3 -c "from run import deinterleave; deinterleave('/usr/plass/tests/ERR1878174.100k.fastq')"

  # Interleaved file has 100k reads (4 lines per read)
  (( $(cat /usr/plass/tests/ERR1878174.100k.fastq | wc -l ) == 400000 ))

  # Deinterleaved file has 50k reads each (4 lines per read)
  (( $(cat /usr/plass/tests/ERR1878174.100k.fastq_fwd.fastq | wc -l ) == 200000 ))
  (( $(cat /usr/plass/tests/ERR1878174.100k.fastq_rev.fastq | wc -l ) == 200000 ))
  (( $(cat /usr/plass/tests/ERR1878174.100k.fastq.gz_fwd.fastq | wc -l ) == 200000 ))
  (( $(cat /usr/plass/tests/ERR1878174.100k.fastq.gz_rev.fastq | wc -l ) == 200000 ))

  gzip /usr/plass/tests/ERR1878174.100k.fastq

}

@test "Assemble paired" {
  cd /usr/plass/tests/

  run.py --input ERR1878174.fastq.gz --output-fastp ERR1878174.paired.fastp --output-log ERR1878174.paired.log --assembly-type paired --temp-folder .

  [[ -s ERR1878174.paired.fastp ]]
}

# @test "Assemble unpaired" {
#   cd /usr/plass/tests/

#   run.py --input ERR1878174.fastq.gz --output-fastp ERR1878174.unpaired.fastp --output-log ERR1878174.unpaired.log --assembly-type unpaired --temp-folder .

#   [[ -s ERR1878174.unpaired.fastp ]]
# }
