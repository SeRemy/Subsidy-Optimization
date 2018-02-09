# -*- coding: utf-8 -*-
"""
Created on Thu Feb 16 14:08:55 2017
@author: jte-sre
"""
import pickle 

def read_results(name):
    results = {}
    
    with open("results/inputs_" + name + ".pkl", "rb") as f_in:
        results["input_economics"] = pickle.load(f_in)
        results["input_devices"] = pickle.load(f_in)
        results["inputs_clustered"] = pickle.load(f_in)
        results["inputs_params"] = pickle.load(f_in)
        results["inputs_building"] = pickle.load(f_in)
        results["inputs_subsidies"] = pickle.load(f_in)
        results["inputs_ref_building"] = pickle.load(f_in)
    
    with open ("results/"+ name + '.pkl', "rb") as fin:
        results["5_x"] = pickle.load(fin) 
        results["res_y"] = pickle.load(fin)
        results["res_x_tariff"] = pickle.load(fin)
        results["res_x_gas"] = pickle.load(fin)
        results["res_x_el"] = pickle.load(fin)
        results["res_power"] = pickle.load(fin)
        results["res_heat"] = pickle.load(fin)
        results["res_energy"] = pickle.load(fin)
        results["res_p_grid"] = pickle.load(fin)
        results["res_G"] = pickle.load(fin)
        results["res_G_total"] = pickle.load(fin)
        results["res_El"] = pickle.load(fin)
        results["res_El_total"] = pickle.load(fin)
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
    
    return results