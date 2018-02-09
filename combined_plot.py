# -*- coding: utf-8 -*-
"""
Created on Mon Feb  5 14:10:26 2018

@author: srm
"""
import pickle

def read_results(name):
    
    liste1 = []
    liste2 = []

    for i in range(0,10):

        results ={}
        path = name + str(i)
        
        with open ("results/"+ path + '.pkl', "rb") as fin:
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
            
        liste1.append(results["3_c_total"])
        liste2.append(results["4_emission"])
        
    return (liste1,liste2)

(costs1,emi1) = read_results(name = "OhneSub/free_")
emi1.sort(reverse = True)
costs1.sort()

(costs2,emi2) = read_results(name = "MitSub/free_")
emi2.sort(reverse = True)
costs2.sort()
#    
import matplotlib.pyplot as plt
plt.rcParams['savefig.facecolor'] = "0.8"


def example_plot(ax, fontsize=12):
#    ax.plot(emi_list,cost_list)
#    ax.plot(emi_list1,cost_list1)
    ax.plot(emi1,costs1, color = "blue")
    ax.plot(emi2,costs2,"green")
            
#    emi_list.sort(reverse = True)
#    cost_list.sort()

    
#    ax.legend(("Ohne Förderung", "Mit Förderung"), fontsize=fontsize )
    
    ax.locator_params(nbins=7)
    ax.axvline(x=0, color = "black")
#    ax.set_xlabel('CO2-Emissionen in t/a', fontsize=fontsize)
#    ax.set_ylabel('Jährliche Kosten in €/a', fontsize=fontsize)
#    ax.set_title('CO2-Vermeidungskosten', fontsize=fontsize)

plt.close('all')
fig, ax = plt.subplots()
example_plot(ax, fontsize=18)