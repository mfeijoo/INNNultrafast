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

lim0 = st.number_input('time (s) before beam starts', value = 3.00, step = 0.01, format = '%f')
fig0 = px.scatter(df, x= 'time', y='ch0')
st.plotly_chart(fig0)

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

st.plotly_chart(fig1)

