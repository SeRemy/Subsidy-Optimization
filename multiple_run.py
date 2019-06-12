# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:27:55 2019

@author: srm-jba
"""

import run_basic as run
import numpy as np
from xlwt import Workbook

def multiple_run():
    
    wb = Workbook()
    
    ws_1 = wb.add_sheet("Übersicht", cell_overwrite_ok=True)
    
    for i in [0,9,18]:
        
        ws_1.write(0+i,0,   "Szenario")
        ws_1.write(1+i,0,   "Gebäudetyp")
        ws_1.write(2+i,0,   "Baujahr")
        ws_1.write(3+i,0,   "Anteil Lüftung- an Gesamtwärmeverlusten")
        ws_1.write(4+i,0,   "Anteil Infiltrations- an Lüftungswärmeverlusten")
        ws_1.write(5+i,0,   "jährlich gemittelte Luftwechselrate")
        ws_1.write(6+i,0,   "flächenspezifische Gesamtwärmeverluste")
        ws_1.write(7+i,0,   "flächenspezifische Lüstungswärmeverluste")
        
        ws_1.write_merge(1+i,1+i,1,3, "SFH")
        ws_1.write_merge(1+i,1+i,4,6, "MFH")
        
        ws_1.write(2+i,1,   "0 1957")
        ws_1.write(2+i,2,   "1958 1978")
        ws_1.write(2+i,3,   "1979 1994")
        ws_1.write(2+i,4,   "0 1957")
        ws_1.write(2+i,5,   "1958 1978")
        ws_1.write(2+i,6,   "1979 1994")
    
    ws_1.write_merge(0,0,1,6,   "benchmark")
    ws_1.write_merge(9,9,1,6,   "retrofit")
    ws_1.write_merge(18,18,1,6, "advanced retrofit")
    
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
                        
                yr_av_Q_Ht          = yr_av_Q_Ht_count/8760
                yr_av_vent_loss     = yr_av_vent_loss_count/8760
                yr_av_vent_inf      = yr_av_vent_inf_count/8760
                yr_av_n_total       = yr_av_n_total_count/8760
                portion_vent        = yr_av_vent_loss/(yr_av_vent_loss+yr_av_Q_Ht)
                portion_inf         = yr_av_vent_inf/yr_av_vent_loss
                area_spec_heat_loss = (yr_av_Q_Ht_count + yr_av_vent_loss_count)/(apartment_quantity*apartment_size)/1000
                area_spec_vent_loss = yr_av_vent_loss_count/(apartment_quantity*apartment_size)/1000
                
                ws.write(8, 27, yr_av_Q_Ht)
                ws.write(18,27, yr_av_vent_loss)
                ws.write(28,27, yr_av_vent_inf)
                ws.write(38,27, yr_av_n_total)
                ws.write(18,28, portion_vent)
                ws.write(28,28, portion_inf)
                
                if building_type == "ClusterA":
                    if options_scenario == "benchmark":
                        if building_age == "0 1957":
                            ws_1.write(3,1, portion_vent) 
                            ws_1.write(4,1, portion_inf)
                            ws_1.write(5,1, yr_av_n_total)
                            ws_1.write(6,1, area_spec_heat_loss)
                            ws_1.write(7,1, area_spec_vent_loss)
                        elif building_age == "1958 1978":
                            ws_1.write(3,2, portion_vent)
                            ws_1.write(4,2, portion_inf)
                            ws_1.write(5,2, yr_av_n_total)
                            ws_1.write(6,2, area_spec_heat_loss)
                            ws_1.write(7,2, area_spec_vent_loss)
                        elif building_age == "1979 1994":
                            ws_1.write(3,3, portion_vent) 
                            ws_1.write(4,3, portion_inf)
                            ws_1.write(5,3, yr_av_n_total)
                            ws_1.write(6,3, area_spec_heat_loss)
                            ws_1.write(7,3, area_spec_vent_loss)
                    elif options_scenario == "s1":
                        if building_age == "0 1957":
                            ws_1.write(12,1, portion_vent) 
                            ws_1.write(13,1, portion_inf)
                            ws_1.write(14,1, yr_av_n_total)
                            ws_1.write(15,1, area_spec_heat_loss)
                            ws_1.write(16,1, area_spec_vent_loss)
                        elif building_age == "1958 1978":
                            ws_1.write(12,2, portion_vent) 
                            ws_1.write(13,2, portion_inf)
                            ws_1.write(14,2, yr_av_n_total)
                            ws_1.write(15,2, area_spec_heat_loss)
                            ws_1.write(16,2, area_spec_vent_loss)
                        elif building_age == "1979 1994":
                            ws_1.write(12,3, portion_vent) 
                            ws_1.write(13,3, portion_inf)
                            ws_1.write(14,3, yr_av_n_total)
                            ws_1.write(15,3, area_spec_heat_loss)
                            ws_1.write(16,3, area_spec_vent_loss)
                    elif options_scenario == "s2":
                        if building_age == "0 1957":
                            ws_1.write(21,1, portion_vent) 
                            ws_1.write(22,1, portion_inf)
                            ws_1.write(23,1, yr_av_n_total)
                            ws_1.write(24,1, area_spec_heat_loss)
                            ws_1.write(25,1, area_spec_vent_loss)
                        elif building_age == "1958 1978":
                            ws_1.write(21,2, portion_vent) 
                            ws_1.write(22,2, portion_inf)
                            ws_1.write(23,2, yr_av_n_total)
                            ws_1.write(24,2, area_spec_heat_loss)
                            ws_1.write(25,2, area_spec_vent_loss)
                        elif building_age == "1979 1994":
                            ws_1.write(21,3, portion_vent) 
                            ws_1.write(22,3, portion_inf)
                            ws_1.write(23,3, yr_av_n_total)
                            ws_1.write(24,3, area_spec_heat_loss)
                            ws_1.write(25,3, area_spec_vent_loss)
                elif building_type == "ClusterB":
                    if options_scenario == "benchmark":
                        if building_age == "0 1957":
                            ws_1.write(3,4, portion_vent) 
                            ws_1.write(4,4, portion_inf)
                            ws_1.write(5,4, yr_av_n_total)
                            ws_1.write(6,4, area_spec_heat_loss)
                            ws_1.write(7,4, area_spec_vent_loss)
                        elif building_age == "1958 1978":
                            ws_1.write(3,5, portion_vent) 
                            ws_1.write(4,5, portion_inf)
                            ws_1.write(5,5, yr_av_n_total)
                            ws_1.write(6,5, area_spec_heat_loss)
                            ws_1.write(7,5, area_spec_vent_loss)
                        elif building_age == "1979 1994":
                            ws_1.write(3,6, portion_vent)
                            ws_1.write(4,6, portion_inf)
                            ws_1.write(5,6, yr_av_n_total)
                            ws_1.write(6,6, area_spec_heat_loss)
                            ws_1.write(7,6, area_spec_vent_loss)
                    elif options_scenario == "s1":
                        if building_age == "0 1957":
                            ws_1.write(12,4, portion_vent) 
                            ws_1.write(13,4, portion_inf)
                            ws_1.write(14,4, yr_av_n_total)
                            ws_1.write(15,4, area_spec_heat_loss)
                            ws_1.write(16,4, area_spec_vent_loss)
                        elif building_age == "1958 1978":
                            ws_1.write(12,5, portion_vent) 
                            ws_1.write(13,5, portion_inf)
                            ws_1.write(14,5, yr_av_n_total)
                            ws_1.write(15,5, area_spec_heat_loss)
                            ws_1.write(16,5, area_spec_vent_loss)
                        elif building_age == "1979 1994":
                            ws_1.write(12,6, portion_vent) 
                            ws_1.write(13,6, portion_inf)
                            ws_1.write(14,6, yr_av_n_total)
                            ws_1.write(15,6, area_spec_heat_loss)
                            ws_1.write(16,6, area_spec_vent_loss)
                    elif options_scenario == "s2":
                        if building_age == "0 1957":
                            ws_1.write(21,4, portion_vent) 
                            ws_1.write(22,4, portion_inf)
                            ws_1.write(23,4, yr_av_n_total)
                            ws_1.write(24,4, area_spec_heat_loss)
                            ws_1.write(25,4, area_spec_vent_loss)
                        elif building_age == "1958 1978":
                            ws_1.write(21,5, portion_vent) 
                            ws_1.write(22,5, portion_inf)
                            ws_1.write(23,5, yr_av_n_total)
                            ws_1.write(24,5, area_spec_heat_loss)
                            ws_1.write(25,5, area_spec_vent_loss)
                        elif building_age == "1979 1994":
                            ws_1.write(21,6, portion_vent) 
                            ws_1.write(22,6, portion_inf)
                            ws_1.write(23,6, yr_av_n_total)
                            ws_1.write(24,6, area_spec_heat_loss)
                            ws_1.write(25,6, area_spec_vent_loss)
                
                
    wb.save("results/vent_changedNuebersicht.xls")
                
multiple_run()
                
                