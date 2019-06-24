# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:46:11 2019

@author: srm-jba
"""
import pickle 
import python.read_basic as reader
import pandas as pd
from xlwt import Workbook

def pick_read(filename):
    
    results={}
    
    with open("results/"+filename+".pkl", "rb") as fin:
        results["5_x"] = pickle.load(fin) 
        results["res_y"] = pickle.load(fin)
        results["res_power"] = pickle.load(fin)
        results["res_heat"] = pickle.load(fin)
        results["res_energy"] = pickle.load(fin)
        results["res_p_grid"] = pickle.load(fin)
        results["res_soc"] = pickle.load(fin)
        results["res_soc_init"] = pickle.load(fin)
        results["res_ch"] = pickle.load(fin)
        results["res_dch"] = pickle.load(fin)
        results["res_p_use"] = pickle.load(fin)
        results["res_p_sell"] = pickle.load(fin)
        results["res_p_hp"] = pickle.load(fin)
        results["res_c_inv"] = pickle.load(fin)
        results["res_c_om"] = pickle.load(fin)
        results["res_c_dem"] = pickle.load(fin)
        results["res_c_fix"] = pickle.load(fin)
        results["3_c_total"] = pickle.load(fin)
        results["res_rev"] = pickle.load(fin)
        results["res_sub"] = pickle.load(fin)
        results["4_emission"] = pickle.load(fin)
        results["ObjVal"] = pickle.load(fin)
        results["2_Runtime"] = pickle.load(fin)
        results["1_MIPGap"] = pickle.load(fin)
        results["res_soc_nom"] = pickle.load(fin)
        results["res_power_nom"] = pickle.load(fin)
        results["res_heat_nom"] = pickle.load(fin)
        results["6_cap"] = pickle.load(fin)
        results["res_heat_mod"] = pickle.load(fin)
        results["res_b_sub_restruc"] = pickle.load(fin)
        results["7_x_restruc"] = pickle.load(fin)
        results["res_Ht"] = pickle.load(fin)
        results["res_Qs"] = pickle.load(fin)
        results["res_Q_p_DIN"] = pickle.load(fin)
        results["res_heating_concept"] = pickle.load(fin)
        results["res_lin_HT"] = pickle.load(fin)
        results["res_sub_chp"] = pickle.load(fin)
        results["res_b_pv_power"] = pickle.load(fin)
        results["res_lin_pv_power"] = pickle.load(fin)    
        results["res_p_chp_total"] = pickle.load(fin)
        results["res_lin_kwkg_2"] = pickle.load(fin)
        results["res_lin_kwkg_1"] = pickle.load(fin)    
        results["res_b_kwkg"] = pickle.load(fin)   
        results["res_sub_kwkg_temp"] = pickle.load(fin)
        results["res_Q_vent_loss"] = pickle.load(fin)
        results["res_n_total"] = pickle.load(fin)
        results["res_Q_v_Inf_wirk"] = pickle.load(fin)
        results["res_Q_Ht"] = pickle.load(fin)
        results["res_x_vent"] = pickle.load(fin)
        results["res_n_50"] = pickle.load(fin)
        
        return results

def write_results(emi, cost):
    
    wb = Workbook()
    ws = wb.add_sheet("Übersicht", cell_overwrite_ok=True)
    
    ws.write(0,0,"Nummer")
    ws.write(1,0,"Kosten")
    ws.write(2,0,"Emissionen")
    ws.write(3,0,"Batterie")
    ws.write(4,0,"Kessel")
    ws.write(5,0,"BHKW")
    ws.write(6,0,"EHS")
    ws.write(7,0,"Luft-WP")
    ws.write(8,0,"Sole-WP")
    ws.write(9,0,"Pellet")
    ws.write(10,0,"PV")
    ws.write(11,0,"STC")
    ws.write(12,0,"TES")
    ws.write(13,0,"Vent")
    ws.write(14,0,"Boden")
    ws.write(15,0,"Dach")
    ws.write(16,0,"Fenster")
    ws.write(17,0,"Wand")
    
    
    for i in range(len(emi.keys())):
        filename = "free_" + str(i)
        Outputs=pick_read(filename)
        
        opti_cost = round(Outputs["3_c_total"],2)
        opti_emi = round(Outputs["4_emission"],2)
        
        ws.write(0,1+i,str(i))
        ws.write(1,1+i,opti_cost)
        ws.write(2,1+i,opti_emi)        
        if Outputs["5_x"]["bat"] == 1:
            ws.write(3,1+i, "ja")
        else:
            ws.write(3,1+i, "nein")
        if Outputs["5_x"]["boiler"] == 1:
            ws.write(4,1+i, "ja")
        else:
            ws.write(4,1+i, "nein")
        if Outputs["5_x"]["chp"] == 1:
            ws.write(5,1+i, "ja")
        else:
            ws.write(5,1+i, "nein")
        if Outputs["5_x"]["eh"] == 1:
            ws.write(6,1+i, "ja")
        else:
            ws.write(6,1+i, "nein")
        if Outputs["5_x"]["hp_air"] == 1:
            ws.write(7,1+i, "ja")
        else:
            ws.write(7,1+i, "nein")
        if Outputs["5_x"]["hp_geo"] == 1:
            ws.write(8,1+i, "ja")
        else:
            ws.write(8,1+i, "nein")
        if Outputs["5_x"]["pellet"] == 1:
            ws.write(9,1+i, "ja")
        else:
            ws.write(9,1+i, "nein")
        if Outputs["5_x"]["pv"] == 1:
            ws.write(10,1+i, "ja")
        else:
            ws.write(10,1+i, "nein")
        if Outputs["5_x"]["stc"] == 1:
            ws.write(11,1+i, "ja")
        else:
            ws.write(11,1+i, "nein")
        if Outputs["5_x"]["tes"] == 1:
            ws.write(12,1+i, "ja")
        else:
            ws.write(12,1+i, "nein")
        if Outputs["res_x_vent"] == 1:
            ws.write(13,1+i, "ja")
        else:
            ws.write(13,1+i, "nein")
            
        if Outputs["7_x_restruc"][('GroundFloor', 'adv_retr')] == 1:
            ws.write(14,1+i, "adv_retr")
        elif Outputs["7_x_restruc"][('GroundFloor', 'retrofit')] == 1:
            ws.write(14,1+i, "retro")
        elif Outputs["7_x_restruc"][('GroundFloor', 'standard')] == 1:
            ws.write(14,1+i, "stand")
            
        if Outputs["7_x_restruc"][('Rooftop', 'adv_retr')] == 1:
            ws.write(15,1+i, "adv_retr")
        elif Outputs["7_x_restruc"][('Rooftop', 'retrofit')] == 1:
            ws.write(15,1+i, "retro")
        elif Outputs["7_x_restruc"][('Rooftop', 'standard')] == 1:
            ws.write(15,1+i, "stand")
            
        if Outputs["7_x_restruc"][('Window', 'adv_retr')] == 1:
            ws.write(16,1+i, "adv_retr")
        elif Outputs["7_x_restruc"][('Window', 'retrofit')] == 1:
            ws.write(16,1+i, "retro")
        elif Outputs["7_x_restruc"][('Window', 'standard')] == 1:
            ws.write(16,1+i, "stand")
            
        if Outputs["7_x_restruc"][('OuterWall', 'adv_retr')] == 1:
            ws.write(17,1+i, "adv_retr")
        elif Outputs["7_x_restruc"][('OuterWall', 'retrofit')] == 1:
            ws.write(17,1+i, "retro")
        elif Outputs["7_x_restruc"][('OuterWall', 'standard')] == 1:
            ws.write(17,1+i, "stand")
    
    wb.save("results/ergebnisse_pareto.xls")

    
