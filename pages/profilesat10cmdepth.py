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

lim0 = st.number_input('time (s) before beam starts', min_value = 0.00, max_value = df.time.max(), value = 3.00, step = 0.01, format = '%f')
lim1 = st.number_input('time (s) after beam finishes', value = df.time.max(), max_value = df.time.max(), step = 0.01, min_value =0.00, format = '%f')
fig0 = px.scatter(df, x= 'time', y='ch0')
st.plotly_chart(fig0)

#Find Zeros
dfnobeam = df[(df.time < lim0) | (df.time <= lim1)]
zeros = dfnobeam.loc[:, 'ch0':].mean()
dfzeros = df.loc[:, 'ch0':] - zeros
dfzeros.columns = ['ch0z', 'ch1z']
dfz = pd.concat([df, dfzeros], axis = 1)

#Find general pulses
maxch0nobeam = dfz.loc[dfz.time < lim0, 'ch0z'].max()
dfz['pulseg'] = dfz.ch0z > maxch0nobeam * 1.40

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

dfzp = dfz[dfz.pulse].copy()
fig1 = px.scatter(dfzp, x = 'time', y = 'dose')
fig1.update_traces(mode = 'markers',
                    marker = dict (color = 'blue', size = 3, opacity = 0.5),
                    showlegend = True,
                    name = 'dose')

#Separate all profiles in each file
#Find shots

dfzp['chunk'] = dfzp.number // 60
dfgs = dfzp.groupby('chunk').agg({'time':np.min, 'dose':np.sum})
dfgf = dfzp.groupby('chunk').agg({'time':np.max, 'dose':np.sum})
dfgs = dfgs.iloc[1:-1,:]
dfgf = dfgf.iloc[1:-1,:]
dfgs['dosediff'] = dfgs.dose.diff()
dfgf['dosediff'] = dfgf.dose.diff()

starttimes = dfgs.loc[dfgs.dosediff > 10, 'time']
stss = [starttimes.iloc[0]] + starttimes[starttimes.diff() > 2].to_list()
sts = [i - 0.5 for i in stss]
finishtimes = dfgf.loc[dfgf.dosediff < -10, 'time']
ftss = [finishtimes.iloc[0]] + finishtimes[finishtimes.diff() > 2].to_list()
fts = [i + 0.5 for i in ftss]
for num ,(stn, ftn) in enumerate(zip(sts, fts)):
    fig1.add_vline(x = stn, line_width = 1, line_dash = 'dash', line_color = 'green', opacity = 0.5)
    fig1.add_vline(x = ftn, line_width = 1, line_dash = 'dash', line_color = 'red', opacity = 0.5)
    dfz.loc[(dfz.time > stn) & (dfz.time < ftn), 'shot'] = num 
    dfzp.loc[(dfzp.time > stn) & (dfzp.time < ftn), 'shot'] = num 

fieldsize = st.number_input('Field Size (mm)', min_value = 0, max_value = 10, value = 5, step = 1)
percentagemax = st.slider('Percentage of maximum above average is calculated', min_value = 80, max_value = 100, value = 90)
smoothfactor = st.slider('Smooth Factor', min_value = 1, max_value = 100, step = 1, value = 1) 

for i in range(2):
    #Transform measurments intime to position

    dfzp0 = dfzp[dfzp.shot == i]
    timecenter = dfzp0.loc[dfzp0.dose >= dfzp0.dose.max() * percentagemax/100, 'time'].median()
    maxnow = dfzp0.loc[dfzp0.dose >  percentagemax/100 * dfzp0.dose.max(), 'dose'].mean()
    timeedge1 = dfzp0.loc[(dfzp0.time < timecenter) & (dfzp0.dose < maxnow/2), 'time'].max()
    timeedge2 = dfzp0.loc[(dfzp0.time > timecenter) & (dfzp0.dose < maxnow/2), 'time'].min()

    # Calculate speed
    speedcalc = fieldsize / (timeedge2 - timeedge1)
    st.write('Speed measured = %.2f mm/s' %speedcalc)

    #Calculate positions
    dfzp0['timebetweensamples'] = dfzp0.time.diff()
    dfzp0['distancetraveled'] = dfzp0.timebetweensamples * speedcalc
    dfzp0['pos1'] = dfzp0.distancetraveled.cumsum()

    #recenter
    edge1 = dfzp0.loc[(dfzp0.time < timecenter) & (dfzp0.dose < maxnow/2), 'pos1'].max()
    edge2 = dfzp0.loc[(dfzp0.time > timecenter) & (dfzp0.dose < maxnow/2), 'pos1'].min()
    newcenter = (edge1 + edge2) / 2

    dfzp0['pos'] = dfzp0.pos1 - newcenter

    #Smooth out
    dfzp0['dosesmooth'] = dfzp0.dose.rolling(smoothfactor, center = True).mean()
    maxnowsmooth = dfzp0.dosesmooth.max()
    edge1 = dfzp0.loc[(dfzp0.time < timecenter) & (dfzp0.dosesmooth < maxnowsmooth/2), 'pos1'].max()
    edge2 = dfzp0.loc[(dfzp0.time > timecenter) & (dfzp0.dosesmooth < maxnowsmooth/2), 'pos1'].min()
    newcenter = (edge1 + edge2) / 2
    dfzp0['pos'] = dfzp0.pos1 - newcenter
    dfzp0['reldosesmooth'] = dfzp0.dosesmooth / dfzp0.dosesmooth.max() * 100
    fig2 = px.scatter(dfzp0, x = 'pos', y = 'reldosesmooth')
    newedge1 = edge1 - newcenter
    newedge2 = edge2 - newcenter
    smoothfieldsize = newedge2 - newedge1
    fig2.add_vline(x = newedge1, line_dash = "dash", line_color = 'green')
    fig2.add_vline(x = 0, line_dash = "dash", line_color = 'black')
    fig2.add_vline(x = newedge2, line_dash = "dash", line_color = 'red')
    fig2.add_annotation(x=0, y = 50, showarrow = False, text = "Field Size: %.2f mm" %smoothfieldsize)
    st.plotly_chart(fig2)
    st.write(dfzp0.loc[:,['pos', 'dosesmooth', 'reldosesmooth']])
