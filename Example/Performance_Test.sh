#!/bin/bash

n_tries=1000
cmd="python3 eegBidsCreator.py -q -t HN -s 080518 -a T233900 -j Example/COF_HN.json -o /Storage/beliy/COFITAGE/Public/BIDS/ -c test/Test.ini  /Storage/beliy/COFITAGE/Public/Emb/35d1ef92-1b65-42f3-aab4-b3d61076f448/ --conversion "
conv=(BV)

#First run command to insure it works properly
for c in ${conv[@]}; do
  rm "Perf_"$c".log" | true
  $cmd $c
  if [ $? != "0" ]; then
    echo "Command $cmd $c returned error"
    exit 0
  fi
done


for c in ${conv[@]}; do
  perf="Perf_"$c".log"
  for i in `seq 1 $n_tries`; do
    /usr/bin/time -f "%e %M" -o $perf -a $cmd $c
  done
done
