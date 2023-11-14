import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from glob import glob

st.title('Profiles at 10 cm depth')

# Load the file 

#Load the file from a list of files in the directory

listoffiles = glob('Profiles at 10 cm depth/*.csv')

file1 = st.selectbox('Select File', listoffiles)

df = pd.read_csv(file1, skiprows = 4)

fig0 = px.scatter(df, x = 'time', y = 'ch0')

st.write(df.head())
st.plotly_chart(fig0)

