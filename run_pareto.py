#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: jte-sre
"""
from __future__ import division
import numpy as np
import pickle
import clustering_medoid as clustering
import parse_inputs as pik
import building_optimization as opti
import reference_building
import matplotlib.pyplot as plt

#%% Read inputs

building = "Testbuilding"
raw_inputs = {}

raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/dhw.csv"))
raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/electricity.csv"))
raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/internal_gains.csv") / 1000)

raw_inputs["solar_roof"]  = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/solar_rad_roof.csv") / 1000)
raw_inputs["solar_south"] = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/solar_rad_s.csv") / 1000)
raw_inputs["solar_east"]  = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/solar_rad_e.csv") / 1000)
raw_inputs["solar_north"] = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/solar_rad_n.csv") / 1000)
raw_inputs["solar_west"]  = np.maximum(0, np.loadtxt("raw_inputs/"+building+"/solar_rad_w.csv") / 1000)

raw_inputs["temperature"]   = np.loadtxt("raw_inputs/"+building+"/temperature.csv")

#%% Clustering Inputs

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
                                     weights = [1,1,1,0,4,4,4,4,2,4])
             
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
clustered["space_heating"] = inputs[8]
clustered["weights"]       = nc
clustered["z"]             = z
clustered["inside_temp"]   = 20
clustered["standard_temp"] = -12
clustered["delta_T"]       = np.maximum(0,(clustered["inside_temp"] - 
                                           clustered["temperature"]))
                                         
#%% Load devices, econmoics, etc.

devs = pik.read_devices(timesteps = len_day, 
                        days = number_clusters,
                        temperature_ambient = clustered["temperature"],
                        temperature_design = clustered["standard_temp"], 
                        solar_irradiation = clustered["solar_irrad"],
                        days_per_cluster = clustered["weights"])

(eco, par, devs, build_par, ep_table) = pik.read_economics(devs)

par = pik.compute_parameters(par, number_clusters, len_day)

sub_par = pik.read_subsidies() 

restruc = pik.read_restructuring(eco)

ref_building = reference_building.calculate_reference_energy_demand()

#%% Store clustered input parameters
filename = "results/inputs_"+building+".pkl"

with open(filename, "wb") as f_in:
    pickle.dump(eco, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(devs, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(clustered, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(par, f_in, pickle.HIGHEST_PROTOCOL)
    pickle.dump(restruc, f_in, pickle.HIGHEST_PROTOCOL)

#%% Free, multi-objective optimization with all restrictions

emi_max = 99999
cost_max = 99999
filename_save = "results/free_"
filename_start = "start_values/free_"
sub = False

options={"EEG": sub,
         "KfW": sub,
         "KWKG": sub,         
         "Bafa_chp": sub,
         "Bafa_hp": sub,
         "Bafa_stc": sub,
         "Bafa_pellet": sub,
         "kfw_eff_buildings" : sub,
         "kfw_single_mea" : sub,
         "opt_costs" : True,
         "HP tariff": True,
         "dhw_electric" : False,
         "New_Building":False,
         "MFH":False,
         "scenario": "free",
         "store_start_vals" : True,
         "load_start_vals" : False
         }

#%% Run cost-minimzation:

options["opt_costs"] = True
options["load_start_vals"] = False
options["filename_results"] = filename_save + "0.pkl"
options["filename_start_vals"] = filename_start + "0.csv"

(min_cost, max_emi) = opti.compute(eco, devs, clustered, par, options, restruc, 
                                     build_par, ref_building, sub_par, ep_table, 
                                     emi_max, cost_max)

# Second optimization to minimize the emission at minimal costs
options["opt_costs"] = False
options["load_start_vals"] = True
options["filename_results"] = filename_save + "0.pkl"
options["filename_start_vals"] = filename_start + "0.csv"

(min_cost, max_emi) = opti.compute(eco, devs, clustered, par, options, restruc, 
                                     build_par, ref_building, sub_par, ep_table, 
                                     max_emi, min_cost + 0.01)

#%% Run emission-minimization:

options["opt_costs"] = False
options["load_start_vals"] = False
options["filename_results"] = filename_save + "9.pkl"
options["filename_start_vals"] = filename_start + "9.csv"

(max_cost, min_emi) = opti.compute(eco, devs, clustered, par, options, restruc,
                                     build_par, ref_building, sub_par, ep_table,
                                     emi_max, cost_max)

# Second optimization to minimize the costs at minimal emissions
options["opt_costs"] = True
options["load_start_vals"] = True
options["filename_results"] = filename_save + "9.pkl"
options["filename_start_vals"] = filename_start + "9.csv"

(max_cost, min_emi) = opti.compute(eco, devs, clustered, par, options, restruc, 
                                     build_par, ref_building, sub_par, ep_table, 
                                     min_emi + 0.01, max_cost)

#%% Run multiple simulations
nr_sim = 8
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
    
    (cost[i], emi[i]) = opti.compute(eco, devs, clustered, par, options, restruc, 
                                       build_par, ref_building, sub_par, ep_table, limit_emi, cost_max)
    
    prev_emi = emi[i]

emi_list = list(emi.values())
cost_list = list(cost.values())

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