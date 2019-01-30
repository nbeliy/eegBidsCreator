import mne
import datetime, math
from numpy import histogram
import matplotlib.pyplot as plt
from DataStructure.Embla.Channel import EbmChannel

chan_idx = 2

emb_raw = mne.io.read_raw_edf("/media/beliy/KINGSTON/Memodyn/ForTest/EDF/35d1ef92-1b65-42f3-aab4-b3d61076f448/Traces.edf", stim_channel=False)
edf_raw = mne.io.read_raw_edf("output/sub-COF098_HN_080518_T233900/ses-080519/eeg/sub-COF098_HN_080518_T233900_ses-080519_task-HN_acq-T233900_eeg.edf", preload=True, stim_channel=False)
conv_raw = mne.io.read_raw_brainvision("output/sub-COF098_HN_080518_T233900/ses-080518/eeg/sub-COF098_HN_080518_T233900_ses-080518_task-HN_acq-T233900_eeg.vhdr", preload=False, stim_channel=False)
c = EbmChannel("/media/beliy/KINGSTON/Memodyn/ForTest/Emb/35d1ef92-1b65-42f3-aab4-b3d61076f448/"+emb_raw.ch_names[chan_idx]+".ebm")

freq = emb_raw.info["sfreq"]
if freq != conv_raw.info["sfreq"]:
    raise Exception("Frequency mismatch")

emb_t_offset  = 0
conv_t_offset = 0
x = emb_raw.info["meas_date"][0] - conv_raw.info["meas_date"][0]
if x > 0:
    conv_t_offset = int(x*freq)
else :
    emb_t_offset = int(x*freq)
edf_t_offset = int((emb_raw.info["meas_date"][0] - edf_raw.info["meas_date"][0])*freq)
print(edf_t_offset)


up_limit = c.TransRange[1]
dw_limit = c.TransRange[0]

orig_up_limit = c.RawRange[1]
orig_dw_limit = c.RawRange[0]

MAX_INT = 32767
unit_scale = 10**(-c.GetMagnitude())
unit    = c.GetUnit()

deviations = []
deviations2= []
deviations3= []

emb_res  = unit_scale*max(abs(up_limit),abs(dw_limit))/MAX_INT
edf_res  = unit_scale*max(abs(orig_up_limit),abs(orig_dw_limit))/MAX_INT

print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
print(emb_raw.ch_names[chan_idx], conv_raw.ch_names[chan_idx], edf_raw.ch_names[chan_idx+1])
print("Resolutions:",emb_res, edf_res)
print("Upper values:", unit_scale*max(abs(up_limit),abs(dw_limit)), 
                        unit_scale*max(abs(orig_up_limit),abs(orig_dw_limit))
    )
print("Start times:", emb_raw.info["meas_date"][0], conv_raw.info["meas_date"][0])
print("Offsets:", emb_t_offset, conv_t_offset)
print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

chunk_size = 10000
chunk = 0
while chunk*chunk_size < emb_raw.n_times:
    max_loc = -9999999
    pos = chunk_size*chunk
    emb_pos = pos + emb_t_offset
    emb_data  = emb_raw.get_data (picks = [chan_idx],  start=emb_pos, stop=emb_pos+chunk_size)[0]
    conv_pos = pos + conv_t_offset
    conv_data = conv_raw.get_data(picks = [chan_idx], start=conv_pos, stop=conv_pos+chunk_size)[0]
    edf_pos = pos + edf_t_offset
    edf_data  = edf_raw.get_data(picks = [chan_idx+1], start=edf_pos, stop=edf_pos+chunk_size)[0]

    t = emb_raw.times[emb_pos]
    t2= conv_raw.times[conv_pos]
    t3= edf_raw.times[edf_pos]
    emb_time = t+emb_raw.info["meas_date"][0]
    conv_time= t2+conv_raw.info["meas_date"][0]
    edf_time= t3+edf_raw.info["meas_date"][0]


    limit = min(len(emb_data), len(conv_data), len(edf_data))
#    print("{}: {:g}\t{:g}\t{:g}".format(datetime.timedelta(seconds=t),emb_data[0]*unit_scale, edf_data[0]*unit_scale, conv_data[0]))
    for i in range(0,limit):
        emb = emb_data[i]*unit_scale
        edf = edf_data[i]*unit_scale
        bv  = conv_data[i]
        if up_limit < orig_up_limit :
            if edf_data[i] > 0.99*up_limit: continue
            if edf_data[i] < 0.99*dw_limit: continue
        deviations.append((emb - edf))
        if edf != 0:
            deviations2.append((emb - edf)/edf)
            deviations3.append((bv - edf)/edf)
    chunk += 1

textstr = '\n'.join((
    r'%-11s=%g %s' % ("Emb. res",emb_res, unit),
    r'%-11s=%g %s' % ("EDF res ", edf_res, unit)))
props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
fig, ax = plt.subplots()
ax.hist(deviations, bins=100, log=True)
plt.title('{}'.format(emb_raw.ch_names[chan_idx]))
plt.xlabel(r'$(v_{emb}-v_{edf})$ [' + unit + ']')
ax.text(0.05, 0.95, textstr, fontsize=14, verticalalignment='top', bbox=props, transform=ax.transAxes)
plt.show()

fig, ax = plt.subplots()
ax.hist(deviations2, bins=100, log=True)
ax.text(0.05, 0.95, textstr, fontsize=14, verticalalignment='top', bbox=props, transform=ax.transAxes)
plt.title('{}'.format(emb_raw.ch_names[chan_idx]))
plt.xlabel(r'$(v_{emb}-v_{edf})/v_{edf}$')
plt.show()

plt.hist(deviations3, bins=100, log=True)
plt.title('{}'.format(emb_raw.ch_names[chan_idx]))
plt.xlabel(r'$(v_{bv}-v_{edf})/v_{bv}$')
plt.show()
