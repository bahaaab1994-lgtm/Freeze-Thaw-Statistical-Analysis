# -*- coding: utf-8 -*-
"""
Created on Mon Aug  4 21:28:35 2025

@author: bahaa
"""

import streamlit as st
import pandas as pd
import numpy as np
from data_loader import load_freeze_thaw_data, load_freeze_thaw_data_by_season, get_available_seasons
from coordinate_matcher import find_nearest_location
# Set page configuration
st.set_page_config(
    page_title="Freeze-Thaw Cycle Data Query",
    page_icon="❄️",
    layout="centered"
)
# Load data
@st.cache_data
def get_data():
    """Load and cache the freeze-thaw cycle data"""
    return load_freeze_thaw_data()
def main():
    st.title("❄️ Freeze-Thaw Cycle Data Query")
    st.markdown("Select a season and enter location details to find freeze-thaw cycle information.")
    
    # Season selection
    st.subheader("📅 Select Season")
    
    available_seasons = get_available_seasons()
    if not available_seasons:
        st.error("No freeze-thaw data files found. Please add Excel files to the project.")
        return
    
    # Create columns for season selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_season = st.selectbox(
            "Choose a season:",
            available_seasons,
            index=len(available_seasons)-1,  # Select most recent season by default
            help="Select the season for which you want to query freeze-thaw data"
        )
    
    with col2:
        st.metric("Available Seasons", len(available_seasons))
    
    # Load data for selected season
    try:
        data = load_freeze_thaw_data_by_season(selected_season)
        if data.empty:
            st.error(f"No data found for season {selected_season}")
            return
        else:
            # Show data summary
            st.success(f"✅ Successfully loaded {len(data)} records for season {selected_season}")
            
            with st.expander("📊 Data Summary"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Records", len(data))
                with col2:
                    st.metric("States", str(data['State'].nunique()))
                with col3:
                    st.metric("Counties", str(data['County'].nunique()))
                
                # Show sample data
                st.subheader("Sample Data")
                st.dataframe(data.head(), use_container_width=True)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Separator
    st.markdown("---")
    
    # Input form
    st.subheader("🔍 Location Query")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        state = st.text_input(
            "State", 
            placeholder="e.g., Colorado",
            help="Enter the state name"
        )
    
    with col2:
        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=None,
            format="%.6f",
            help="Enter latitude in decimal degrees"
        )
    
    with col3:
        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=None,
            format="%.6f",
            help="Enter longitude in decimal degrees"
        )
    
    # Search button
    if st.button("Search for Freeze-Thaw Data", type="primary"):
        # Validate inputs
        if not state or state.strip() == "":
            st.error("Please enter a state name.")
            return
        
        if latitude is None or longitude is None:
            st.error("Please enter both latitude and longitude values.")
            return
        
        # Load fresh data for the selected season for the search
        search_data = load_freeze_thaw_data_by_season(selected_season)
        if search_data.empty:
            st.error(f"No data available for season {selected_season}")
            return
        
        # Normalize state input
        state_normalized = state.strip().title()
        
        # Filter data by state first
        state_data = search_data[search_data['State'].str.contains(state_normalized, case=False, na=False)]
        
        if state_data.empty:
            st.error(f"No data found for state: {state_normalized}")
            
            # Show available states
            available_states = sorted(search_data['State'].unique())
            st.info("Available states in database:")
            st.write(", ".join(available_states))
            return
        
        # Find nearest location
        try:
            nearest_location, distance = find_nearest_location(
                latitude, longitude, state_data
            )
            
            if nearest_location is None:
                st.warning(
                    f"No monitoring stations found within 50 km of the specified coordinates in {state_normalized}. "
                    "Try searching with coordinates closer to populated areas."
                )
                
                # Show available locations in the state
                st.subheader(f"Available monitoring stations in {state_normalized}:")
                display_data = state_data[['County', 'Latitude', 'Longitude', 'Total_Freeze_Thaw_Cycles', 'Damaging_Freeze_Thaw_Cycles']].copy()
                st.dataframe(display_data, use_container_width=True)
                return
            
            # Display results
            st.success(f"✅ Nearest monitoring station found for season {selected_season}!")
            
            # Location information
            st.subheader("📍 Location Details")
            
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.metric("County", nearest_location['County'])
                st.metric("State", nearest_location['State'])
                st.metric("Distance", f"{distance:.2f} km")
            
            with info_col2:
                st.metric("Station Latitude", f"{nearest_location['Latitude']:.6f}")
                st.metric("Station Longitude", f"{nearest_location['Longitude']:.6f}")
            
            # Freeze-thaw cycle data
            st.subheader(f"❄️ Freeze-Thaw Cycle Data ({selected_season})")
            
            cycle_col1, cycle_col2 = st.columns(2)
            
            with cycle_col1:
                st.metric(
                    "Total Freeze-Thaw Cycles",
                    int(nearest_location['Total_Freeze_Thaw_Cycles']),
                    help="Total number of freeze-thaw cycles recorded at this location"
                )
            
            with cycle_col2:
                st.metric(
                    "Damaging Freeze-Thaw Cycles",
                    int(nearest_location['Damaging_Freeze_Thaw_Cycles']),
                    help="Number of freeze-thaw cycles that could cause structural damage"
                )
            
            # Additional information
            damage_percentage = (nearest_location['Damaging_Freeze_Thaw_Cycles'] / 
                               nearest_location['Total_Freeze_Thaw_Cycles'] * 100)
            
            st.info(
                f"**Analysis:** {damage_percentage:.1f}% of freeze-thaw cycles at this location "
                f"are classified as potentially damaging to infrastructure."
            )
            
            # Show location on map
            st.subheader("📍 Station Location")
            map_data = pd.DataFrame({
                'lat': [nearest_location['Latitude']],
                'lon': [nearest_location['Longitude']]
            })
            st.map(map_data, zoom=8)
            
        except Exception as e:
            st.error(f"Error processing search: {str(e)}")
    
    # Additional information
    st.markdown("---")
    st.subheader("ℹ️ About This Data")
    st.markdown("""
    This application provides freeze-thaw cycle data from monitoring stations across various states.
    
    - **Total Freeze-Thaw Cycles**: Represents all freezing events that the concrete experienced during the monitoring period, regardless of the moisture condition.
    - **Damaging Freeze-Thaw Cycles**: Refers to the subset of freeze-thaw cycles during which the Degree of Saturation (DOS) exceeded the critical threshold of 80%, making the concrete susceptible to freeze-thaw damage.
    
    *Note: Results are based on the nearest available monitoring station and may not reflect exact conditions at your specific location.*
    """)
if __name__ == "__main__":
    main()