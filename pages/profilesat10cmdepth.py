import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import boto3

st.title('Profiles at 10 cm depth')

# Load the file 

#Load the file from a list of files in the directory
s3 = boto3.client('s3')
response1 = s3.list_objects_v2(Bucket = 'bluephysicsaws', Prefix = 'Profiles at 10 cm depth')

listoffiles = [file['Key'] for file in response1.get('Contents', [])]

file1 = st.selectbox('Select File', listoffiles)

@st.cache_data
def load_data(file):
    path = 's3://bluephysicsaws/%s' %file
    df = pd.read_csv(path, skiprows = 4)
    return df

df = load_data(file1)
fig8 = px.scatter(df, x='time', y='ch0', title = 'Raw Data')
st.plotly_chart(fig8)

lim0 = st.number_input('time (s) before beam starts', min_value = 0.00, max_value = df.time.max(), value = 6.00, step = 0.01, format = '%f')
lim1 = st.number_input('time (s) after beam finishes', value = df.time.max(), max_value = df.time.max(), step = 0.01, min_value =0.00, format = '%f')
#st.plotly_chart(fig0)

#Find Zeros
dfnobeam = df[(df.time < lim0) | (df.time <= lim1)]
zeros = dfnobeam.loc[:, 'ch0':].mean()
dfzeros = df.loc[:, 'ch0':] - zeros
dfzeros.columns = ['ch0z', 'ch1z']
dfzb = pd.concat([df, dfzeros], axis = 1)
dfz = dfzb.loc[(dfzb.time > lim0) & (dfzb.time < lim1),:]

limpulses = st.slider('minimum pulse', min_value = 1.00, max_value = 1.40, value = 1.05, step = 0.001, format = '%f')
#Find general pulses
maxch0nobeam = dfzb.loc[(dfzb.time < lim0) | (dfzb.time > lim1), 'ch0z'].max()
dfz['pulseg'] = dfz.ch0z > maxch0nobeam * limpulses

#Find coincide pulses
dfz['pulseafter'] = dfz.pulseg.shift(-1)
dfz['pulsecoincide'] = dfz.pulseg & dfz.pulseafter

#Identify single pulses
dfz['pulsecoincidea'] = dfz.pulsecoincide.shift().fillna(False)
dfz['pulse'] = dfz.pulseg
dfz.loc[dfz.pulsecoincidea, 'pulse'] = False

#Add signal of pulses coinciding
dfz['ch1zg'] = dfz.ch1z
dfz['ch0zg'] = dfz.ch0z
dfz['ch0za'] = dfz.ch0z.shift(-1)
dfz['ch1za'] = dfz.ch1z.shift(-1)
dfz.loc[dfz.pulsecoincide, 'ch0zg'] = dfz.ch0z + dfz.ch0za
dfz.loc[dfz.pulsecoincide, 'ch1zg'] = dfz.ch1z + dfz.ch1za
dfz.loc[dfz.pulsecoincidea, ['ch0zg', 'ch1zg']] = 0

ACR = st.number_input('ACR', value = 0.949, step = 0.001, max_value = 1.000, format = '%f', min_value = 0.949)

dfz['dose'] = dfz.ch0zg - dfz.ch1zg * ACR

fig0 = px.scatter(dfz, x= 'time', y='dose', title = 'dose zeroed')
dfzp = dfz[dfz.pulse].copy()

#Separate all profiles in each file
#Find shots

dfz['chunk'] = dfz.number // 60
dfgs = dfz.groupby('chunk').agg({'time':np.min, 'dose':np.sum})
dfgf = dfz.groupby('chunk').agg({'time':np.max, 'dose':np.sum})
dfgs = dfgs.iloc[1:-1,:]
dfgf = dfgf.iloc[1:-1,:]
dfgs['dosediff'] = dfgs.dose.diff()
dfgf['dosediff'] = dfgf.dose.diff()

cutoff = st.number_input('Cutoff',  min_value = 1, max_value = 15, value = 10, step = 1)
starttimes = dfgs.loc[dfgs.dosediff > cutoff, 'time']
stss = [starttimes.iloc[0]] + starttimes[starttimes.diff() > 2].to_list()
sts = [i - 2 for i in stss]
finishtimes = dfgf.loc[dfgf.dosediff < -cutoff, 'time']
ftss = [finishtimes.iloc[0]] + finishtimes[finishtimes.diff() > 2].to_list()
fts = [i + 2 for i in ftss]
for num ,(stn, ftn) in enumerate(zip(sts, fts)):
    fig0.add_vline(stn, line_dash = 'dash', line_color = 'green')
    fig0.add_vline(ftn, line_dash = 'dash', line_color = 'red')
    dfzp.loc[(dfzp.time > stn) & (dfzp.time < ftn), 'shot'] = num 
    dfz.loc[(dfz.time > stn) & (dfz.time < ftn), 'shot'] = num 

