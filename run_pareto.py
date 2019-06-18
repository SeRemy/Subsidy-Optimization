#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: jte-sre
"""
from __future__ import division
import numpy as np
import pickle
import matplotlib.pyplot as plt

import python.clustering_medoid as clustering
import python.parse_inputs as pik
import python.building_optimization as opti
import python.reference_building as ref_bui
import python.read_vent as read_vent

#%% Define Parameters

building_type = "ClusterA"       # ClusterA, ClusterB

building_age  = "0 1957" # 0 1957, 1958 1978, 1979 1994

location      = "Garmisch"# Bremerhaven, Rostock, Hamburg, Potsdam, Essen, Bad Marienberg, Kassel, Braunlage, 
                          # Chemnitz, Hof, Fichtelberg, Mannheim, Mühldorf, Stötten, Garmisch    

#Household parameters: 
household_size     = 1          # 1, 2, 3, 4, 5
apartment_quantity = 1         # 4, 6, 8, 10, 12
apartment_size     = 110
electricity_demand = "medium"   # low, medium, high  
dhw_demand         = "medium"   # low, medium, high  

sub = True

#%% Read inputs

raw_inputs = {}

if building_type == "ClusterA":
    raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/sfh/dhw_" + str(household_size) + "_" + dhw_demand + ".csv") / 1000 )
    raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/sfh/electricity_" + str(household_size) + "_" + electricity_demand + ".csv") / 1000)
    raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/sfh/int_gains_" + str(household_size) + "_" + electricity_demand + ".csv") / 1000)
elif building_type == "ClusterB":
    raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/mfh/dhw_mfh_" + str(apartment_quantity) + ".csv") / 1000 )
    raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/mfh/electricity_" + str(apartment_quantity) + ".csv") / 1000)
    raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/mfh/int_gains_" + str(apartment_quantity) + ".csv") / 1000)

raw_inputs["solar_roof"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" + location + "_solar_roof.csv") / 1000)
raw_inputs["solar_south"] = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" + location + "_solar_south.csv") / 1000)
raw_inputs["solar_east"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" + location + "_solar_east.csv") / 1000)
raw_inputs["solar_north"] = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" + location + "_solar_north.csv") / 1000)
raw_inputs["solar_west"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" + location + "_solar_west.csv") / 1000)

raw_inputs["temperature"] = np.loadtxt("raw_inputs/weather_files/" + location + "_temperature.csv")

raw_inputs["wind_speed"] = np.loadtxt("raw_inputs/weather_files/" + location + "_windspeed.csv")
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
                              raw_inputs["wind_speed"],
                              raw_inputs["int_gains"]])                                
                  
(inputs, nc, z) = clustering.cluster(inputs_clustering, 
                                     number_clusters,
                                     norm = 2,
                                     mip_gap = 0.0,
                                     weights = [8,8,8,3,1,1,1,1,1,1])
             
# Determine time steps per day
len_day = int(inputs_clustering.shape[1] / 365)
    
clustered = {}

clustered["electricity"]   = inputs[0]
clustered["dhw"]           = inputs[1]
clustered["solar_roof"]    = inputs[2]
clustered["temp_ambient"]  = inputs[3]
clustered["solar_s"]       = inputs[4]
clustered["solar_w"]       = inputs[5]
clustered["solar_e"]       = inputs[6]
clustered["solar_n"]       = inputs[7]
clustered["wind_speed"]    = inputs[8]                                                                          
clustered["int_gains"]     = inputs[9]

clustered["weights"]       = nc

clustered["temp_indoor"]   =  20
clustered["temp_design"]   = -12

clustered["temp_delta"]    = np.maximum(0,(clustered["temp_indoor"] - 
                                           clustered["temp_ambient"]))
                                         
#%% Load devices, econmoics, etc.

devs = pik.read_devices(timesteps               = len_day, 
                            days                = number_clusters,
                            temperature_ambient = clustered["temp_ambient"],
                            temperature_design  = clustered["temp_design"], 
                            solar_irradiation   = clustered["solar_roof"],
                            days_per_cluster    = clustered["weights"])
    
(economics, params, devs, ep_table, shell_eco) = pik.read_economics(devs) 
params    = pik.compute_parameters(params, number_clusters, len_day)
subsidies = pik.read_subsidies(economics) 
buildings = pik.parse_building_parameters()
scenarios = pik.retrofit_scenarios()

(vent, df_vent) = read_vent.read_vent()

vent["n_50_table"] = vent["n_50_table"][building_age]

#%% Chose data for the chosen building and calculate reference building
    
building = {}
building["U-values"]   = scenarios[building_type][building_age]
building["dimensions"] = buildings[building_type][building_age]
building["usable_roof"] = 0.25
building["dimensions"]["Area"] = apartment_quantity * apartment_size
building["quantity"] = apartment_quantity 

ref_building = ref_bui.reference_building(building["dimensions"])

#%% Free, multi-objective optimization with all restrictions

emi_max = 99999
cost_max = 99999

filename_save = "results/free_"
filename_start = "start_values/free_"

options = {#Optimization of costs (True) or emissions (False)        
           "opt_costs" : True,
           #Subsidy programs               
           "EEG": True,
           "kfw_battery": True,
           "KWKG": True,           
           "Bafa_chp": True,
           "Bafa_hp": True,
           "Bafa_stc": True,
           "Bafa_pellet": True,
           "kfw_eff_buildings" : True,
           "kfw_single_mea" : True,         
           #Further parameters
           "New_Building" : False,
           "dhw_electric" : False,
           "scenario": "free",
           "Design_heat_load" : True,
           "store_start_vals" : True,
           "load_start_vals" : False,
         }
if building_type == "ClusterB":
    options["ClusterB"] = True
else:
    options["ClusterB"] = False

#%% Store clustered input parameters

filename = "results/inputs_" + building_type + "_" + building_age + "_" + options["scenario"] + ".pkl"
with open(filename, "wb") as f_in:
    pickle.dump(economics, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(devs, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(clustered, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(params, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(building, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(subsidies, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(ref_building, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(ep_table, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(shell_eco, f_in, pickle.HIGHEST_PROTOCOL)

#%% Run cost-minimzation:

#options["opt_costs"] = True
#options["load_start_vals"] = False
options["filename_results"] = filename_save + "0.pkl"
options["filename_start_vals"] = filename_start + "0.csv"

(min_cost, max_emi, x_vent, df_windows, res_n_total, air_flow1, air_flow2) = opti.compute(economics, devs, clustered, df_vent, params, options, 
                                                                                           building, ref_building, shell_eco, subsidies,
                                                                                           ep_table, emi_max, cost_max, vent)

# Second optimization to minimize the emission at minimal costs
options["opt_costs"] = False
options["load_start_vals"] = True
options["filename_results"] = filename_save + "0.pkl"
options["filename_start_vals"] = filename_start + "0.csv"

(min_cost, max_emi, x_vent, df_windows, res_n_total, air_flow1, air_flow2) = opti.compute(economics, devs, clustered, df_vent, params, options, 
                                                                                           building, ref_building, shell_eco, subsidies,
                                                                                           ep_table, max_emi, min_cost + 10, vent)

#%% Run emission-minimization:

options["opt_costs"] = False
options["load_start_vals"] = False
options["filename_results"] = filename_save + "9.pkl"
options["filename_start_vals"] = filename_start + "9.csv"

(max_cost, min_emi, x_vent, df_windows, res_n_total, air_flow1, air_flow2) = opti.compute(economics, devs, clustered, df_vent, params, options, 
                                                                                           building, ref_building, shell_eco, subsidies,
                                                                                           ep_table, emi_max, cost_max, vent)

# Second optimization to minimize the costs at minimal emissions
options["opt_costs"] = True
options["load_start_vals"] = True
options["filename_results"] = filename_save + "9.pkl"
options["filename_start_vals"] = filename_start + "9.csv"

(max_cost, min_emi, x_vent, df_windows, res_n_total, air_flow1, air_flow2) = opti.compute(economics, devs, clustered, df_vent, params, options, 
                                                                                           building, ref_building, shell_eco, subsidies,
                                                                                           ep_table, min_emi + 0.01, max_cost, vent)

#%% Run multiple simulations
nr_sim = 25

options["opt_costs"] = True
options["load_start_vals"] = False
prev_emi = max_emi
emi = {}
cost = {}

emi[0] = max_emi
cost[0] = min_cost

emi[9] = min_emi
cost[9] = max_cost

for i in range(1, nr_sim+1):
    
    limit_emi = min(max_emi - (max_emi - min_emi) * i / (nr_sim + 1), emi_max)#prev_emi * 0.999)

    options["filename_results"] = "results/free_" + str(i) + ".pkl"
    
    (cost[i], emi[i], x_vent, df_windows, res_n_total, air_flow1, air_flow2) = opti.compute(economics, devs, clustered, df_vent, params, options, 
                                                                                           building, ref_building, shell_eco, subsidies,
                                                                                           ep_table, limit_emi, cost_max, vent)
    
    prev_emi = emi[i]

emi_list = list(emi.values())
cost_list = list(cost.values())

emi_list.sort(reverse = True)
cost_list.sort()

plt.rcParams['savefig.facecolor'] = "0.8"

def example_plot(ax, fontsize=12):
    ax.plot(emi_list,cost_list)

    ax.locator_params(nbins=6)
    ax.set_xlabel('CO2-Emissionen', fontsize=fontsize)
    ax.set_ylabel('Jaehrliche Kosten', fontsize=fontsize)
    ax.set_title('CO2-Vermeidungskosten', fontsize=fontsize)

plt.close('all')
fig, ax = plt.subplots()
example_plot(ax, fontsize=18)