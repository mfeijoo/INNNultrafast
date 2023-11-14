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

fig0 = px.scatter(df, x = 'time', y = 'ch0')

st.write(df.head())
st.plotly_chart(fig0)