st.plotly_chart(fig0)
fieldsize = st.number_input('Field Size (mm)', min_value = 0, max_value = 10, value = 5, step = 1)
percentagemax = st.slider('Percentage of maximum above average is calculated', min_value = 80, max_value = 100, value = 90)
smoothfactor= st.slider('Smooth Factor', min_value = 1, max_value = 100, step = 1, value = 1) 

for i in range(num + 1):
    #Transform measurments intime to position

    dfz0 = dfzp[dfzp.shot == i]
    
    timecenter = dfz0.loc[dfz0.dose >= dfz0.dose.max() * percentagemax/100, 'time'].median()
    maxnow = dfz0.loc[dfz0.dose >  percentagemax/100 * dfz0.dose.max(), 'dose'].mean()
    timeedge1 = dfz0.loc[(dfz0.time < timecenter) & (dfz0.dose < maxnow/2), 'time'].max()
    timeedge2 = dfz0.loc[(dfz0.time > timecenter) & (dfz0.dose < maxnow/2), 'time'].min()

    # Calculate speed
    speedcalc = fieldsize / (timeedge2 - timeedge1)
    st.write('Speed measured = %.2f mm/s' %speedcalc)

    

    #Calculate positions
    dfz0['timebetweensamples'] = dfz0.time.diff()
    dfz0['distancetraveled'] = dfz0.timebetweensamples * speedcalc
    dfz0['pos1'] = dfz0.distancetraveled.cumsum()

    #Calculate samples and pulses per mm
    numberofpulses = dfz[dfz.shot == i].pulse.sum()
    numberofsamples = dfz.shape[0]
    totaldistance = dfz0.distancetraveled.sum()
    pulsespermm = numberofpulses / totaldistance
    samplespermm = numberofsamples / totaldistance
    st.write('Samples per mm %.2f' %samplespermm)
    st.write('Pulses per mm %.2f' %pulsespermm)

    #recenter
    edge1 = dfz0.loc[(dfz0.time < timecenter) & (dfz0.dose < maxnow/2), 'pos1'].max()
    edge2 = dfz0.loc[(dfz0.time > timecenter) & (dfz0.dose < maxnow/2), 'pos1'].min()
    newcenter = (edge1 + edge2) / 2

    dfz0['pos'] = dfz0.pos1 - newcenter

    #Smooth out
    dfz0['dosesmooth'] = dfz0.dose.rolling(smoothfactor, center = True).mean()
    maxnowsmooth = dfz0.dosesmooth.max()
    edge1 = dfz0.loc[(dfz0.time < timecenter) & (dfz0.dosesmooth < maxnowsmooth/2), 'pos1'].max()
    edge2 = dfz0.loc[(dfz0.time > timecenter) & (dfz0.dosesmooth < maxnowsmooth/2), 'pos1'].min()
    newcenter = (edge1 + edge2) / 2
    dfz0['pos'] = dfz0.pos1 - newcenter
    dfz0['reldosesmooth'] = dfz0.dosesmooth / dfz0.dosesmooth.max() * 100
    dfz0toplot = dfz0.loc[(dfz0.pos > - fieldsize) & (dfz0.pos < fieldsize),:]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
                            x = dfz0toplot.pos,
                            y = dfz0toplot.reldosesmooth,
                            mode = 'markers',
                            marker = dict(color = 'blue')))
    newedge1 = edge1 - newcenter
    newedge2 = edge2 - newcenter
    smoothfieldsize = newedge2 - newedge1
    fig2.add_vline(x = newedge1, line_dash = "dash", line_color = 'green')
    fig2.add_vline(x = 0, line_dash = "dash", line_color = 'black')
    fig2.add_vline(x = newedge2, line_dash = "dash", line_color = 'red')
    fig2.add_annotation(x=0, y = 50, showarrow = False, text = "Field Size: %.2f mm" %smoothfieldsize)
    st.plotly_chart(fig2)
    st.write(dfz0.loc[:,['pos', 'dosesmooth', 'reldosesmooth']])
