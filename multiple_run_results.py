# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 21:40:50 2019

@author: jonas

function to generate results into an excel sheet to have a better overview

"""

import run_basic as run
import numpy as np
from xlwt import Workbook

def overview_results():
    
    scenarios           = ["benchmark"]#, "free"]#, "all_hp_geo", "all_hp_air", "all_chp"] # "free_o_vent", "all_chp_pv"
    opt_cost            = [1]
    opt_location        = ["Essen"]#, "Hamburg", "Fichtelberg"]
    useable_roofarea    = 0.25
    electricity_demand  = "medium"
    dhw_demand          = "medium"
    household_size      = 3
    
    for key in scenarios:
        
        name_wb         = "wb_" + key 
        name_wb         = Workbook()
        
        name_sheet      = "ws_ov_" + key
        name_sheet      = name_wb.add_sheet("Übersicht", cell_overwrite_ok=True)
        ws_vent = name_wb.add_sheet("Lüftung", cell_overwrite_ok=True)
        ws_cost = name_wb.add_sheet("KostenEmission", cell_overwrite_ok=True)
        
        for loc in range(len(opt_location)):
            for cost in range(len(opt_cost)):
                
                if cost == 0:
                    name_cost   = "Kosten"
                    bi_cost     = True  
                else:
                    name_cost = "Emission"
                    bi_cost     = False
            
                name_sheet.write_merge(0+loc*26,0+loc*26,0+cost*15,1+cost*15,               "Optimierung")
                ws_vent.write(0+loc*11,0+cost*8,                                            "Optimierung")
                ws_cost.write_merge(0+loc*41,0+loc*41,0+cost*9,1+cost*9,                    "Optimierung")
                
                name_sheet.write_merge(1+loc*26,1+loc*26,0+cost*15,1+cost*15,               "Standort")
                ws_vent.write(1+loc*11,0+cost*8,                                            "Standort")
                ws_cost.write_merge(1+loc*41,1+loc*41,0+cost*9,1+cost*9,                    "Standort")
                
                name_sheet.write_merge(2+loc*26,2+loc*26,0+cost*15,1+cost*15,               "Szenario")
                ws_vent.write(2+loc*11,0+cost*8,                                            "Szenario")
                ws_cost.write_merge(2+loc*41,2+loc*41,0+cost*9,1+cost*9,                    "Szenario")
                
                name_sheet.write_merge(3+loc*26,3+loc*26,0+cost*15,1+cost*15,               "Gebäudetyp")
                ws_vent.write(3+loc*11,0+cost*8,                                            "Gebäudetyp")
                ws_cost.write_merge(3+loc*41,3+loc*41,0+cost*9,1+cost*9,                    "Gebäudetyp")
                
                name_sheet.write_merge(4+loc*26,4+loc*26,0+cost*15,1+cost*15,               "Baujahr")
                ws_vent.write(4+loc*11,0+cost*8,                                            "Baujahr")
                ws_cost.write_merge(4+loc*41,4+loc*41,0+cost*9,1+cost*9,                    "Baujahr")
                
                name_sheet.write_merge(0+loc*26,0+loc*26,2+cost*15,13+cost*15,              name_cost)
                ws_vent.write_merge(0+loc*11,0+loc*11,1+cost*8,6+cost*8,                    name_cost)
                ws_cost.write_merge(0+loc*41,0+loc*41,2+cost*9,7+cost*9,                    name_cost)
                
                name_sheet.write_merge(1+loc*26,1+loc*26,2+cost*15,13+cost*15,              opt_location[loc])
                ws_vent.write_merge(1+loc*11,1+loc*11,1+cost*8,6+cost*8,                    opt_location[loc])
                ws_cost.write_merge(1+loc*41,1+loc*41,2+cost*9,7+cost*9,                    opt_location[loc])
                
                name_sheet.write_merge(2+loc*26,2+loc*26,2+cost*15,13+cost*15,              key)
                ws_vent.write_merge(2+loc*11,2+loc*11,1+cost*8,6+cost*8,                    key)
                ws_cost.write_merge(2+loc*41,2+loc*41,2+cost*9,7+cost*9,                    key)
                
                name_sheet.write_merge(3+loc*26,3+loc*26,2+cost*15,7+cost*15,               "SFH")
                name_sheet.write_merge(3+loc*26,3+loc*26,8+cost*15,13+cost*15,              "MFH")
                ws_vent.write_merge(3+loc*11,3+loc*11,1+cost*8,3+cost*8,                    "SFH")
                ws_vent.write_merge(3+loc*11,3+loc*11,4+cost*8,6+cost*8,                    "MFH")
                ws_cost.write_merge(3+loc*41,3+loc*41,2+cost*9,4+cost*9,                    "SFH")
                ws_cost.write_merge(3+loc*41,3+loc*41,5+cost*9,7+cost*9,                    "MFH")
                
                name_sheet.write_merge(4+loc*26,4+loc*26,2+cost*15,3+cost*15,               "0 1957")
                name_sheet.write_merge(4+loc*26,4+loc*26,4+cost*15,5+cost*15,               "1958 1978")
                name_sheet.write_merge(4+loc*26,4+loc*26,6+cost*15,7+cost*15,               "1979 1994")
                name_sheet.write_merge(4+loc*26,4+loc*26,8+cost*15,9+cost*15,               "0 1957")
                name_sheet.write_merge(4+loc*26,4+loc*26,10+cost*15,11+cost*15,             "1958 1978")
                name_sheet.write_merge(4+loc*26,4+loc*26,12+cost*15,13+cost*15,             "1979 1994")
                ws_vent.write(4+loc*11,1+cost*8,                                            "0 1957")
                ws_vent.write(4+loc*11,2+cost*8,                                            "1958 1978")
                ws_vent.write(4+loc*11,3+cost*8,                                            "1979 1994")
                ws_vent.write(4+loc*11,4+cost*8,                                            "0 1957")
                ws_vent.write(4+loc*11,5+cost*8,                                            "1958 1978")
                ws_vent.write(4+loc*11,6+cost*8,                                            "1979 1994")
                ws_cost.write(4+loc*41,2+cost*9,                                            "0 1957")
                ws_cost.write(4+loc*41,3+cost*9,                                            "1958 1978")
                ws_cost.write(4+loc*41,4+cost*9,                                            "1979 1994")
                ws_cost.write(4+loc*41,5+cost*9,                                            "0 1957")
                ws_cost.write(4+loc*41,6+cost*9,                                            "1958 1978")
                ws_cost.write(4+loc*41,7+cost*9,                                            "1979 1994")
                
                name_sheet.write_merge(6+loc*26,16+loc*26,0+cost*15,0+cost*15,              "Anlagen-technik")
                name_sheet.write(6+loc*26,1+cost*15,                                        "Batterie")
                name_sheet.write(7+loc*26,1+cost*15,                                        "Kessel")
                name_sheet.write(8+loc*26,1+cost*15,                                        "BHKW")
                name_sheet.write(9+loc*26,1+cost*15,                                        "Luft-WP")
                name_sheet.write(10+loc*26,1+cost*15,                                       "Sole-WP")
                name_sheet.write(11+loc*26,1+cost*15,                                       "Pellet-Kessel")
                name_sheet.write(12+loc*26,1+cost*15,                                       "PV")
                name_sheet.write(13+loc*26,1+cost*15,                                       "Solarthermie")
                name_sheet.write(14+loc*26,1+cost*15,                                       "Therm ES")
                name_sheet.write(15+loc*26,1+cost*15,                                       "Elektroheizstab")
                name_sheet.write(16+loc*26,1+cost*15,                                       "Lüftungsgerät")
                
                name_sheet.write_merge(17+loc*26,20+loc*26,0+cost*15,0+cost*15,             "Sanierungs-maßnahme")
                name_sheet.write(17+loc*26,1+cost*15,                                       "Boden")
                name_sheet.write(18+loc*26,1+cost*15,                                       "Dach")
                name_sheet.write(19+loc*26,1+cost*15,                                       "Fenster")
                name_sheet.write(20+loc*26,1+cost*15,                                       "Wand")
                
                name_sheet.write_merge(22+loc*26,23+loc*26,0+cost*15,0+cost*15,             "Ergebnis")
                name_sheet.write(22+loc*26,1+cost*15,                                       "C_ges")
                name_sheet.write(23+loc*26,1+cost*15,                                       "E_ges")
                
                ws_vent.write(5+loc*11,0+cost*8,                                            "Anteil Lüftung- an Gesamtwärmeverlusten")
                ws_vent.write(6+loc*11,0+cost*8,                                            "Anteil Infiltrations- an Lüftungswärmeverlusten")
                ws_vent.write(7+loc*11,0+cost*8,                                            "Jährlich gemittelte Lüftwechselrate [h^(-1)]")
                ws_vent.write(8+loc*11,0+cost*8,                                            "Flächenspezifische Gesamtwärmeverluste [W/m²]")
                ws_vent.write(9+loc*11,0+cost*8,                                            "Flächenspezifische Lüftungswärmeverluste [W/m²]")
                
                ws_cost.write_merge(5+loc*41,19+loc*41,0+cost*9,0+cost*9,                   "Investitions-kosten")
                ws_cost.write_merge(21+loc*41,22+loc*41,0+cost*9,0+cost*9,                  "Fixkosten")
                ws_cost.write_merge(24+loc*41,28+loc*41,0+cost*9,0+cost*9,                  "Bedarfs-kosten")
                ws_cost.write_merge(30+loc*41,39+loc*41,0+cost*9,0+cost*9,                  "Wartung- und Instandhaltungs-kosten")
                
                ws_cost.write(5+loc*41,1+cost*9,                                            "Sanierung: Boden")
                ws_cost.write(6+loc*41,1+cost*9,                                            "Sanierung: Dach")
                ws_cost.write(7+loc*41,1+cost*9,                                            "Sanierung: Fenster")
                ws_cost.write(8+loc*41,1+cost*9,                                            "Sanierung: Wand")
                ws_cost.write(9+loc*41,1+cost*9,                                            "Batterie")
                ws_cost.write(10+loc*41,1+cost*9,                                           "Kessel")
                ws_cost.write(11+loc*41,1+cost*9,                                           "BHKW")
                ws_cost.write(12+loc*41,1+cost*9,                                           "Elektroheizstab")
                ws_cost.write(13+loc*41,1+cost*9,                                           "Luft-WP")
                ws_cost.write(14+loc*41,1+cost*9,                                           "Sole-WP")
                ws_cost.write(15+loc*41,1+cost*9,                                           "Pellet-Kessel")
                ws_cost.write(16+loc*41,1+cost*9,                                           "PV")
                ws_cost.write(17+loc*41,1+cost*9,                                           "Solarthermie")
                ws_cost.write(18+loc*41,1+cost*9,                                           "Thermischer ES")
                ws_cost.write(19+loc*41,1+cost*9,                                           "Maschinelle Lüftung")
                
                ws_cost.write(21+loc*41,1+cost*9,                                           "Elektrizität")
                ws_cost.write(22+loc*41,1+cost*9,                                           "Gas")
                
                ws_cost.write(24+loc*41,1+cost*9,                                           "Kessel")
                ws_cost.write(25+loc*41,1+cost*9,                                           "BHKW")
                ws_cost.write(26+loc*41,1+cost*9,                                           "Elektrizitätsbedarf")
                ws_cost.write(27+loc*41,1+cost*9,                                           "Elektro WP")
                ws_cost.write(28+loc*41,1+cost*9,                                           "Pellet")
                
                ws_cost.write(30+loc*41,1+cost*9,                                           "Batterie")
                ws_cost.write(31+loc*41,1+cost*9,                                           "Kessel")
                ws_cost.write(32+loc*41,1+cost*9,                                           "BHKW")
                ws_cost.write(33+loc*41,1+cost*9,                                           "Elektroheizstab")
                ws_cost.write(34+loc*41,1+cost*9,                                           "Luft-WP")
                ws_cost.write(35+loc*41,1+cost*9,                                           "Sole-WP")
                ws_cost.write(36+loc*41,1+cost*9,                                           "Pellet-Kessel")
                ws_cost.write(37+loc*41,1+cost*9,                                           "PV")
                ws_cost.write(38+loc*41,1+cost*9,                                           "Solarthermie")
                ws_cost.write(39+loc*41,1+cost*9,                                           "Thermischer ES")
                
                for i in range(6):
                    name_sheet.write(5+loc*26,2+2*i+cost*15,                                "Auswahl")
                    name_sheet.write(5+loc*26,3+2*i+cost*15,                                "Leistung")
                    
#                name_sheet.write_merge(16+loc*26,16+loc*26,2+cost*15,13+cost*15,            "Sanierungsmaßnahme")
                    
                for building_type in ["ClusterA"]:#, "ClusterB"]:
                    for building_age in ["0 1957"]:#, "1958 1978", "1979 1994"]:
                        
                        if building_type == "ClusterA":
                            apartment_quantity  = 1
                            apartment_size      = 110
                        else:
                            apartment_quantity  = 10
                            apartment_size      = 70
                            
                        location = opt_location[loc]
                        
                        options = {"opt_costs" : bi_cost,
                                   "EEG": True,
                                   "kfw_battery": True,
                                   "KWKG": True,           
                                   "Bafa_chp": True,
                                   "Bafa_hp": True,
                                   "Bafa_stc": True,
                                   "Bafa_pellet": True,
                                   "kfw_eff_buildings" : True,
                                   "kfw_single_mea" : True,         
                                   "New_Building" : False,
                                   "dhw_electric" : False,
                                   "scenario": key,
                                   "Design_heat_load" : True,
                                   "store_start_vals" : False,
                                   "load_start_vals" : False,
                                   "filename_results" : "results/" + building_type + "_" + \
                                                                       building_age + "_" + key + ".pkl",                 
                                   "filename_start_vals" :"start_values/" + building_type + "_" + \
                                                                          building_age + "_start.csv"}
                        
                        Outputs = run.building_optimization(  building_type, building_age, location, 
                                                              household_size, electricity_demand, 
                                                              dhw_demand, useable_roofarea, 
                                                              apartment_quantity, apartment_size, options)
                        
                        if building_type == "ClusterA":
                            if building_age     == "0 1957":
                                b_age           = 0
                                b_age_vent      = 0
                            elif building_age   == "1958 1978":
                                b_age           = 2
                                b_age_vent      = 1
                            elif building_age   == "1979 1994":
                                b_age           = 4
                                b_age_vent      = 2
                        else:
                            if building_age     == "0 1957":
                                b_age           = 6
                                b_age_vent      = 3
                            elif building_age   == "1958 1978":
                                b_age           = 8
                                b_age_vent      = 4
                            elif building_age   == "1979 1994":
                                b_age           = 10
                                b_age_vent      = 5
                        
                        if Outputs["5_x"]["bat"] == 1:
                            name_sheet.write(6+loc*26,2+cost*15+b_age,                                      "ja")
                            name_sheet.write(6+loc*26,3+cost*15+b_age,                                      Outputs["6_cap"]["bat"])
                        else:
                            name_sheet.write(6+loc*26,2+cost*15+b_age,                                      "nein")
                            name_sheet.write(6+loc*26,3+cost*15+b_age,                                      0)
                        if Outputs["5_x"]["boiler"] == 1:
                            name_sheet.write(7+loc*26,2+cost*15+b_age,                                      "ja")
                            name_sheet.write(7+loc*26,3+cost*15+b_age,                                      Outputs["6_cap"]["boiler"])
                        else:
                            name_sheet.write(7+loc*26,2+cost*15+b_age,                                      "nein")
                            name_sheet.write(7+loc*26,3+cost*15+b_age,                                      0)
                        if Outputs["5_x"]["chp"] == 1:
                            name_sheet.write(8+loc*26,2+cost*15+b_age,                                      "ja")
                            name_sheet.write(8+loc*26,3+cost*15+b_age,                                      Outputs["6_cap"]["chp"])
                        else:
                            name_sheet.write(8+loc*26,2+cost*15+b_age,                                      "nein")
                            name_sheet.write(8+loc*26,3+cost*15+b_age,                                      0)
                        if Outputs["5_x"]["hp_air"] == 1:
                            name_sheet.write(9+loc*26,2+cost*15+b_age,                                      "ja")
                            name_sheet.write(9+loc*26,3+cost*15+b_age,                                      Outputs["6_cap"]["hp_air"])
                        else:
                            name_sheet.write(9+loc*26,2+cost*15+b_age,                                      "nein")
                            name_sheet.write(9+loc*26,3+cost*15+b_age,                                      0)
                        if Outputs["5_x"]["hp_geo"] == 1:
                            name_sheet.write(10+loc*26,2+cost*15+b_age,                                     "ja")
                            name_sheet.write(10+loc*26,3+cost*15+b_age,                                     Outputs["6_cap"]["hp_geo"])
                        else:
                            name_sheet.write(10+loc*26,2+cost*15+b_age,                                     "nein")
                            name_sheet.write(10+loc*26,3+cost*15+b_age,                                     0)
                        if Outputs["5_x"]["pellet"] == 1:
                            name_sheet.write(11+loc*26,2+cost*15+b_age,                                     "ja")
                            name_sheet.write(11+loc*26,3+cost*15+b_age,                                     Outputs["6_cap"]["pellet"])
                        else:
                            name_sheet.write(11+loc*26,2+cost*15+b_age,                                     "nein")
                            name_sheet.write(11+loc*26,3+cost*15+b_age,                                     0)
                        if Outputs["5_x"]["pv"] == 1:
                            name_sheet.write(12+loc*26,2+cost*15+b_age,                                     "ja")
                            name_sheet.write(12+loc*26,3+cost*15+b_age,                                     Outputs["6_cap"]["pv"])
                        else:
                            name_sheet.write(12+loc*26,2+cost*15+b_age,                                     "nein")
                            name_sheet.write(12+loc*26,3+cost*15+b_age,                                     0)
                        if Outputs["5_x"]["tes"] == 1:
                            name_sheet.write(14+loc*26,2+cost*15+b_age,                                     "ja")
                            name_sheet.write(14+loc*26,3+cost*15+b_age,                                     Outputs["6_cap"]["tes"])
                        else:
                            name_sheet.write(14+loc*26,2+cost*15+b_age,                                     "nein")
                            name_sheet.write(14+loc*26,3+cost*15+b_age,                                     0)
                        if Outputs["5_x"]["eh"] == 1:
                            name_sheet.write(15+loc*26,2+cost*15+b_age,                                     "ja")
                            name_sheet.write(15+loc*26,3+cost*15+b_age,                                     Outputs["6_cap"]["eh"])
                        else:
                            name_sheet.write(15+loc*26,2+cost*15+b_age,                                     "nein")
                            name_sheet.write(15+loc*26,3+cost*15+b_age,                                     0)
                        if Outputs["5_x"]["stc"] == 1:
                            name_sheet.write(13+loc*26,2+cost*15+b_age,                                     "ja")
                            name_sheet.write(13+loc*26,3+cost*15+b_age,                                     Outputs["6_cap"]["stc"])
                        else:
                            name_sheet.write(13+loc*26,2+cost*15+b_age,                                     "nein")
                            name_sheet.write(13+loc*26,3+cost*15+b_age,                                     0)
                        if Outputs["res_x_vent"] == 1:
                            name_sheet.write(16+loc*26,2+cost*15+b_age,                                     "ja")
                        else:
                            name_sheet.write(16+loc*26,2+cost*15+b_age,                                     "nein")
                        if Outputs["7_x_restruc"][('GroundFloor', 'adv_retr')] == 1:
                            name_sheet.write_merge(17+loc*26,17+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "advanced retrofit")
                        elif Outputs["7_x_restruc"][('GroundFloor', 'retrofit')] == 1:
                            name_sheet.write_merge(17+loc*26,17+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "retrofit")
                        elif Outputs["7_x_restruc"][('GroundFloor', 'standard')] == 1:
                            name_sheet.write_merge(17+loc*26,17+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "standard")
                        if Outputs["7_x_restruc"][('Rooftop', 'adv_retr')] == 1:
                            name_sheet.write_merge(18+loc*26,18+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "advanced retrofit")
                        elif Outputs["7_x_restruc"][('Rooftop', 'retrofit')] == 1:
                            name_sheet.write_merge(18+loc*26,18+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "retrofit")
                        elif Outputs["7_x_restruc"][('Rooftop', 'standard')] == 1:
                            name_sheet.write_merge(18+loc*26,18+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "standard")
                        if Outputs["7_x_restruc"][('Window', 'adv_retr')] == 1:
                            name_sheet.write_merge(19+loc*26,19+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "advanced retrofit")
                        elif Outputs["7_x_restruc"][('Window', 'retrofit')] == 1:
                            name_sheet.write_merge(19+loc*26,19+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "retrofit")
                        elif Outputs["7_x_restruc"][('Window', 'standard')] == 1:
                            name_sheet.write_merge(19+loc*26,19+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "standard")
                        if Outputs["7_x_restruc"][('OuterWall', 'adv_retr')] == 1:
                            name_sheet.write_merge(20+loc*26,20+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "advanced retrofit")
                        elif Outputs["7_x_restruc"][('OuterWall', 'retrofit')] == 1:
                            name_sheet.write_merge(20+loc*26,20+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "retrofit")
                        elif Outputs["7_x_restruc"][('OuterWall', 'standard')] == 1:
                            name_sheet.write_merge(20+loc*26,20+loc*26,2+cost*15+b_age,3+cost*15+b_age,     "standard")
                        name_sheet.write_merge(22+loc*26,22+loc*26,2+cost*15+b_age,3+cost*15+b_age,         Outputs["3_c_total"])
                        name_sheet.write_merge(23+loc*26,23+loc*26,2+cost*15+b_age,3+cost*15+b_age,         Outputs["4_emission"])
                        
                        yr_av_Q_Ht_count      = 0
                        yr_av_vent_loss_count = 0
                        yr_av_vent_inf_count  = 0
                        yr_av_n_total_count   = 0
                        
                        for d in range(8):
                            for t in range(24):
                                yr_av_Q_Ht_count      += Outputs["res_heat_mod"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                                yr_av_vent_loss_count += (Outputs["res_Q_vent_loss"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]/
                                                          (1-int(Outputs["res_x_vent"])+int(Outputs["res_x_vent"])*0.6)) #0.6 as Rückwärmezahl                                                               
                                yr_av_vent_inf_count  += Outputs["res_Q_v_Inf_wirk"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                                yr_av_n_total_count   += Outputs["res_n_total"][(7, 23)][d, t]*Outputs["inputs_clustered"]["weights"][d]
                                
                        yr_av_Q_Ht          = yr_av_Q_Ht_count
                        yr_av_vent_loss     = yr_av_vent_loss_count
                        yr_av_vent_inf      = yr_av_vent_inf_count
                        yr_av_n_total       = yr_av_n_total_count/8760
                        portion_vent        = yr_av_vent_loss/yr_av_Q_Ht
                        portion_inf         = yr_av_vent_inf/yr_av_vent_loss
                        area_spec_heat_loss = yr_av_Q_Ht/(apartment_quantity*apartment_size)
                        area_spec_vent_loss = yr_av_vent_loss_count/(apartment_quantity*apartment_size)
                        
                        ws_vent.write(5+loc*11,1+cost*8+b_age_vent,                                            portion_vent)
                        ws_vent.write(6+loc*11,1+cost*8+b_age_vent,                                            portion_inf)
                        ws_vent.write(7+loc*11,1+cost*8+b_age_vent,                                            yr_av_n_total)
                        ws_vent.write(8+loc*11,1+cost*8+b_age_vent,                                            area_spec_heat_loss)
                        ws_vent.write(9+loc*11,1+cost*8+b_age_vent,                                            area_spec_vent_loss)
                        
                        ws_cost.write(5+loc*41,2+cost*9+b_age_vent,                                            Outputs["res_c_inv"]["GroundFloor"])
                        ws_cost.write(6+loc*41,2+cost*9+b_age_vent,                                            Outputs["res_c_inv"]["Rooftop"])
                        ws_cost.write(7+loc*41,2+cost*9+b_age_vent,                                            Outputs["res_c_inv"]["Window"])
                        ws_cost.write(8+loc*41,2+cost*9+b_age_vent,                                            Outputs["res_c_inv"]["OuterWall"])
                        ws_cost.write(9+loc*41,2+cost*9+b_age_vent,                                            Outputs["res_c_inv"]["bat"])
                        ws_cost.write(10+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["boiler"])
                        ws_cost.write(11+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["chp"])
                        ws_cost.write(12+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["eh"])
                        ws_cost.write(13+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["hp_air"])
                        ws_cost.write(14+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["hp_geo"])
                        ws_cost.write(15+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["pellet"])
                        ws_cost.write(16+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["pv"])
                        ws_cost.write(17+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["stc"])
                        ws_cost.write(18+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["tes"])
                        ws_cost.write(19+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_inv"]["vent"])
                        
                        ws_cost.write(21+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_fix"]["el"])
                        ws_cost.write(22+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_fix"]["gas"])
                        
                        ws_cost.write(24+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_dem"]["boiler"])
                        ws_cost.write(25+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_dem"]["chp"])
                        ws_cost.write(26+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_dem"]["grid_house"])
                        ws_cost.write(27+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_dem"]["grid_hp"])
                        ws_cost.write(28+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_dem"]["pellet"])
                        
                        ws_cost.write(30+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["bat"])
                        ws_cost.write(31+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["boiler"])
                        ws_cost.write(32+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["chp"])
                        ws_cost.write(33+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["eh"])
                        ws_cost.write(34+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["hp_air"])
                        ws_cost.write(35+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["hp_geo"])
                        ws_cost.write(36+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["pellet"])
                        ws_cost.write(37+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["pv"])
                        ws_cost.write(38+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["stc"])
                        ws_cost.write(39+loc*41,2+cost*9+b_age_vent,                                           Outputs["res_c_om"]["tes"])
                        
                        
                        
                        
        name_wb.save("results/ergebnisse_" + key + ".xls")

            
overview_results()
        
        
        
        
        
    
    
    

