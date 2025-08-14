# -*- coding: utf-8 -*-
"""
Created on Mon Aug  4 21:28:35 2025

@author: bahaa
"""
############ Statistical Analysis
import streamlit as st
import pandas as pd
import numpy as np
from data_loader import load_freeze_thaw_data_by_season, get_available_seasons
from coordinate_matcher import find_nearest_location
# Set page configuration
st.set_page_config(
    page_title="Freeze-Thaw Cycle Data Analysis",
    page_icon="❄️",
    layout="centered"
)
def clean_county_name(county):
    """Remove numbers from county names (e.g., Jefferson5 -> Jefferson)"""
    if pd.isna(county):
        return county
    # Remove trailing numbers
    import re
    cleaned = re.sub(r'\d+$', '', str(county)).strip()
    return cleaned if cleaned else str(county)
@st.cache_data
def get_states_for_latest_season():
    """Get available states from the most recent season"""
    try:
        seasons = get_available_seasons()
        if not seasons:
            return []
        
        latest_season = seasons[-1]  # Most recent season
        data = load_freeze_thaw_data_by_season(latest_season)
        if data.empty:
            return []
        
        # Clean and get unique states
        states = data['State'].dropna().astype(str).str.strip()
        unique_states = states.unique()
        clean_states = [state for state in unique_states if state and state.strip()]
        return sorted(list(set(clean_states)))
    except Exception as e:
        st.error(f"Error loading states: {str(e)}")
        return []
def calculate_comprehensive_statistics(location_data, all_seasons):
    """Calculate statistics for all years and last 5 years for a specific location"""
    try:
        location_stats = []
        
        # Get data for all seasons for this location
        for season in all_seasons:
            try:
                season_data = load_freeze_thaw_data_by_season(season)
                if season_data.empty:
                    continue
                
                # Clean county names in season data
                season_data['County_Clean'] = season_data['County'].apply(clean_county_name)
                location_county_clean = clean_county_name(location_data['County'])
                
                # Find matching record by State and cleaned County
                exact_match = season_data[
                    (season_data['State'].str.strip().str.upper() == location_data['State'].strip().upper()) &
                    (season_data['County_Clean'].str.strip().str.upper() == location_county_clean.strip().upper())
                ]
                
                if not exact_match.empty:
                    # If multiple matches, find the one with closest coordinates
                    if len(exact_match) > 1:
                        distances = []
                        for idx, row in exact_match.iterrows():
                            lat_diff = abs(row['Latitude'] - location_data['Latitude'])
                            lon_diff = abs(row['Longitude'] - location_data['Longitude'])
                            distance = (lat_diff**2 + lon_diff**2)**0.5
                            distances.append(distance)
                        
                        closest_idx = exact_match.index[np.argmin(distances)]
                        record = exact_match.loc[closest_idx]
                    else:
                        record = exact_match.iloc[0]
                    
                    location_stats.append({
                        'Season': season,
                        'Total_Cycles': record['Total_Freeze_Thaw_Cycles'],
                        'Damaging_Cycles': record['Damaging_Freeze_Thaw_Cycles']
                    })
                    
            except Exception as e:
                continue
        
        if not location_stats:
            return None
        
        # Convert to DataFrame and sort by season (most recent first)
        stats_df = pd.DataFrame(location_stats)
        stats_df = stats_df.sort_values('Season', ascending=False)
        
        # Get data arrays
        total_cycles = stats_df['Total_Cycles'].values
        damaging_cycles = stats_df['Damaging_Cycles'].values
        
        # ALL YEARS STATISTICS (up to 24 seasons)
        total_all_avg = float(np.mean(total_cycles)) if len(total_cycles) > 0 else 0
        damaging_all_avg = float(np.mean(damaging_cycles)) if len(damaging_cycles) > 0 else 0
        
        total_all_cov = float((np.std(total_cycles) / np.mean(total_cycles) * 100)) if len(total_cycles) > 1 and np.mean(total_cycles) > 0 else 0
        damaging_all_cov = float((np.std(damaging_cycles) / np.mean(damaging_cycles) * 100)) if len(damaging_cycles) > 1 and np.mean(damaging_cycles) > 0 else 0
        
        # LAST 5 YEARS STATISTICS
        recent_total = total_cycles[:5] if len(total_cycles) >= 5 else total_cycles
        recent_damaging = damaging_cycles[:5] if len(damaging_cycles) >= 5 else damaging_cycles
        
        total_5yr_avg = float(np.mean(recent_total)) if len(recent_total) > 0 else 0
        damaging_5yr_avg = float(np.mean(recent_damaging)) if len(recent_damaging) > 0 else 0
        
        total_5yr_cov = float((np.std(recent_total) / np.mean(recent_total) * 100)) if len(recent_total) > 1 and np.mean(recent_total) > 0 else 0
        damaging_5yr_cov = float((np.std(recent_damaging) / np.mean(recent_damaging) * 100)) if len(recent_damaging) > 1 and np.mean(recent_damaging) > 0 else 0
        
        return {
            'data': stats_df,
            'total_all_avg': total_all_avg,
            'damaging_all_avg': damaging_all_avg,
            'total_all_cov': total_all_cov,
            'damaging_all_cov': damaging_all_cov,
            'total_5yr_avg': total_5yr_avg,
            'damaging_5yr_avg': damaging_5yr_avg,
            'total_5yr_cov': total_5yr_cov,
            'damaging_5yr_cov': damaging_5yr_cov,
            'years_available': len(total_cycles)
        }
    except Exception as e:
        st.error(f"Error calculating statistics: {str(e)}")
        return None
