#!/bin/bash

n_tries=1000
cmd="python3 eegBidsCreator.py -t HN -s 080518 -a T233900 -j Example/COF_HN.json -o output -c test/Test.ini  /media/beliy/KINGSTON/Memodyn/ForTest/Emb/35d1ef92-1b65-42f3-aab4-b3d61076f448/ --conversion "
conv=(BV EDF)

for c in ${conv[@]}; do
  perf="Perf_"$c".log"
  for i in `seq 1 $n_tries`; do
    /usr/bin/time -f "%e %M" -o $perf -a $cmd $c
  done
done
