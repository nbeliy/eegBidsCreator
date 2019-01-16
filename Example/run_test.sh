#!/bin/bash
n_parralel=5 
count=0

def_path='/media/beliy/KINGSTON/Memodyn/ForTest/Emb'
ini_file="Example/COF_BH.ini"
out_path="output/ForTest"

run(){
  base=`basename $1`
  base=${base:0:8}
  python3 eegBidsCreator.py -c $ini_file -a $base -o $out_path -q --logfile $out_path/$base.log $file
  retval="$base returned value: $?"
}

if [ $# -eq 0 ]; then
  set -- $def_path
fi  

while [ $# -gt 0 ]; do
  path="$1/*"
  shift
  echo "Going into $path"
  for file in `ls -d $path`; do 
    ((count++))
    base=`basename $file`
    base=${base:0:8}
    (run $file; echo $retval)&
    if [ $(($count%$n_parralel)) -eq 0 ]; then
      wait
    fi
  done
  wait

done
