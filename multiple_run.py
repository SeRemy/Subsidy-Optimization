# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:27:55 2019

@author: srm-jba
"""

import run_basic as run
import numpy as np
import pandas as pd
#import xlrd
from xlwt import Workbook

def multiple_run():
    
    wb = Workbook()
    
    location      = "Garmisch"
    useable_roofarea  = 0.25
    electricity_demand = "medium"
    dhw_demand         = "medium"
    
    for building_type in ["ClusterA", "ClusterB"]:
        for building_age in ["0 1957", "1958 1978", "1979 1994"]:
            for options_scenario in ["benchmark", "s1"]:
                
                if building_type == "ClusterA":
                    apartment_quantity = 1
                    apartment_size = 110
                    household_size = 3  
                else:
                    apartment_quantity = 10
                    apartment_size = 70
                    household_size = 1
                    
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
                           "scenario": options_scenario,
                           "Design_heat_load" : True,
                           "store_start_vals" : False,
                           "load_start_vals" : False,
                           #File-names
                           "filename_results" : "results/" + building_type + "_" + \
                                                               building_age + "_" + options_scenario + ".pkl",                 
                           "filename_start_vals" :"start_values/" + building_type + "_" + \
                                                                  building_age + "_" + options_scenario + "_start.csv"}
                    
                Outputs = run.building_optimization(building_type, building_age, location, 
                                          household_size, electricity_demand, 
                                          dhw_demand, useable_roofarea, 
                                          apartment_quantity, apartment_size, options)
                
                
#                print(Outputs["res_heat_mod"][(7, 23)][1,1])
                
                if building_age == "0 1957":
                    ws_age = "1957"
                elif building_age == "1958 1978":
                    ws_age = "1978"
                elif building_age == "1979 1994":
                    ws_age = "1994"
                
                ws = wb.add_sheet(building_type + "_" + ws_age + "_" + options_scenario, cell_overwrite_ok=True)
                
                ws.write(0,0, "heat_mod")
                ws.write(10,0, "vent_loss")
                ws.write(20,0, "vent_inf")
                ws.write(0,29, "Input_weights")
                       
                for n in range(8):
                    for m in range(24):
                        
                        ws.write(n+1,0,n)
                        ws.write(n+11,0,n)
                        ws.write(n+21,0,n)
                        
                        weights_inputs = Outputs["inputs_clustered"]["weights"][n].astype(np.float64)
                        ws.write(n+1,29,label=weights_inputs)
                        
                        ws.write(0,m+1,m)
                        ws.write(10,m+1,m)
                        ws.write(20,m+1,m)
                        
                        heat_mod    = Outputs["res_heat_mod"][(7, 23)][n,m]
                        vent_loss   = Outputs["res_Q_vent_loss"][(7, 23)][n,m]
                        vent_inf    = Outputs["res_Q_v_Inf_wirk"][(7, 23)][n,m]

#                        write_heat_mod = heat_mod[n,m]#.astype(np.float64) #hier gibt er mir ein key error(0,0)
                        ws.write(n+1,m+1,heat_mod)
                        
#                        write_vent_loss = vent_loss[n,m]#.astype(np.float64)
                        ws.write(n+11,m+1,vent_loss)
                        
#                        write_vent_inf = vent_inf[n,m]#.astype(np.float64)
                        ws.write(n+21,m+1,vent_inf)
                    
                    
                    
    wb.save("results/vent_try.xls")
                
multiple_run()
                
                