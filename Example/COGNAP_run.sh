#!/bin/bash
n_parralel=5 
count=0

in_path='/Storage/beliy/COGNAP/Incoming'
out_path='/Storage/beliy/COGNAP/Outcoming/'
q_path='/Storage/beliy/COGNAP/Quarantine/'
bk_path='/Storage/beliy/COGNAP/Backup/'
ini_file='/Storage/beliy/COGNAP/Configuration/Configurationfile_EEGBIDS_COGNAP.ini'
json_file='/Storage/beliy/COGNAP/Configuration/COG_'
log_path='/Storage/beliy/COGNAP/Log/'

run(){
  base=`basename "$1"`
  python3 eegBidsCreator.py -c $ini_file -j $json_file -o $out_path \
      -q --logfile $log_path/$base.log --log DEBUG $1
  retval=$?
}

#needed to exclude spaces and tabs from for separator
IFS=$'\n'


post_process(){
  base=`basename "$1"`
  retval="$2"
  echo "$base returned value: $retval";
  if [ $retval -ne 0 ]; then
    if [ -a "$q_path/$base" ]; then 
      rm -rf "$q_path/$base"
    fi
    cp -r "$in_path/$base" "$q_path/."
    cp "$log_path/$base.log" "$q_path/."
  else 
    dest=$bk_path/$base.tgz
    tar -C "$1/.." -czf "$dest" "$base"
    if [ $? -eq '0' ]; then
      true
    #  echo "rm -rf $1"
    #  rm -rf $in_path/$base
    else 
      echo "Filed to compress and move file $1"
      retval='200'
    fi
  fi
  echo "$retval $base" >> journal.txt
}

path="$in_path/*/"
shift
echo "Going into $path"
for file in `ls -d $path`; do 
  ((count++))
  (run "$file"; post_process "$file" "$retval")&
  if [ $(($count%$n_parralel)) -eq 0 ]; then
    wait
  fi
done
wait

