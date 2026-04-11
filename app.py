import pandas as pd
import plotly
import plotly.express as px

# 1. Load the data
df = pd.read_csv('census_patient_percent.csv')

# 2. Clean the data (convert to numeric and drop missing values)
df['PatientPercent'] = pd.to_numeric(df['PatientPercent'], errors='coerce')
df['CENTLAT'] = pd.to_numeric(df['CENTLAT'], errors='coerce')
df['CENTLON'] = pd.to_numeric(df['CENTLON'], errors='coerce')
df = df.dropna(subset=['CENTLAT', 'CENTLON', 'PatientPercent'])

# 3. Create the interactive map
fig = px.scatter_geo(df,
                     lat='CENTLAT',
                     lon='CENTLON',
                     color='PatientPercent',
                     scope='usa', # Filters the base map to the United States
                     title='Patient Percent by Census Tract',
                     color_continuous_scale='Plasma',
                     size_max=15)

# 4. Center and zoom in on the data bounds (Kansas)
fig.update_geos(
    center=dict(lon=-98, lat=38),
    lataxis_range=[36, 41],
    lonaxis_range=[-103, -93],
    fitbounds="locations"
)

# 5. Save or show
fig.write_html('interactive_patient_map.html')
fig.show()