# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 18:04:44 2019

@author: srm-jba
"""


import run_basic as run
import multiple_run as multiple_run
from xlwt import Workbook
import numpy as np

def multiple_run_u_values():
    
    wb = Workbook()
    
    ws_1 = wb.add_sheet("Übersicht_U-Values", cell_overwrite_ok=True)
    
    ws_1.write(0,0,   "Szenario")
    ws_1.write(1,0,   "Gebäudetyp")
    ws_1.write(2,0,   "Baujahr")
    ws_1.write(3,0,   "Außenwand")
    ws_1.write(4,0,   "Boden")
    ws_1.write(5,0,   "Dach")
    ws_1.write(6,0,   "Fenster")
    
    ws_1.write(8,0,   "Szenario")
    ws_1.write(9,0,   "Gebäudetyp")
    ws_1.write(10,0,  "Baujahr")
    ws_1.write(11,0,  "Außenwand")
    ws_1.write(12,0,  "Boden")
    ws_1.write(13,0,  "Dach")
    ws_1.write(14,0,  "Fenster")
    
    ws_1.write(16,0,  "Szenario")
    ws_1.write(17,0,  "Gebäudetyp")
    ws_1.write(18,0,  "Baujahr")
    ws_1.write(19,0,  "Außenwand")
    ws_1.write(20,0,  "Boden")
    ws_1.write(21,0,  "Dach")
    ws_1.write(22,0,  "Fenster")
    
    ws_1.write_merge(0,0,1,6,   "benchmark")
    ws_1.write_merge(8,8,1,6,   "retrofit")
    ws_1.write_merge(16,16,1,6,  "advanced retrofit")
    
    ws_1.write_merge(1,1,1,3,   "SFH")
    ws_1.write_merge(1,1,4,6,   "MFH")
    ws_1.write_merge(9,9,1,3,   "SFH")
    ws_1.write_merge(9,9,4,6,   "MFH")
    ws_1.write_merge(17,17,1,3, "SFH")
    ws_1.write_merge(17,17,4,6, "MFH")
    
    ws_1.write(2,1,   "0 1957")
    ws_1.write(2,2,   "1958 1978")
    ws_1.write(2,3,   "1979 1994")
    ws_1.write(2,4,   "0 1957")
    ws_1.write(2,5,   "1958 1978")
    ws_1.write(2,6,   "1979 1994")
    ws_1.write(10,1,  "0 1957")
    ws_1.write(10,2,  "1958 1978")
    ws_1.write(10,3,  "1979 1994")
    ws_1.write(10,4,  "0 1957")
    ws_1.write(10,5,  "1958 1978")
    ws_1.write(10,6,  "1979 1994")
    ws_1.write(18,1,  "0 1957")
    ws_1.write(18,2,  "1958 1978")
    ws_1.write(18,3,  "1979 1994")
    ws_1.write(18,4,  "0 1957")
    ws_1.write(18,5,  "1958 1978")
    ws_1.write(18,6,  "1979 1994")
    
    ws_2 = wb.add_sheet("Übersicht_vent", cell_overwrite_ok=True)
    
    ws_2.write(0,0,   "Szenario")
    ws_2.write(1,0,   "Gebäudetyp")
    ws_2.write(2,0,   "Baujahr")
    ws_2.write(3,0,   "Anteil Lüftung- an Gesamtwärmeverlusten")
    ws_2.write(4,0,   "Anteil Infiltrations- an Lüftungswärmeverlusten")
    ws_2.write(5,0,   "jährlich gemittelte Luftwechselrate")
    
    ws_2.write(7,0,   "Szenario")
    ws_2.write(8,0,   "Gebäudetyp")
    ws_2.write(9,0,   "Baujahr")
    ws_2.write(10,0,  "Anteil Lüftung- an Gesamtwärmeverlusten")
    ws_2.write(11,0,  "Anteil Infiltrations- an Lüftungswärmeverlusten")
    ws_2.write(12,0,  "jährlich gemittelte Luftwechselrate")
    
    ws_2.write(14,0,   "Szenario")
    ws_2.write(15,0,   "Gebäudetyp")
    ws_2.write(16,0,   "Baujahr")
    ws_2.write(17,0,  "Anteil Lüftung- an Gesamtwärmeverlusten")
    ws_2.write(18,0,  "Anteil Infiltrations- an Lüftungswärmeverlusten")
    ws_2.write(19,0,  "jährlich gemittelte Luftwechselrate")
    
    ws_2.write_merge(0,0,1,6, "benchmark")
    ws_2.write_merge(7,7,1,6, "retrofit")
    ws_2.write_merge(14,14,1,6, "retrofit")
    ws_2.write_merge(1,1,1,3, "SFH")
    ws_2.write_merge(1,1,4,6, "MFH")
    ws_2.write_merge(8,8,1,3, "SFH")
    ws_2.write_merge(8,8,4,6, "MFH")
    ws_2.write_merge(15,15,1,3, "SFH")
    ws_2.write_merge(15,15,4,6, "MFH")
    
    ws_2.write(2,1,   "0 1957")
    ws_2.write(2,2,   "1958 1978")
    ws_2.write(2,3,   "1979 1994")
    ws_2.write(2,4,   "0 1957")
    ws_2.write(2,5,   "1958 1978")
    ws_2.write(2,6,   "1979 1994")
    ws_2.write(9,1,   "0 1957")
    ws_2.write(9,2,   "1958 1978")
    ws_2.write(9,3,   "1979 1994")
    ws_2.write(9,4,   "0 1957")
    ws_2.write(9,5,   "1958 1978")
    ws_2.write(9,6,   "1979 1994")
    ws_2.write(16,1,   "0 1957")
    ws_2.write(16,2,   "1958 1978")
    ws_2.write(16,3,   "1979 1994")
    ws_2.write(16,4,   "0 1957")
    ws_2.write(16,5,   "1958 1978")
    ws_2.write(16,6,   "1979 1994")
    
    location            = "Garmisch"
    useable_roofarea    = 0.25
    electricity_demand  = "medium"
    dhw_demand          = "medium"
    
    for building_type in ["ClusterA", "ClusterB"]:
        for building_age in ["0 1957", "1958 1978", "1979 1994"]:
            for options_scenario in ["benchmark", "s1", "s2"]:
                
                if building_type == "ClusterA":
                    apartment_quantity  = 1
                    apartment_size      = 110
                    household_size      = 3  
                else:
                    apartment_quantity  = 10
                    apartment_size      = 70
                    household_size      = 1
                    
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
                
                if building_age == "0 1957":
                    ws_age = "1957"
                elif building_age == "1958 1978":
                    ws_age = "1978"
                elif building_age == "1979 1994":
                    ws_age = "1994"
                
                ws = wb.add_sheet(building_type + "_" + ws_age + "_" + options_scenario, cell_overwrite_ok=True)
                
                ws.write(0,0,   "Q_Ht")
                ws.write(10,0,  "vent_loss")
                ws.write(20,0,  "vent_inf")
                ws.write(30,0,  "n_total")
                ws.write(0,29,  "Input_weights")
                ws.write(0,30,  "Input_temp")
                ws.write(7,27,  "yearly average")
                ws.write(17,27, "yearly average")
                ws.write(27,27, "yearly average")
                ws.write(37,27, "yearly average")
                ws.write(17,28, "portion of vent from total heat loss")
                ws.write(27,28, "portion of inf from vent heat loss")
                
                temp_array      = np.asarray(Outputs["inputs_clustered"]["temp_ambient"])
                temp_average    = np.mean(temp_array, axis = 1)
                       
                for n in range(8):
                    for m in range(24):
                        
                        ws.write(n+1,0,n)
                        ws.write(n+11,0,n)
                        ws.write(n+21,0,n)
                        ws.write(n+31,0,n)
                        
                        weights_inputs = Outputs["inputs_clustered"]["weights"][n].astype(np.float64)
                        ws.write(n+1,29,label=weights_inputs)
                        temp_inputs    = temp_average[n]
                        ws.write(n+1,30,label=temp_inputs)
                        
                        ws.write(0, m+1,m)
                        ws.write(10,m+1,m)
                        ws.write(20,m+1,m)
                        ws.write(30,m+1,m)
                        
                        Q_Ht        = Outputs["res_Q_Ht"][(7, 23)][n,m]
                        vent_loss   = Outputs["res_Q_vent_loss"][(7, 23)][n,m]
                        vent_inf    = Outputs["res_Q_v_Inf_wirk"][(7, 23)][n,m]
                        n_total     = Outputs["res_n_total"][(7, 23)][n,m]

                        ws.write(n+1, m+1,Q_Ht)
                        ws.write(n+11,m+1,vent_loss)
                        ws.write(n+21,m+1,vent_inf)                        
                        ws.write(n+31,m+1,n_total)
                        
                    av_Q_Ht         = sum(Outputs["res_Q_Ht"][(7, 23)][n, i] for i in range(24))
                    av_vent_loss    = sum(Outputs["res_Q_vent_loss"][(7, 23)][n, i] for i in range(24))
                    av_vent_inf     = sum(Outputs["res_Q_v_Inf_wirk"][(7, 23)][n, i] for i in range(24))
                    av_n_total      = sum(Outputs["res_n_total"][(7, 23)][n, i] for i in range(24))
                    
                    ws.write(n+1,  25, av_Q_Ht)
                    ws.write(n+11, 25, av_vent_loss)
                    ws.write(n+21, 25, av_vent_inf)
                    ws.write(n+31, 25, av_n_total)
                    
                    ws.write(n+1,  26, av_Q_Ht*Outputs["inputs_clustered"]["weights"][n])
                    ws.write(n+11, 26, av_vent_loss*Outputs["inputs_clustered"]["weights"][n])
                    ws.write(n+21, 26, av_vent_inf*Outputs["inputs_clustered"]["weights"][n])
                    ws.write(n+31, 26, av_n_total*Outputs["inputs_clustered"]["weights"][n])
                
                yr_av_Q_Ht_count      = 0
                yr_av_vent_loss_count = 0
                yr_av_vent_inf_count  = 0
                yr_av_n_total_count   = 0
                
                for d in range(8):
                    for t in range(24):
                        yr_av_Q_Ht_count      += Outputs["res_Q_Ht"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                        yr_av_vent_loss_count += Outputs["res_Q_vent_loss"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                        yr_av_vent_inf_count  += Outputs["res_Q_v_Inf_wirk"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                        yr_av_n_total_count   += Outputs["res_n_total"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                        
                yr_av_Q_Ht      = yr_av_Q_Ht_count/8760
                yr_av_vent_loss = yr_av_vent_loss_count/8760
                yr_av_vent_inf  = yr_av_vent_inf_count/8760
                yr_av_n_total   = yr_av_n_total_count/8760
                portion_vent    = yr_av_vent_loss/(yr_av_vent_loss+yr_av_Q_Ht)
                portion_inf     = yr_av_vent_inf/yr_av_vent_loss
                
                ws.write(8, 27, yr_av_Q_Ht)
                ws.write(18,27, yr_av_vent_loss)
                ws.write(28,27, yr_av_vent_inf)
                ws.write(38,27, yr_av_n_total)
                ws.write(18,28, portion_vent)
                ws.write(28,28, portion_inf)
                
                if options_scenario == "benchmark":
                    u_wall      = Outputs["inputs_building"]["U-values"]["standard"]["OuterWall"]["U-Value"]
                    u_floor     = Outputs["inputs_building"]["U-values"]["standard"]["GroundFloor"]["U-Value"]
                    u_roof      = Outputs["inputs_building"]["U-values"]["standard"]["Rooftop"]["U-Value"]
                    u_window    = Outputs["inputs_building"]["U-values"]["standard"]["Window"]["U-Value"]
                    
                    if building_age == "0 1957":
                        if building_type == "ClusterA":
                            ws_1.write(3,1, u_wall)
                            ws_1.write(4,1, u_floor)
                            ws_1.write(5,1, u_roof)
                            ws_1.write(6,1, u_window)
                            
                            ws_2.write(3,1, portion_vent) 
                            ws_2.write(4,1, portion_inf)
                            ws_2.write(5,1, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3,4, u_wall)
                            ws_1.write(4,4, u_floor)
                            ws_1.write(5,4, u_roof)
                            ws_1.write(6,4, u_window)
                            
                            ws_2.write(3,4, portion_vent) 
                            ws_2.write(4,4, portion_inf)
                            ws_2.write(5,4, yr_av_n_total)
                    elif building_age == "1958 1978":
                        if building_type == "ClusterA":
                            ws_1.write(3,2, u_wall)
                            ws_1.write(4,2, u_floor)
                            ws_1.write(5,2, u_roof)
                            ws_1.write(6,2, u_window)
                            
                            ws_2.write(3,2, portion_vent)
                            ws_2.write(4,2, portion_inf)
                            ws_2.write(5,2, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3,5, u_wall)
                            ws_1.write(4,5, u_floor)
                            ws_1.write(5,5, u_roof)
                            ws_1.write(6,5, u_window)
                            
                            ws_2.write(3,5, portion_vent)
                            ws_2.write(4,5, portion_inf)
                            ws_2.write(5,5, yr_av_n_total)
                    elif building_age == "1979 1994":
                        if building_type == "ClusterA":
                            ws_1.write(3,3, u_wall)
                            ws_1.write(4,3, u_floor)
                            ws_1.write(5,3, u_roof)
                            ws_1.write(6,3, u_window)
                            
                            ws_2.write(3,3, portion_vent) 
                            ws_2.write(4,3, portion_inf)
                            ws_2.write(5,3, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3,6, u_wall)
                            ws_1.write(4,6, u_floor)
                            ws_1.write(5,6, u_roof)
                            ws_1.write(6,6, u_window)
                            
                            ws_2.write(3,6, portion_vent)
                            ws_2.write(4,6, portion_inf)
                            ws_2.write(5,6, yr_av_n_total)
                    
                elif options_scenario == "s1":
                    u_wall      = Outputs["inputs_building"]["U-values"]["retrofit"]["OuterWall"]["U-Value"]
                    u_floor     = Outputs["inputs_building"]["U-values"]["retrofit"]["GroundFloor"]["U-Value"]
                    u_roof      = Outputs["inputs_building"]["U-values"]["retrofit"]["Rooftop"]["U-Value"]
                    u_window    = Outputs["inputs_building"]["U-values"]["retrofit"]["Window"]["U-Value"]
                    
                    if building_age == "0 1957":
                        if building_type == "ClusterA":
                            ws_1.write(3+8,1, u_wall)
                            ws_1.write(4+8,1, u_floor)
                            ws_1.write(5+8,1, u_roof)
                            ws_1.write(6+8,1, u_window)
                            
                            ws_2.write(10,1, portion_vent) 
                            ws_2.write(11,1, portion_inf)
                            ws_2.write(12,1, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3+8,4, u_wall)
                            ws_1.write(4+8,4, u_floor)
                            ws_1.write(5+8,4, u_roof)
                            ws_1.write(6+8,4, u_window)
                            
                            ws_2.write(10,4, portion_vent) 
                            ws_2.write(11,4, portion_inf)
                            ws_2.write(12,4, yr_av_n_total)
                    elif building_age == "1958 1978":
                        if building_type == "ClusterA":
                            ws_1.write(3+8,2, u_wall)
                            ws_1.write(4+8,2, u_floor)
                            ws_1.write(5+8,2, u_roof)
                            ws_1.write(6+8,2, u_window)
                            
                            ws_2.write(10,2, portion_vent)
                            ws_2.write(11,2, portion_inf)
                            ws_2.write(12,2, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3+8,5, u_wall)
                            ws_1.write(4+8,5, u_floor)
                            ws_1.write(5+8,5, u_roof)
                            ws_1.write(6+8,5, u_window)
                            
                            ws_2.write(10,5, portion_vent)
                            ws_2.write(11,5, portion_inf)
                            ws_2.write(12,5, yr_av_n_total)
                    elif building_age == "1979 1994":
                        if building_type == "ClusterA":
                            ws_1.write(3+8,3, u_wall)
                            ws_1.write(4+8,3, u_floor)
                            ws_1.write(5+8,3, u_roof)
                            ws_1.write(6+8,3, u_window)
                            
                            ws_2.write(10,3, portion_vent)
                            ws_2.write(11,3, portion_inf)
                            ws_2.write(12,3, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3+8,6, u_wall)
                            ws_1.write(4+8,6, u_floor)
                            ws_1.write(5+8,6, u_roof)
                            ws_1.write(6+8,6, u_window)
                            
                            ws_2.write(10,6, portion_vent)
                            ws_2.write(11,6, portion_inf)
                            ws_2.write(12,6, yr_av_n_total)
                            
                elif options_scenario == "s2":
                    u_wall      = Outputs["inputs_building"]["U-values"]["adv_retr"]["OuterWall"]["U-Value"]
                    u_floor     = Outputs["inputs_building"]["U-values"]["adv_retr"]["GroundFloor"]["U-Value"]
                    u_roof      = Outputs["inputs_building"]["U-values"]["adv_retr"]["Rooftop"]["U-Value"]
                    u_window    = Outputs["inputs_building"]["U-values"]["adv_retr"]["Window"]["U-Value"]
                    
                    if building_age == "0 1957":
                        if building_type == "ClusterA":
                            ws_1.write(3+16,1, u_wall)
                            ws_1.write(4+16,1, u_floor)
                            ws_1.write(5+16,1, u_roof)
                            ws_1.write(6+16,1, u_window)
                            
                            ws_2.write(17,1, portion_vent) 
                            ws_2.write(18,1, portion_inf)
                            ws_2.write(19,1, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3+16,4, u_wall)
                            ws_1.write(4+16,4, u_floor)
                            ws_1.write(5+16,4, u_roof)
                            ws_1.write(6+16,4, u_window)
                            
                            ws_2.write(17,4, portion_vent) 
                            ws_2.write(18,4, portion_inf)
                            ws_2.write(19,4, yr_av_n_total)
                    elif building_age == "1958 1978":
                        if building_type == "ClusterA":
                            ws_1.write(3+16,2, u_wall)
                            ws_1.write(4+16,2, u_floor)
                            ws_1.write(5+16,2, u_roof)
                            ws_1.write(6+16,2, u_window)
                            
                            ws_2.write(17,2, portion_vent)
                            ws_2.write(18,2, portion_inf)
                            ws_2.write(19,2, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3+16,5, u_wall)
                            ws_1.write(4+16,5, u_floor)
                            ws_1.write(5+16,5, u_roof)
                            ws_1.write(6+16,5, u_window)
                            
                            ws_2.write(17,5, portion_vent)
                            ws_2.write(18,5, portion_inf)
                            ws_2.write(19,5, yr_av_n_total)
                    elif building_age == "1979 1994":
                        if building_type == "ClusterA":
                            ws_1.write(3+16,3, u_wall)
                            ws_1.write(4+16,3, u_floor)
                            ws_1.write(5+16,3, u_roof)
                            ws_1.write(6+16,3, u_window)
                            
                            ws_2.write(17,3, portion_vent)
                            ws_2.write(18,3, portion_inf)
                            ws_2.write(19,3, yr_av_n_total)
                        elif building_type == "ClusterB":
                            ws_1.write(3+16,6, u_wall)
                            ws_1.write(4+16,6, u_floor)
                            ws_1.write(5+16,6, u_roof)
                            ws_1.write(6+16,6, u_window)
                            
                            ws_2.write(17,6, portion_vent)
                            ws_2.write(18,6, portion_inf)
                            ws_2.write(19,6, yr_av_n_total)

                    
                
    wb.save("results/u_values_vent_uebersicht.xls")
                
multiple_run_u_values()
#multiple_run.multiple_run()