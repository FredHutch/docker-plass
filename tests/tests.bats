#!/usr/bin/env bats

@test "Python is present" {
  result="$(python -c 'print(2+2)')"
  [ "$result" -eq 4 ]
}

@test "fastq-dump" {
	output="$(fastq-dump --stdout -X 2 SRR390728)"
	correct_output="$(cat /usr/plass/tests/fastq-dump-output.fastq)"

	[ "$output" == "$correct_output" ]
}

@test "AWS CLI v1.15.54" {
  v="$(aws --version 2>&1)"
  [[ "$v" =~ "1.15.54" ]]
}


@test "Curl is installed" {
  v="$(curl --version)"
}

@test "Run script in path" {
  v="$(run.py -h)"
}
