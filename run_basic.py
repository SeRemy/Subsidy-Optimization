#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author: srm
"""
from __future__ import division
import numpy as np
import pandas as pd
import pickle
import python.clustering_medoid as clustering
import python.parse_inputs as pik
import python.building_optimization as opti
import python.reference_building as ref_bui
import python.read_basic as reader
import python.read_vent as read_vent


def building_optimization(building_type, building_age, location, 
                          household_size, electricity_demand, 
                          dhw_demand, useable_roofarea, 
                          apartment_quantity, apartment_size, options):
    
#%% Read inputs  
    
    raw_inputs = {} 
            
    # Weather data: 
    raw_inputs["solar_roof"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" + location + "_solar_roof.csv") / 1000)    
   
    raw_inputs["solar_south"] = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" 
                                              + location + "_solar_south.csv") / 1000)  
    
    raw_inputs["solar_east"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/"
                                               + location + "_solar_east.csv") / 1000)    
    
    raw_inputs["solar_north"] = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" 
                                              + location + "_solar_north.csv") / 1000)
    
    raw_inputs["solar_west"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" 
                                               + location + "_solar_west.csv") / 1000)
    
    raw_inputs["temperature"] = np.loadtxt("raw_inputs/weather_files/" 
                                              + location + "_temperature.csv")
    
    raw_inputs["wind_speed"]  = np.maximum(0, np.loadtxt("raw_inputs/weather_files/" 
                                              + location + "_windspeed.csv"))
    
    # Electricity, dhw and internal gains:
    
    if building_type == "ClusterA":    
        
        options["ClusterB"] = False
        
        raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/sfh/dhw_" 
                                      + str(household_size) + "_" + dhw_demand + ".csv") / 1000)       
        
        raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/sfh/electricity_" 
                                      + str(household_size) + "_" + electricity_demand + ".csv") / 1000)
        
        raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/sfh/int_gains_" 
                                      + str(household_size) + "_" + electricity_demand + ".csv") / 1000)
        
        
    if building_type == "ClusterB":
        
        options["ClusterB"] = True
        
        if electricity_demand == "low":
            raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/mfh/electricity_mfh_" 
                       + str(apartment_quantity) + ".csv") / 1000 * 0.75)
            
            raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/mfh/internal_gains_mfh_" 
                      + str(apartment_quantity) + ".csv") / 1000 * 0.75)
            
        elif electricity_demand == "medium":
            raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/mfh/electricity_mfh_" 
                          	+ str(apartment_quantity) + ".csv") / 1000)
            
            raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/mfh/internal_gains_mfh_" 
                          + str(apartment_quantity) + ".csv") / 1000)
            
        elif electricity_demand == "high":
            raw_inputs["electricity"] = np.maximum(0, np.loadtxt("raw_inputs/mfh/electricity_mfh_" 
                      + str(apartment_quantity) + ".csv") / 1000 * 1.25)
            
            raw_inputs["int_gains"]   = np.maximum(0, np.loadtxt("raw_inputs/mfh/internal_gains_mfh_" 
                      + str(apartment_quantity) + ".csv") / 1000 * 1.25)
            
        if dhw_demand == "low":            
            raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/mfh/dhw_mfh_" 
                                          + str(apartment_quantity) + ".csv") / 1000 * 0.75)
        
        elif dhw_demand == "medium":            
            raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/mfh/dhw_mfh_" 
                                          + str(apartment_quantity) + ".csv") / 1000)
        
        elif dhw_demand == "high":            
            raw_inputs["dhw"]         = np.maximum(0, np.loadtxt("raw_inputs/mfh/dhw_mfh_" 
                                          + str(apartment_quantity) + ".csv") / 1000 * 1.25)
            
            
    
    
    #%% Clustering Inputdata
    
    # add raw_inputs["ventilation_loss"]
    
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
    
    clustered["temp_delta"]       = np.maximum(0,(clustered["temp_indoor"] - 
                                               clustered["temp_ambient"]))
    
    #%% Load devices, econmoics, etc.
    
    devs = pik.read_devices(timesteps           = len_day, 
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
    building["usable_roof"] = useable_roofarea
    building["dimensions"]["Area"] = apartment_quantity * apartment_size
    building["quantity"] = apartment_quantity

    ref_building = ref_bui.reference_building(building["dimensions"])
    
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
    
    #%% Define dummy parameters, options and start optimization
    
    max_emi = 99999
    max_cost = 99999      
             
    (costs, emission, x_vent, df_windows, res_n_total, air_flow1, air_flow2) =  opti.compute(economics, devs, clustered, df_vent, params, options, 
                                                                                building, ref_building, shell_eco, subsidies,
                                                                                ep_table, max_emi, max_cost, vent)
                                 
    Outputs = reader.read_results(building_type + "_" + building_age +"_" + options["scenario"])
#    
#    #%% Ausgabe: 
# 
#    print(" ")
#    print(" ")
#    print(" ")
#    print("Annuität: " + str(round(Outputs["ObjVal"],1)) + " €/a")
#    print(" ")
#    
#    print("Emissionen: " + str(round(Outputs["4_emission"],1)) + " t/a")
#    print(" ")    
#    
#    print("Fördergelder:")
#    print(" ")
#    for i in Outputs["res_sub"].keys():       
#        if Outputs["res_sub"][i] > 0.0:
#            print(i + ": " + str(round(Outputs["res_sub"][i],1)) + " €/a")
#            print(" ")
#    
#    print("Anlagentechnik:")
#    print(" ")
#    for i in Outputs["5_x"].keys():       
#        if Outputs["5_x"][i] == 1:
#            if i == "boiler" or i == "eh" or i == "hp_air" or \
#                i == "hp_geo" or i == "chp" or i == "pellet":
#                j = " kW"
#            elif i =="stc" or i =="pv":
#                j = " m²"
#            elif i == "tes":
#                j = " m³"
#            elif i == "bat":
#                j = " kWh"
#            
#            print(i + ": " + str(round(Outputs["6_cap"][i],1)) + j)
#            print(" ")
#            
#    print("Gebäudehülle:")
#    print(" ")
#    for i in Outputs["7_x_restruc"].keys():
#        if Outputs["7_x_restruc"][i] == 1:        
#            print(i)
#            print(" ")
#    
#    print("")
#    if x_vent == 1:
#        print("Lüftungssystem: ja")
#    else:
#        print("Lüftungssystem: nein")
#    print("")  
#    print("n_50: " + str(n_50))
#
    return Outputs
    
#%% Define Building parameters: 

if __name__ == "__main__":
    
    
    # Building parameters: 
    building_type = "ClusterA"  # ClusterA, ClusterB
    
    building_age  = "1958 1978"    # 0 1957, 1958 1978, 1979 1994
    
    location      = "Garmisch"   # Bremerhaven, Rostock, Hamburg, Potsdam, Essen, 
                                # Bad Marienberg (Westerwald), Kassel, 
                                # Braunlage (Harz), Chemnitz, Hof (Oberfranken), 
                                # Fichtelberg (Erzgebirge), Mannheim, 
                                # Mühldorf (München), Stötten (Kempten), Garmisch    
        
    useable_roofarea  = 0.25    #Default value: 0.25
    
    apartment_quantity = 1      # SFH and TH: 1 - Always
                                # MFH: 4, 6, 8, 10, 12
                                # AB: 15, 20, 25, 30, 35 
                                
    apartment_size = 110        # SFH and TH: average 110 - 120 m² in Germany
                                # MFH and AB: avergae 60 - 70 m² in Germany 
    
    household_size = 3          # SFH and TH: 1, 2, 3, 4, 5
                                # MFH and AB: not relevant
    
    electricity_demand = "medium"   # low, medium, high  
    
    dhw_demand         = "medium"   # low, medium, high
    
    #%% Set options
    
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
               "store_start_vals" : False,
               "load_start_vals" : False,
               #File-names
               "filename_results" : "results/" + building_type + "_" + \
                                                   building_age + "_" + "benchmark" + ".pkl",                 
               "filename_start_vals" :"start_values/" + building_type + "_" + \
                                                      building_age + "_start.csv"}
        
    Optimization_results = building_optimization(building_type, building_age, location, 
                                                 household_size, electricity_demand, 
                                                 dhw_demand, useable_roofarea, 
                                                 apartment_quantity, apartment_size, 
                                                 options)    