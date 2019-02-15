function x = meeg_test(D1, D2, chann, toffset)
%% Compares point-by-point two channels named 'chann' from
%% meeg D1 and D2. Return the vector of relative differences
%% The channels are ynchronized by Lights-off event
%% tooffset allows to fine-tune synchronisation
 
  name1 = D1.fname;
  name2 = D2.fname;

  dsec = double(D1.info.date(3) - D2.info.date(3))*24*60*60;
  dsec = dsec + double(D1.info.hour(1) - D2.info.hour(1))*60*60;
  dsec = dsec + double(D1.info.hour(2) - D2.info.hour(2))*60;
  dsec = dsec + (double(D1.info.hour(3)) - double(D2.info.hour(3)));

  offset1 = 0;
  offset2 = 0;

  if dsec > 0 
    offset2 = int64(dsec*D1.fsample);
  else
    offset1 = int64(-dsec*D2.fsample);
  end
  fprintf('%s %f %d\n', name1, dsec, offset1);
  fprintf('%s %f %d\n', name2, dsec, offset2);

  index1 = 0;
  index2 = 0;
  for i = 1:size(D1.chanlabels,2)
    if strcmp(D1.chanlabels{i},chann)
      index1 = i;
      break
    end
  end

  for i = 1:size(D2.chanlabels,2)
    if strcmp(D2.chanlabels{i},chann)
      index2 = i;
      break
    end
  end

  if index1 == 0
    fprintf('Channel <%s> not found in %s\n', chann, name1 );
    return
  end
  if index2 == 0
    fprintf('Channel <%s> not found in %s\n', chann, name2 );
    return
  end
  fprintf('%d %d\n',index1, index2);

  ev1 = D1.events;
  ev2 = D2.events;

  t1 = 0;
  t2 = 0;
  for ev = ev1
    if strcmp(ev.type, 'Lights_off_COGNAP')
      t1 = ev.time;
      break
    end
  end

  for ev = ev2
    if strcmp(ev.type, 'Lights_off_COGNAP')
      t2 = ev.time;
      break
    end
  end

  pos1 = int64(t1*D1.fsample);
  pos2 = int64(t2*D2.fsample);%+toffset;
  fprintf('%d\t%d\t%d\n', pos1,pos2, pos1-pos2);
  fprintf('%f\t%f\n',D1(index1,pos1), D2(index2, pos2));
  fprintf('%f\n', (D1(index1,pos1) - D2(index2, pos2))/D1(index1,pos1))
  dsec = round(dsec + (t1 - t2),3)*10;
  fprintf('dsec: %f\t%f\n', dsec, dsec*D1.fsample);
  toffset = -dsec*D1.fsample;
  pos2 = pos2 + toffset;
  if pos2 < 0
    pos2 = pos2 - toffset;
    pos1 = pos1 - toffset;
  end
 

  offset1 = 0;
  offset2 = 0;
  if pos1 > pos2 
    offset1 = pos1 - pos2;
  else
    offset2 = pos2 - pos1;
  end

  s = min(D1.nsamples - offset1 - 1, D2.nsamples - offset2 - 1);
  disp(offset1);
  disp(offset2);
  x = (D1(index1, offset1+1:offset1+s) - D2(index2, offset2+1:offset2+s))./D1(index1, offset1+1:offset1+s);
  [M,I] = min(x);
  fprintf('Minimum %f: %d:\n\tD1 = %f\n\tD2=%f\n', M, I, D1(index1, I+offset1), D2(index2, I+offset2));
  [M,I] = max(x);
  fprintf('Maximum %f: %d:\n\tD1 = %f\n\tD2=%f\n', M, I, D1(index1, I+offset1), D2(index2, I+offset2));
end

