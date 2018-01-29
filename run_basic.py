#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author: jte-sre
"""

from __future__ import division
import numpy as np
import pickle

import python.clustering_medoid as clustering
import python.parse_inputs as pik
import python.building_optimization as opti
import python.reference_building as ref_bui
import python.read_basic as reader

def building_optimization(building_type, building_age, location, 
                          household_size, electricity_demand, 
                          dhw_demand):
    #%% Read inputs
    
    raw_inputs = {}
    raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/household/dhw_"+ household_size + "_" + dhw_demand + ".csv") / 1000 )
    raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/household/electricity_" + household_size + "_" + electricity_demand + ".csv") / 1000)
    raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/household/int_gains_" + household_size + "_" + electricity_demand + ".csv") / 1000)
    raw_inputs["solar_roof"]  = np.maximum(0, np.loadtxt("raw_inputs/location/" + location + "/solar_rad_roof.csv") / 1000)
    raw_inputs["solar_south"] = np.maximum(0, np.loadtxt("raw_inputs/location/" + location + "/solar_rad_s.csv") / 1000)
    raw_inputs["solar_east"]  = np.maximum(0, np.loadtxt("raw_inputs/location/" + location + "/solar_rad_e.csv") / 1000)
    raw_inputs["solar_north"] = np.maximum(0, np.loadtxt("raw_inputs/location/" + location + "/solar_rad_n.csv") / 1000)
    raw_inputs["solar_west"]  = np.maximum(0, np.loadtxt("raw_inputs/location/" + location + "/solar_rad_w.csv") / 1000)
    raw_inputs["temperature"] = np.loadtxt("raw_inputs/location/" + location + "/temperature.csv")
    
    #%% Clustering Inputdata
    
    number_clusters = 8
    inputs_clustering = np.array([raw_inputs["electricity"], 
                                  raw_inputs["dhw"],                              
                                  raw_inputs["solar_roof"],
                                  raw_inputs["temperature"],
                                  raw_inputs["solar_south"],
                                  raw_inputs["solar_west"],
                                  raw_inputs["solar_east"],
                                  raw_inputs["solar_north"],
                                  raw_inputs["int_gains"]
                                  ])
                  
    (inputs, nc, z) = clustering.cluster(inputs_clustering, 
                                         number_clusters,
                                         norm = 2,
                                         mip_gap = 0.0,
                                         weights = [8,8,8,3,1,1,1,1,1])
                 
    # Determine time steps per day
    len_day = int(inputs_clustering.shape[1] / 365)
    clustered = {}
    clustered["electricity"]   = inputs[0]
    clustered["dhw"]           = inputs[1]
    clustered["solar_irrad"]   = inputs[2]
    clustered["temperature"]   = inputs[3]
    clustered["solar_s"]       = inputs[4]
    clustered["solar_w"]       = inputs[5]
    clustered["solar_e"]       = inputs[6]
    clustered["solar_n"]       = inputs[7]
    clustered["int_gains"]     = inputs[8]
    clustered["weights"]       = nc
    clustered["z"]             = z
    
    clustered["inside_temp"]       = 20
    clustered["inside_temp_night"] = 16

    clustered["standard_temp"] = -12
    clustered["delta_T"]       = np.maximum(0,(clustered["inside_temp"] - 
                                               clustered["temperature"]))
    
    #%% Load devices, econmoics, etc.
    
    devs = pik.read_devices(timesteps           = len_day, 
                            days                = number_clusters,
                            temperature_ambient = clustered["temperature"],
                            temperature_design  = clustered["standard_temp"], 
                            solar_irradiation   = clustered["solar_irrad"],
                            days_per_cluster    = clustered["weights"])
    
    (economics, params, devs, ep_table, shell_eco) = pik.read_economics(devs)
    params    = pik.compute_parameters(params, number_clusters, len_day)
    subsidies = pik.read_subsidies() 
    buildings = pik.parse_building_parameters()
    scenarios = pik.retrofit_scenarios()
    
    #%% Chose data for the chosen building and calculate reference building
    
    building = {}
    building["U-values"]   = scenarios[building_type][building_age]
    building["dimensions"] = buildings[building_type][building_age]
    ref_building = ref_bui.reference_building(building["dimensions"])
    
    #%% Store clustered input parameters
    
    filename = "results/inputs_" + building_type + "_" + building_age + ".pkl"
    with open(filename, "wb") as f_in:
        pickle.dump(economics, f_in, pickle.HIGHEST_PROTOCOL)
        pickle.dump(devs, f_in, pickle.HIGHEST_PROTOCOL)
        pickle.dump(clustered, f_in, pickle.HIGHEST_PROTOCOL)
        pickle.dump(params, f_in, pickle.HIGHEST_PROTOCOL)
        pickle.dump(building, f_in, pickle.HIGHEST_PROTOCOL)
    
    #%% Define dummy parameters, options and start optimization
    
    max_emi = 99999
    max_cost = 99999
    
    options={"filename_results" : "results/" + building_type + "_" + building_age + ".pkl",
             "opt_costs" : True,
             "EEG": True,
             "KfW": True,
             "KWKG": True,         
             "Bafa_chp": True,
             "Bafa_hp": True,
             "Bafa_stc": True,
             "Bafa_pellet": True,
             "kfw_eff_buildings" : True,
             "kfw_single_mea" : True,
             "HP tariff": True,
             "dhw_electric" : False,
             "New_Building": False,
             "MFH": False,
             "scenario": "free",
             "Design_heat_load" : False,
             "store_start_vals" : True,
             "load_start_vals" : False,
             "filename_start_vals" :"start_values/" + building_type + "_" + building_age + "_start.csv"}
             
    (costs, emission) = opti.compute(economics, devs, clustered, params, options, 
                                     building, ref_building, shell_eco, subsidies,
                                     ep_table, max_emi, max_cost)
    
    results = reader.read_results(building_type + "_" + building_age)

    return results
    
#%% Define Building parameters: 

if __name__ == "__main__":
    
    # Building parameters: 
    building_type = "SFH"       # SFH, TH, MFH, AB
    
    building_age  = "1958 1968" # 0 1859, 1860 1918, 1919 1948, 1949 1957, 1958 1968, 1969 1978, 
                                # 1979 1983 1984 1994, 1995 2001, 2002 2009, 2010 2015, 2016 2100  
    
    location      = "Essen"   # Bremerhaven, Rostock, Hamburg, Potsdam, Essen, Bad Marienberg, Kassel, Braunlage, 
                              # Chemnitz, Hof, Fichtelberg, Mannheim, Mühldorf, Stötten, Garmisch    
    
    #Household parameters: 
    household_size     = "3"        # 1, 2, 3, 4, 5
    electricity_demand = "medium"   # low, medium, high  
    dhw_demand         = "medium"   # low, medium, high  
    
    Outputs = building_optimization(building_type, building_age, location, 
                                    household_size, electricity_demand, 
                                    dhw_demand)