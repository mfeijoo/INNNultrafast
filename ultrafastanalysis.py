import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from glob import glob

st.title('INNN Mexico Ultrafast Scans')

st.header ('PDD Single Scan')

#Load the file from a list of files in the directory

listoffiles = glob('*.csv')

file1 = st.selectbox('Select File', listoffiles)

df = pd.read_csv(file1, skiprows = 4)

#Find Zeros

fig0 = px.scatter(df, x='time', y='ch0')
fig0.update_traces(marker=dict(size=2))

st.plotly_chart(fig0)

lim0 = st.number_input('time(s) before beam starts')
lim1 = st.number_input('time(s) begining of pdd')
lim2 = st.number_input('time(s) end of pdd')
depth = st.number_input('PDD depth (mm)')

#Find Zeros
dfnobeam = df[df.time < lim0]
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


#General Sattistics

st.header ('General Statistics')
st.write ( 'Total Number of Samples: %s' %dfz.shape[0])
st.write ('Totall Number of pulses: %s' %dfz.pulse.sum())
st.write ('Pulse coinciding: %s' %dfz.pulsecoincide.sum())

#Calculate total dose
ACR = st.number_input('Introduce ACR value', value = 0.9490, step = 0.0001, format = '%f')
dfz['chargedose'] = dfz.ch0zg - dfz.ch1zg * ACR

#Calculate dose when only pulses
dfz['chargedosep'] = dfz.loc[dfz.pulse, 'chargedose']

#Create PDD
dfzpdd = dfz.loc[(dfz.time > lim1) & (dfz.time < lim2), :].copy()
pddtime = lim2 - lim1
speed = depth / pddtime
st.write ('Calculated speed: %.2f mm/s' %speed)



dfzpdd['timebetweensamples'] = dfzpdd.time.diff()
dfzpdd['disttraveled'] = dfzpdd.timebetweensamples * speed
dfzpdd['pos1'] = dfzpdd.disttraveled.cumsum()
firstpos1pdd = dfzpdd.loc[dfzpdd.time > lim1, 'pos1'].min()
lastpos1pdd = dfzpdd.loc[dfzpdd.time < lim2, 'pos1'].max()
dfzpdd['pos'] = depth - dfzpdd.pos1

#Smooth out PDD
avgtimebetweenpulses = dfzpdd.dropna().time.diff().mean() * 1000
pulsespermm = speed * avgtimebetweenpulses

dfzpddp = dfzpdd.dropna().copy()

smoothfactor = st.slider('Smooth Factor', min_value = 1, max_value = 400)

dfzpddp['smoothcharge'] = dfzpddp.chargedosep.rolling(smoothfactor, center = True).mean()

dfzpddp['pdd'] = dfzpddp.smoothcharge / dfzpddp.smoothcharge.max() * 100

fig3 = px.scatter(dfzpddp, x='pos', y='pdd')
fig3.update_traces(marker=dict(size=2))
st.plotly_chart(fig3)

st.write(dfzpddp.loc[:,['pos', 'pdd', 'smoothcharge']].dropna())

