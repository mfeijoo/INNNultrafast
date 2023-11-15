import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import boto3

st.title('PDD with profiles')

# Load the file 

#Load the file from a list of files in the directory
s3 = boto3.client('s3')
response1 = s3.list_objects_v2(Bucket = 'bluephysicsaws', Prefix = 'PDD with profiles')

listoffiles = [file['Key'] for file in response1.get('Contents', [])]

file1 = st.selectbox('Select File', listoffiles)

@st.cache_data
def load_data(file):
    path = 's3://bluephysicsaws/%s' %file
    df = pd.read_csv(path, skiprows = 4)
    return df

df = load_data(file1)

fig0 = px.scatter(df, x = 'time', y = 'ch0')
st.plotly_chart(fig0)

lim0 = st.number_input('time (s) before beam starts', value = 6.00, step = 0.01, format = '%f')

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
dfz['dose'] = dfz.ch0zg - dfz.ch1zg
dfzp = dfz[dfz.pulse].copy()
fig1 = px.scatter(dfzp, x = 'time', y = 'dose')
fig1.update_traces(mode = 'markers',
                    marker = dict (color = 'blue', size = 3, opacity = 0.5),
                    showlegend = True,
                    name = 'dose')

#Find shots

dfz['chunk'] = dfz.number // 300
dfgs = dfz.groupby('chunk').agg({'time':np.min, 'ch0zg':np.sum})
dfgf = dfz.groupby('chunk').agg({'time':np.max, 'ch0zg':np.sum})
dfgs = dfgs.iloc[1:-1,:]
dfgf = dfgf.iloc[1:-1,:]
dfgs['ch0diff'] = dfgs.ch0zg.diff()
dfgf['ch0diff'] = dfgf.ch0zg.diff()
#fig2 = px.line(dfgs, x = 'time', y = 'ch0zg', markers = True)
#st.plotly_chart(fig2)

cutoff = st.slider('cutoff', min_value = 10, max_value = 60, value = 40)
starttimes = dfgs.loc[dfgs.ch0diff > cutoff, 'time']
stss = [starttimes.iloc[0]] + starttimes[starttimes.diff() > 2].to_list()
sts = [i - 0.5 for i in stss]
finishtimes = dfgf.loc[dfgf.ch0diff < -cutoff, 'time']
ftss = [finishtimes.iloc[0]] + finishtimes[finishtimes.diff() > 2].to_list()
fts = [i + 0.5 for i in ftss]
for num ,(stn, ftn) in enumerate(zip(sts, fts)):
    fig1.add_vline(x = stn, line_width = 1, line_dash = 'dash', line_color = 'green', opacity = 0.5)
    fig1.add_vline(x = ftn, line_width = 1, line_dash = 'dash', line_color = 'red', opacity = 0.5)
    dfz.loc[(dfz.time > stn) & (dfz.time < ftn), 'shot'] = num 
    dfzp.loc[(dfzp.time > stn) & (dfzp.time < ftn), 'shot'] = num 

st.plotly_chart(fig1)

rowtodrop = st.number_input('shot to drop', min_value = 0, max_value = 18, value = 0)
#Calculate integrals
percent = st.slider('Percentage of maximum above average is calculted', min_value = 80, max_value = 100, value = 90) 
dfi = pd.DataFrame()
dfi['meandose'] = dfzp.groupby('shot')['dose'].agg(lambda x: x[x >= percent / 100 * x.max()].mean())
dfi.reset_index(inplace = True)
if rowtodrop > 0:
    dfi.drop(rowtodrop - 1, inplace = True)
dfi['direction'] = ['crossplane', 'inplane'] * 9
dfi['depth'] = [5,5,10,10,15,15,25,25,50,50,100,100,150,150,200,200,250,250]
dfig = dfi.loc[:,['meandose', 'depth']].groupby('depth').mean()
dfig['error'] = dfi.loc[:,['meandose', 'depth']].groupby('depth').std()
dfig['pdd'] = dfig.meandose / dfig.meandose.max() * 100
dfig.reset_index(inplace=True)

fig2 = px.scatter(dfig, x = 'depth', y = 'pdd', error_y = 'error')
st.plotly_chart(fig2)

st.write(dfig)
st.write('mean error: %.3f' %dfig.error.mean())