def get_variability_category(cov):
    """Categorize variability based on COV"""
    if cov < 15:
        return "Low", "🟢"
    elif cov <= 40:
        return "Moderate", "🟡"
    else:
        return "High", "🔴"
def main():
    st.title("❄️ Freeze-Thaw Cycle Data Analysis")
    st.markdown("Enter location coordinates to analyze freeze-thaw cycle data with 24-year and 5-year statistical summaries.")
    
    # Get all available seasons
    all_seasons = get_available_seasons()
    if not all_seasons:
        st.error("No freeze-thaw data files found. Please add Excel files to the project.")
        return
    
    # Get available states
    available_states = get_states_for_latest_season()
    if not available_states:
        st.error("No states found in the database.")
        return
    
    # Location Query Section
    st.subheader("🔍 Location Query")
    
    # Add helpful note about coordinates
    st.info("💡 **Coordinate Tips:** For US locations, longitude values are negative (west of Greenwich). "
            "For example: Denver, CO is at 39.7392, -104.9903")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        state = st.selectbox(
            "State",
            available_states,
            index=0,
            help="Select the state name"
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
    if st.button("Analyze Freeze-Thaw Data", type="primary"):
        # Validate inputs
        if not state:
            st.error("Please select a state.")
            return
        
        if latitude is None or longitude is None:
            st.error("Please enter both latitude and longitude values.")
            return
        
        # Load data from the most recent season for location search
        latest_season = all_seasons[-1]
        search_data = load_freeze_thaw_data_by_season(latest_season)
        if search_data.empty:
            st.error("No data available for location search.")
            return
        
        # Filter data by state first
        state_data = search_data[search_data['State'].str.contains(state, case=False, na=False)]
        
        if state_data.empty:
            st.error(f"No data found for state: {state}")
            available_states_list = sorted(search_data['State'].unique())
            st.info("Available states in database:")
            st.write(", ".join(available_states_list))
            return
        
        # Find nearest location
        try:
            nearest_location, distance = find_nearest_location(latitude, longitude, state_data)
            
            if nearest_location is None:
                st.warning(
                    f"No monitoring stations found within 50 km of the specified coordinates in {state}. "
                    "Try searching with coordinates closer to populated areas."
                )
                
                # Show available locations in the state
                st.subheader(f"Available monitoring stations in {state}:")
                display_data = state_data[['County', 'Latitude', 'Longitude', 'Total_Freeze_Thaw_Cycles', 'Damaging_Freeze_Thaw_Cycles']].copy()
                display_data['County'] = display_data['County'].apply(clean_county_name)
                st.dataframe(display_data, use_container_width=True)
                return
            
            # Clean county name for display
            clean_county = clean_county_name(nearest_location['County'])
            
            # Display results
            st.success(f"✅ Nearest monitoring station found!")
            
            # Location information
            st.subheader("📍 Station Details")
            
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.metric("County", clean_county)
                st.metric("State", nearest_location['State'])
                st.metric("Distance", f"{distance:.2f} km")
            
            with info_col2:
                st.metric("Station Latitude", f"{nearest_location['Latitude']:.6f}")
                st.metric("Station Longitude", f"{nearest_location['Longitude']:.6f}")
                st.metric("Available Seasons", len(all_seasons))
            
            # Calculate comprehensive statistics
            st.subheader("📊 Statistical Analysis")
            
            with st.spinner("Calculating historical statistics..."):
                stats = calculate_comprehensive_statistics(nearest_location, all_seasons)
            
            if stats is None:
                st.warning("Unable to calculate historical statistics for this location.")
                return
            
            # Display statistical summary
            st.markdown("### 📈 24-Year Analysis (All Available Data)")
            all_col1, all_col2 = st.columns(2)
            
            with all_col1:
                st.markdown("**Total Freeze-Thaw Cycles (24 Years)**")
                st.metric("Average", f"{stats['total_all_avg']:.1f}")
                
                total_all_var_cat, total_all_var_icon = get_variability_category(stats['total_all_cov'])
                st.metric("COV", f"{stats['total_all_cov']:.1f}%")
                st.markdown(f"{total_all_var_icon} **{total_all_var_cat} Variability**")
            
            with all_col2:
                st.markdown("**Damaging Freeze-Thaw Cycles (24 Years)**")
                st.metric("Average", f"{stats['damaging_all_avg']:.1f}")
                
                damaging_all_var_cat, damaging_all_var_icon = get_variability_category(stats['damaging_all_cov'])
                st.metric("COV", f"{stats['damaging_all_cov']:.1f}%")
                st.markdown(f"{damaging_all_var_icon} **{damaging_all_var_cat} Variability**")
            
            # LAST 5 YEARS SECTION
            st.markdown("### 📊 Last 5 Years Analysis")
            recent_col1, recent_col2 = st.columns(2)
            
            with recent_col1:
                st.markdown("**Total Freeze-Thaw Cycles (Last 5 Years)**")
                st.metric("Average", f"{stats['total_5yr_avg']:.1f}")
                
                total_5yr_var_cat, total_5yr_var_icon = get_variability_category(stats['total_5yr_cov'])
                st.metric("COV", f"{stats['total_5yr_cov']:.1f}%")
                st.markdown(f"{total_5yr_var_icon} **{total_5yr_var_cat} Variability**")
            
            with recent_col2:
                st.markdown("**Damaging Freeze-Thaw Cycles (Last 5 Years)**")
                st.metric("Average", f"{stats['damaging_5yr_avg']:.1f}")
                
                damaging_5yr_var_cat, damaging_5yr_var_icon = get_variability_category(stats['damaging_5yr_cov'])
                st.metric("COV", f"{stats['damaging_5yr_cov']:.1f}%")
                st.markdown(f"{damaging_5yr_var_icon} **{damaging_5yr_var_cat} Variability**")
            
            # Historical data table
            st.subheader("📋 Historical Data")
            
            # Display data table with better formatting
            display_df = stats['data'].copy()
            display_df['Total_Cycles'] = display_df['Total_Cycles'].round(1)
            display_df['Damaging_Cycles'] = display_df['Damaging_Cycles'].round(1)
            display_df = display_df.rename(columns={
                'Season': 'Season',
                'Total_Cycles': 'Total Cycles',
                'Damaging_Cycles': 'Damaging Cycles'
            })
            
            st.dataframe(display_df, use_container_width=True)
            
            # Summary insights
            st.subheader("🔍 Key Insights")
            
            insights = []
            
            # Compare 24-year vs 5-year averages
            total_trend = "increasing" if stats['total_5yr_avg'] > stats['total_all_avg'] else "decreasing"
            damaging_trend = "increasing" if stats['damaging_5yr_avg'] > stats['damaging_all_avg'] else "decreasing"
            
            insights.append(f"• **Recent Trend**: Total cycles are {total_trend} in the last 5 years compared to the 24-year average")
            insights.append(f"• **Damaging Cycles**: {damaging_trend} in the last 5 years compared to the 24-year average")
            
            # Variability insights
            if stats['total_all_cov'] > 40:
                insights.append("• **High Variability**: This location shows high year-to-year variation in freeze-thaw cycles")
            elif stats['total_all_cov'] < 15:
                insights.append("• **Consistent Pattern**: This location shows relatively consistent freeze-thaw patterns")
            
            # Data availability
            insights.append(f"• **Data Coverage**: Analysis based on {stats['years_available']} years of available data")
            
            for insight in insights:
                st.markdown(insight)
                
        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
            st.info("Please check your coordinates and try again.")
if __name__ == "__main__":
    main()