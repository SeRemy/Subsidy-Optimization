#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 01 10:35:56 2015
@author: tsz
"""
from __future__ import division
import gurobipy as gp
import numpy as np
import pickle

#%%

def compute(eco, devs, clustered, params, options, building, ref_building, 
            shell_eco, sub_par, ep_table, max_emi, max_cost):
    """
    Compute the optimal building energy system consisting of pre-defined 
    devices (devs) for a given building. Furthermore the program can choose
    between different restructuring measures.(clustered) under given economic and 
    other parameters (eco and params).
    
    Parameters
    ----------
    eco : dictionary
        - b : 
        - crf : capital recovery factor
        - prChange : price changes
        - q : 
        - rate : interest rate
        - sub_CHP : subsidies for electricity from CHP units
        - t_calc : calculation time
        - tax : value added tax
        - gas, Boiler : gas costs for boilers
        - gas, CHP : gas costs for CHP units
        - pr, el : electricity price
        - sell, CHP : feed-in remuneration for CHP units
        - sell, PV : feed-in remuneration for PV units
    devs : dictionary
        - bat : Batteries
        - boiler : Boilers
        - chp : CHP units
        - eh : Electrical heaters
        - hp_air : air heat pump
        - hp_geo: geothermal heat pump
        - pel: Pellet boiler
        - pv : Photovoltaic cells
        - stc : Solar thermal collectors
        - tes : Thermal energy storage systems
    clustered : dictionary
        - design_heat_load : Building's design heat load based on DIN EN 12831
        - electricity : Electricity load profile
        - heat : Heat demand profile
        - solar_irrad : Solar irradiation on PV or STC cells
        - temperature : Outside temperature
        - weights : Weight factors from the clustering algorithm
    params : dictionary
        - dt : time step length (h)
        - maximum roof area (m2)
        - mip_gap : Solver setting (-)
        - time_limit : Solver setting (s)
        - days : 
        - time_steps : 
    """
    
    # Extract parameters
    dt = params["dt"]
    
    # Define subsets
    heater  = ["boiler", "chp", "eh", "hp_air", "hp_geo","pellet"]
    storage = ["bat", "tes"]
    solar   = ["pv", "stc"]
    subsidy_devs = ["chp", "bat", "hp_air", "hp_geo", "stc", "pellet", "pv"]
    
    building_components = ["Window","OuterWall","GroundFloor","Rooftop"]
    restruc_scenarios   = ["standard", "retrofit", "adv_retr"]
    kfw_standards       = ["kfw_eff_55","kfw_eff_70","kfw_eff_85",
                           "kfw_eff_100","kfw_eff_115"]
    
    time_steps = range(params["time_steps"])
    days       = range(params["days"])
    
    # Maximal for solar collectors and pv useable Rooftoparea
    A_max = 0.4 * building["dimensions"]["Area"] * building["dimensions"]["Rooftop"]
    
    try:
        model = gp.Model("Design computation")
        
#%% Define variables
        
        # Costs: There are cost-variables for investment, operation & maintenance,
        # demand costs (fuel costs) and fix costs for electricity and gas tariffs

        c_inv  = {dev: model.addVar(vtype="C", name="c_inv_"+dev)
                 for dev in (list(devs.keys()) + list(building_components))}
                     
        c_om   = {dev: model.addVar(vtype="C", name="c_om_"+dev)
                 for dev in list(devs.keys())}
                     
        c_dem  = {dev: model.addVar(vtype="C", name="c_dem_"+dev)
                 for dev in ("boiler", "chp", "pellet", "grid_hou", "grid_hp")}   
                 
        c_fix  = {dev: model.addVar(vtype="C", name="c_fix_"+dev)
                 for dev in ("el", "gas")}    
        
        # Revenues and Subsidies                
        revenue = {dev: model.addVar(vtype="C", name="revenue_"+dev)
                  for dev in ("chp", "pv")} 
                     
        subsidy = {dev: model.addVar(vtype="C", name="subsidy_"+dev)
                   for dev in (subsidy_devs + building_components + kfw_standards)}  
        
        # Different subsidy possiblities for chps          
        sub     = {dev: model.addVar(vtype="C", name="sub_"+dev)
                   for dev in ("micro_lump", "micro_var", "micro", "large", "bafa")} 
                                      
        # Purchase and activation decision variables        
        x = {}  # Purchase (all devices)         
        for dev in devs.keys():
            x[dev] = model.addVar(vtype="B", name="x_"+dev)
        
        y = {}  # Acitivation (heaters)   
        for d in days:
            for t in time_steps:
                timetag = "_"+str(d)+"_"+str(t)
                for dev in heater: # All heating devices
                    y[dev,d,t] = model.addVar(vtype="B", name="y_"+dev+"_"+timetag)    
        
        # Capacities of all available technologies (thermal output, area, volume,...)
        capacity = {}
        for dev in devs.keys():
            capacity[dev] = model.addVar(vtype="C", name="Capacity_"+dev , lb = 0) 
       
        # Volume of thermal storage
        volume = model.addVar(vtype="C", name="Volume", lb = 0)
        
        # PV and STC areas
        area = {}
        for dev in solar:
            area[dev] = model.addVar(vtype="C", name="Area_"+dev)        
        
        # state of charge (SOC), power, heat and energy
        soc = {}
        power = {}
        heat = {}
        energy = {}
        soc_nom = {}
        power_nom = {}
        heat_nom = {}
        for d in days: # All days
            for t in time_steps: # All time steps of all days
                timetag = "_"+str(d)+"_"+str(t)
                for dev in storage: # All storage devices
                    soc[dev,d,t] = model.addVar(vtype="C", name="SOC_"+dev+"_"+timetag, lb = 0)                
                
                for dev in (heater + solar):
                    power[dev,d,t] = model.addVar(vtype="C", name="P_"+dev+"_"+timetag)                    
                    heat[dev,d,t] = model.addVar(vtype="C", name="Q_"+dev+"_"+timetag)
                
                for dev in heater:
                    energy[dev,d,t] = model.addVar(vtype="C", name="E_"+dev+"_"+timetag)       
                    
                for dev in heater:
                    heat_nom[dev,d,t] = model.addVar(vtype="C", name="Q_nom_"+dev+"_"+timetag)
                
                for dev in ("hp_air", "hp_geo"):
                    power_nom[dev,d,t] = model.addVar(vtype="C", name="P_nom_"+dev+"_"+timetag)        
        
        for dev in storage:
            soc_nom[dev] = model.addVar(vtype="C", name="SOC_nom_"+dev)

        # Storage initial SOC's
        soc_init = {}
        for dev in storage:
            for d in days:
                tag = dev + "_" + str(d)
                soc_init[dev,d] = model.addVar(vtype="C", name="SOC_init_"+tag)

        # Storage charging and discharging
        ch = {}
        dch = {}
        for dev in storage:
            for d in days:
                for t in time_steps:
                    timetag = "_" + str(d) + "_" + str(t)
                    ch[dev,d,t] = model.addVar(vtype="C", name="ch"+dev+timetag)
                    dch[dev,d,t] = model.addVar(vtype="C", name="dch"+dev+timetag)
                    
        # Electricity imports, sold, self-used and transferred (to heat pump) electricity
        p_grid  = {}
        p_use   = {}
        p_sell  = {}
        p_hp    = {}
        for d in days:
            for t in time_steps:
                timetag = "_"+str(d)+"_"+str(t)
                
                p_grid["grid_hou",d,t] = model.addVar(vtype="C", name="p_grid_hou"+timetag)
                p_grid["grid_hp",d,t]  = model.addVar(vtype="C", name="p_grid_hp"+timetag)
                
                # Note: bat is referring to the discharge power
                for dev in ("pv", "bat","chp"):
                    p_use[dev,d,t]  = model.addVar(vtype="C", name="P_use_"+dev+timetag)
                    p_sell[dev,d,t] = model.addVar(vtype="C", name="P_sell_"+dev+timetag)
                    p_hp[dev,d,t]   = model.addVar(vtype="C", name="P_hp_"+dev+timetag)

        # Amount of gas consumed
        gas_tariffs = eco["gas"].keys()
        
        G = {}
        for tar in gas_tariffs:
            G[tar] = {}
            for dev in ("boiler","chp"):
                for n in range(len(eco["gas"][tar]["lb"])):
                    G[tar][dev,n] = model.addVar(vtype="C", name="G_"+dev+"_"+str(n))
        
        G_total = {dev: model.addVar(vtype="C", name="G_total_"+dev)
                  for dev in ("boiler","chp")}
        
        # Amount of electricity consumed
        el_tariffs = eco["el"].keys()
        
        El = {}
        for tar in el_tariffs:
            El[tar] = {}
            for dev in ("grid_hou","grid_hp"):
                for n in range(len(eco["el"][tar]["lb"])):
                    El[tar][dev,n] = model.addVar(vtype="C", name="El_"+dev+"_"+str(n))
        
        El_total = {dev: model.addVar(vtype="C", name="El_total_"+dev)
                    for dev in ("grid_hou","grid_hp")}
                                       
        # Split EH for HP tariff
        eh_split = {}
        for d in days:
            for t in time_steps:
                timetag = "_"+str(d)+"_"+str(t)                
                eh_split["eh_w/o_hp",d,t] = model.addVar(vtype="C", 
                                                    name="p_eh_w/o_hp"+timetag)
                eh_split["eh_w/_hp",d,t]  = model.addVar(vtype="C", 
                                                     name="p_eh_w/_hp"+timetag)
                                
        # Tariffs    
        x_tariff = {"gas":{}, "el":{}}   
        
        # All tariff gradations
        for tar in gas_tariffs:
            x_tariff["gas"][tar] = {}
            for n in range(len(eco["gas"][tar]["lb"])):            
                x_tariff["gas"][tar][n] = model.addVar(vtype="B", 
                                               name="x_tariff_"+tar+"_"+str(n))
        
        for tar in el_tariffs:
            x_tariff["el"][tar] = {}
            for n in range(len(eco["el"][tar]["lb"])):            
                x_tariff["el"][tar][n] = model.addVar(vtype="B", 
                                               name="x_tariff_"+tar+"_"+str(n))
        
        # General tariff decision variables
        x_gas = {tar: model.addVar(vtype="B", name="x_"+tar)
                for tar in gas_tariffs}
                    
        x_el = {tar: model.addVar(vtype="B", name="x_"+tar)
                for tar in el_tariffs}     
                
        # Design heat load following DIN EN 12831
        dsh = model.addVar(vtype = "C", name = "dsh" )
         
        #%% Variables for Subsidies 
         
        #EEG for PV
        b_eeg = {}
        for powerstep in ("10","40","750","10000"):
            b_eeg[powerstep] = model.addVar(vtype="B",
                                            name="b_eeg_"+str(powerstep))            
                    
        p_sell_pv = {}
        for powerstep in ("total","10","40","750","10000"):
            p_sell_pv[powerstep] = model.addVar(vtype="C",
                                            name="p_sell_pv_"+str(powerstep))               
        
        pv_power = model.addVar(vtype="C", name = "pv_power")
        
        #KWKG for CHP           
        b_kwkg = {}
        for concept in ("micro","50","100","250","2000","10000"):   
            b_kwkg[concept] = model.addVar(vtype="B",
                                            name="b_sub_kwkg_"+str(concept))
            
        p_use_chp = {}
        for powerstep in ("50","100","10000"):
            p_use_chp[powerstep] = model.addVar(vtype = "C",
                                            name ="p_use_chp_"+str(powerstep))            
        p_sell_chp = {}
        for powerstep in ("50","100","250","2000","10000"):
            p_sell_chp[powerstep] = model.addVar(vtype = "C",
                                            name ="p_sell_chp_"+str(powerstep)) 
        
        p_chp_total = {}
        for usage in ("use","sell"):
            p_chp_total[usage] = model.addVar(vtype = "C",
                                            name ="p_chp_total_"+str(usage)) 
            
        lin_kwkg = {}
        for powerstep in ("50","100","250","2000","10000"):
            lin_kwkg[powerstep] = model.addVar(vtype = "C", 
                                                name = "lin_kwkg_" + powerstep,
                                                lb = 0)
        
        #BAT
        lin_pv_bat = model.addVar(vtype="C", name="lin_pv_bat")
        lin_bat_sub = model.addVar(vtype="C", name="lin_bat_sub")
        
        #CHP
        x_chp = {}
        for dev in ("lump","var"):
            x_chp[dev,"micro"]  = model.addVar(vtype="B", name="x_chp_"+str(dev)+"_micro")        
        
        lin_chp_kwkg = model.addVar(vtype = "C", name="lin_chp_kwkg",lb = 0)
        
        chp_powerstep = {}
        for i in range (1,5):
            chp_powerstep[i] = model.addVar(vtype = "C", 
                                         name = "kwk_powerstep"+str(i), lb = 0)
            
        sub_chp_basic = model.addVar(vtype="C", name="sub_chp_basic", lb = 0 )
        
        #STC
        b_bafa_stc = {}
        for i in ("basic_fix","basic_var","inno","add1"):
            b_bafa_stc[i] = model.addVar(vtype = "B", name = "b_bafa_stc_"+i)
         
        sub_bafa_stc = {}
        for i in ("basic_var", "basic_fix", "inno", "build_eff"):
            sub_bafa_stc[i] = model.addVar(vtype = "C", 
                                          name = "sub_bafa_stc_"+i, lb = 0)

        lin_sub_stc = model.addVar(vtype = "C", 
                            name = "lin_sub_stc", lb = 0, ub = A_max)
        
        #HP
        lin_hp_sub_basic = {}
        for dev in ("hp_air", "hp_geo"):
            lin_hp_sub_basic[dev] = model.addVar(vtype="C", name="lin_hp_sub_basic_"+dev, lb = 0)
        
        lin_hp_sub_inno = {}
        for dev in ("hp_air", "hp_geo"):
            lin_hp_sub_inno[dev] = model.addVar(vtype="C", name="lin_hp_sub_inno_"+dev, lb = 0)   
            
        lin_hp_sub_add = {}
        for dev in ("hp_air", "hp_geo"):
            lin_hp_sub_add[dev] = model.addVar(vtype="C", name="lin_hp_sub_add_"+dev, lb = 0)
                
        b_bafa_hp= {}
        for dev in ("hp_air", "hp_geo"):
            b_bafa_hp[dev] = {}
            for i in ("basic_fix", "basic_var", "inno_var", "inno_fix", "add1"):
                b_bafa_hp[dev][i] = model.addVar(vtype = "B", name = "b_bafa_"+dev+"_"+i)
            
        sub_bafa_hp = {}
        for dev in ("hp_air", "hp_geo"):
            sub_bafa_hp[dev] = {}
            for i in ("basic", "inno", "build_eff"):
                sub_bafa_hp[dev][i] = model.addVar(vtype = "C", name = "sub_bafa_"+dev+"_"+i, lb = 0)
                
        energy_hp = {}
        for dev in ("hp_air", "hp_geo"):
            energy_hp[dev] = {}
            for i in ("total_heat", "total_power"):
                energy_hp[dev][i] = model.addVar(vtype = "C", name = "energy_hp_"+dev+"_"+i, lb = 0)
        
        #PELLET           
        b_bafa_pellet = {}
        for i in ("basic_fix", "basic_storage", "basic_var", "inno_fix", "inno_storage", "add1"):
            b_bafa_pellet[i] = model.addVar(vtype = "B", name = "b_bafa_pellet_"+i)
            
        sub_bafa_pellet = {}
        for i in ("basic", "inno", "build_eff"):
            sub_bafa_pellet[i] = model.addVar(vtype = "C", name = "sub_bafa_pellet_"+i, lb = 0)

        lin_sub_pellet = {}
        for i in ("basic", "inno", "storage"):        
            lin_sub_pellet[i]= model.addVar(vtype = "C", name = "lin_sub_pellet_"+i, lb = 0)            
                
        #%% Variables for restructuring measures
            
        # Variable for building-shell components
        x_restruc  ={}
        for dev in building_components:
            for n in restruc_scenarios:
                x_restruc[dev,n] = model.addVar(vtype="B", name="x_"+dev+"_"+str(n))
        
        # Variable if restrictions for renovation programmes are satisfied
        b_sub_restruc = {} 
        for dev in (building_components + kfw_standards):
            b_sub_restruc[dev] = model.addVar(vtype = "B", name = "b_sub_restruc"+dev)
        
        # Heating demand depending on to the chosen building shell components
        heat_mod = {}  
        for d in days:
            for t in time_steps:
                heat_mod[d,t] = model.addVar(vtype = "C", name = "heat_mod", lb = 0)
        
        # Transmission losses
        Q_Ht = {}  
        for d in days:
            for t in time_steps:
                Q_Ht[d,t] = model.addVar(vtype = "C", name = "HT")
        
        # Real solar gains
        Q_s = {}  
        for d in days:
            for t in time_steps:
                Q_s[d,t] = model.addVar(vtype = "C", name = "Qs")               
        
        # Primary energy demand in accordance with DIIN V 4108
        Q_p_DIN = model.addVar(vtype = "C", name = "Q_p_DIN")
        
        # Transmission coefficient in accordance with DIN V 4108
        H_t = model.addVar(vtype = "C", name = "H_t", lb = 0)  
       
        # Variable for chosen heating concept (relevant for primary energy demand)
        heating_concept = {}
        lin_H_t = {}        
        for n in ep_table["ep"].keys():
            heating_concept[n] = model.addVar(vtype = "B", name = "heating_concept_"+str(n))
            lin_H_t[n] = model.addVar(vtype = "C", name = "lin_H_t_+str(n)", lb = 0)      
        
        # Variables for flow temperature
        b_TVL = {}
        for temp in ("35","55"):
            b_TVL[temp] = model.addVar(vtype = "B", name = "b_TVL_"+str(temp))
            
        lin_TVL = {}
        for temp in ("35","55"):
            for dev in ("hp_geo","hp_air"):
                for d in days:
                    for t in time_steps:
                        lin_TVL[temp,dev,d,t] = model.addVar(vtype = "C", name = "lin_TVL_"+str(temp), lb = 0) 
            
#%% Objectives      
                   
        c_total = model.addVar(vtype="C", name="c_total", lb= -gp.GRB.INFINITY)
        
        emission = model.addVar(vtype="C", name= "CO2_emission", lb= -gp.GRB.INFINITY)      
                
        # Update
        model.update()

#%% Set Objective

        if options["opt_costs"]:
            model.setObjective(c_total, gp.GRB.MINIMIZE)
        else:
            model.setObjective(emission, gp.GRB.MINIMIZE)

#%% Define Constraints

        M = 100000

        # Differentiation between old and new buildings because of different 
        # regulations in the "Marktanreizprogramm" for HP and STC
        if options["New_Building"]:
            alpha = 0
            model.addConstr(b_TVL["35"] == 1)
       
        else: 
            alpha = 1
            model.addConstr(b_TVL["55"] == 1)
            
        # Differentiation between SFH and MFH because of different 
        # regulations in the "Marktanreizprogramm" STC 
        if options["MFH"]:
            MFH = 1
        else:
            MFH = 0      
            
        #%% Determine device capacity
        for d in days:
            for t in time_steps:
                for dev in heater:
                    model.addConstr(capacity[dev] >= heat_nom[dev,d,t],                      
                                    name="Capacity_"+dev+"_"+str(d)+"_"+str(t))
        
        for dev in solar:
            model.addConstr(capacity[dev] == area[dev], name="Capacity_"+dev)
        
        dev = "tes"
        model.addConstr(capacity[dev] == volume, name="Capacity_"+dev)
        
        dev = "bat"
        model.addConstr(capacity[dev] == soc_nom[dev], name="Capacity_"+dev)

        model.addConstr(x["tes"] == 1)
 
        #%% Capacitybounds:
        
        #Heater
        for dev in heater:
            model.addConstr(capacity[dev] >= x[dev] * devs[dev]["Q_nom_min"],
                            name="Capacity_min_"+dev)
        
            model.addConstr(capacity[dev] <= x[dev] * devs[dev]["Q_nom_max"],
                            name="Capacity_max_"+dev)
                    
        #Solar Components               
        for dev in solar:
            # Minimum area for each device
            model.addConstr(area[dev] >= x[dev] * devs[dev]["area_min"],
                            name="Minimum_area_"+dev)
            # Maximum area for each device
            model.addConstr(area[dev] <= x[dev] * A_max,
                            name="Maximum_area_"+dev)
                            
        # Maximum available area
        model.addConstr(sum(area[dev] for dev in solar) <= A_max,
                        name="Maximum_total_area")
        
        #Thermal Energy Storage
        dev = "tes"
        model.addConstr(volume >= x[dev] * devs[dev]["volume_min"], 
                        name="Storage_Volume_min")
        model.addConstr(volume <= x[dev] * devs[dev]["volume_max"], 
                        name="Storage_Volume_max")        
        model.addConstr(soc_nom[dev] == volume * params["rho_w"] * 
                        params["c_w"] * devs[dev]["dT_max"] / 3600000, 
                        name="Storage_Volume")
        
        #Batterie
        dev = "bat"
        model.addConstr(soc_nom[dev] >= x[dev] * devs[dev]["cap_min"],
                        name="Battery_capacity_min")
        model.addConstr(soc_nom[dev] <= x[dev] * devs[dev]["cap_max"],
                        name="Battery_capacity_max")  

#%% Economic constraints
        
        model.addConstr(c_total ==  (sum(c_inv[key] for key in c_inv.keys())       
                                   + sum(c_om[key]  for key in c_om.keys())
                                   + sum(c_dem[key] for key in c_dem.keys())
                                   + sum(c_fix[key] for key in c_fix.keys())
                                   - sum(revenue[key] for key in revenue.keys())
                                   - sum(subsidy[key] for key in subsidy.keys())))     
        
        # Investments
        for dev in devs.keys():
            model.addConstr(c_inv[dev] == eco["crf"] * (1-devs[dev]["rval"]) *
                                         (x[dev] * (devs[dev]["c_inv_fix"] + 
                                          eco["inst_costs"]["EFH"][dev] * (1 - MFH) + 
                                          eco["inst_costs"]["MFH"][dev] * MFH) +                                         
                                          capacity[dev] * devs[dev]["c_inv_var"]),
                                          name="Investment_costs_"+dev)
        
        # Operation and maintenance
        for dev in devs.keys():
            model.addConstr(c_om[dev] == eco["b"]["infl"] * eco["crf"] * 
                                         devs[dev]["c_om_rel"] * 
                                        (x[dev] * devs[dev]["c_inv_fix"] +
                                         capacity[dev] * devs[dev]["c_inv_var"]),
                                         name="O&M_costs_"+dev)

        # Demand related costs:

        # Gas:
        # Exactly one gas tariff if at least one chp or boiler is installed        
        for dev in ("chp", "boiler"):
            model.addConstr(sum(x_gas[key] for key in x_gas.keys()) >= x[dev],
                            name="single_gas_tariff_"+dev)
            
        model.addConstr(sum(x_gas[key] for key in x_gas.keys()) <= 1,
                        name="single_gas_tariff_overall")

        for tar in gas_tariffs:
            # Choose one tariff level for the dertermined gas tariff
            model.addConstr(sum(x_tariff["gas"][tar][n] 
                            for n in x_tariff["gas"][tar].keys()) == x_gas[tar],
                            name="gas_levels_"+tar+"_"+str(n))
            
            # The tariff level is restricted by the consumed gas amount
            for n in x_tariff["gas"][tar].keys():
                model.addConstr(x_tariff["gas"][tar][n] * eco["gas"][tar]["lb"][n] <= 
                                (G[tar]["boiler",n] + G[tar]["chp",n]) * 0.001,
                                name="gas_level_lb"+tar+"_"+str(n))
                
                model.addConstr(x_tariff["gas"][tar][n] * eco["gas"][tar]["ub"][n] >= 
                                (G[tar]["boiler",n] + G[tar]["chp",n]) * 0.001,
                                name="gas_level_ub"+tar+"_"+str(n))
                
        # Divide because of energy tax
        for dev in ("boiler","chp"):   
            # Total amount of gas used
            model.addConstr(G_total[dev] == sum(sum(G[tar][dev,n] 
                                            for n in x_tariff["gas"][tar].keys())
                                            for tar in gas_tariffs))
                    
            model.addConstr(G_total[dev] == sum(clustered["weights"][d] * dt * sum(energy[dev,d,t] 
                                    for t in time_steps)
                                    for d in days))
            # Variable gas costs
            if dev == "chp":
                model.addConstr(c_dem[dev] == sum(sum(
                        G[tar][dev,n] * (eco["gas"][tar]["var"][n] - eco["energy_tax"])
                        for n in x_tariff["gas"][tar].keys())
                        for tar in gas_tariffs) * eco["b"]["gas"] * eco["crf"],
                        name="c_dem_"+dev)
            else: 
                model.addConstr(c_dem[dev] == sum(sum(
                        G[tar][dev,n] * eco["gas"][tar]["var"][n]
                        for n in x_tariff["gas"][tar].keys())
                        for tar in gas_tariffs) * eco["b"]["gas"] * eco["crf"],
                        name="c_dem_"+dev)
                    
        # Fixed costs for gas administration
        model.addConstr(c_fix["gas"] == sum(sum(x_tariff["gas"][tar][n] * eco["gas"][tar]["fix"][n]
                        for n in x_tariff["gas"][tar].keys())
                        for tar in gas_tariffs),
                        name="c_fix_gas")
                    
            
        # Electricity:                   
        # Choose one tariff for general electricity purchase
        non_hp_tariffs = sum(x_el[tar] for tar in x_el.keys() 
                            if eco["el"][tar]["hp"] == 0)
            
        model.addConstr(non_hp_tariffs == 1,
                        name="single_el_tariff")

        # If a HP is installed, the HP tariff is available
        hp_tariffs = sum(x_el[tar] for tar in x_el.keys() if eco["el"][tar]["hp"] == 1)
        
        if options["HP tariff"]:
            # Allow special heat pump tariffs
            model.addConstr(hp_tariffs <= x["hp_air"] + x["hp_geo"], name="optional_hp_tariff")
        else:
            # Prohibit special heat pump tariffs
            model.addConstr(hp_tariffs <= 0, name="optional_hp_tariff")

        # grid_hou electricity cannot be purchased with el_hp tariff
        for tar in x_el.keys():
            if eco["el"][tar]["hp"] == 1:
                for n in x_tariff["el"][tar].keys():
                    model.addConstr(El[tar]["grid_hou",n] == 0)
        
        for tar in el_tariffs:
            # Choose one tariff level for the dertermined el tariff
            model.addConstr(sum(x_tariff["el"][tar][n] 
                            for n in x_tariff["el"][tar].keys()) == x_el[tar])
            
            # The tariff level is restricted by the consumed el amount
            for n in x_tariff["el"][tar].keys():
                model.addConstr(x_tariff["el"][tar][n] * eco["el"][tar]["lb"][n] <= 
                (El[tar]["grid_hou",n] + El[tar]["grid_hp",n]) * 0.001,
                name="el_level_lb_"+tar+"_"+str(n))
                
                model.addConstr(x_tariff["el"][tar][n] * eco["el"][tar]["ub"][n] >= 
                (El[tar]["grid_hou",n] + El[tar]["grid_hp",n]) * 0.001,
                name="el_level_ub_"+tar+"_"+str(n))
            
        # Devide because of optional HP tariff
        for dev in ("grid_hou", "grid_hp"):
            # Total amount of electricity used
            model.addConstr(El_total[dev] == sum(sum(El[tar][dev,n] 
                                            for n in x_tariff["el"][tar].keys())
                                            for tar in el_tariffs))
            
            model.addConstr(El_total[dev] == sum(clustered["weights"][d] * sum(p_grid[dev,d,t] 
                                            for t in time_steps)
                                            for d in days) * dt)
        
            # Variable electricity costs
            model.addConstr(c_dem[dev] == sum(sum(
                    El[tar][dev,n] * eco["el"][tar]["var"][n]
                    for n in x_tariff["el"][tar].keys())
                    for tar in el_tariffs) * eco["b"]["el"] * eco["crf"],
                    name="c_dem_"+dev)
        
        # Fixed costs for el administration
        model.addConstr(c_fix["el"] == sum(sum(x_tariff["el"][tar][n] * 
                                        eco["el"][tar]["fix"][n]
                                        for n in x_tariff["el"][tar].keys())
                                        for tar in el_tariffs),
                                        name="c_fix_el")
                                        
        # Pellets
        dev = "pellet"
        model.addConstr(c_dem[dev] == eco["pel"]["pel_sta"]["var"][0] *         
                                      sum(clustered["weights"][d] *  
                                      sum(heat[dev,d,t] 
                                      for t in time_steps) 
                                      for d in days) * dt, 
                                      name="c_dem_"+dev)       
                                                                                     
        #%% Revenues for selling chp-electricity to the grid
        
        dev = "chp"
        model.addConstr(revenue[dev] == eco["b"]["eex"] * eco["crf"] * dt *
            sum(clustered["weights"][d] * sum(p_sell[dev,d,t]  * eco["price_sell_el"]
            for t in time_steps) for d in days),
            name="Feed_in_rev_"+dev)
                                                   
#%% Technical constraints
    
        # Devices can be switched on only if they have been purchased       
        for dev in heater:
            model.addConstr(sum(sum(y[dev,d,t] for t in time_steps) for d in days) 
                                 <= params["time_steps"] * params["days"] * x[dev],
                                  name="Activation_"+dev)
                                  
        # Flow temperature is either 35 or 55°c
        # Choice depends on the age of the building       
        model.addConstr(b_TVL["35"] + b_TVL["55"] == 1)
        
        # Devices nominal values (heat_nom = y * capacity)
        for dev in heater:
            for d in days:
                for t in time_steps:
                    # Abbreviations
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    q_nom_min = devs[dev]["Q_nom_min"]
                    q_nom_max = devs[dev]["Q_nom_max"]
                    
                    model.addConstr(heat_nom[dev,d,t] <= q_nom_max * y[dev,d,t],
                                            name="Max_heat_1_"+dev+"_"+timetag)
                    
                    model.addConstr(heat_nom[dev,d,t] >= q_nom_min * y[dev,d,t],
                                            name="Min_heat_1_"+dev+"_"+timetag)
                        
                    model.addConstr(capacity[dev] - heat_nom[dev,d,t]
                                          <= q_nom_max * (x[dev] - y[dev,d,t]),
                                            name="Max_heat_2_"+dev+"_"+timetag)
                    
                    model.addConstr(capacity[dev] - heat_nom[dev,d,t]
                                          >= q_nom_min * (x[dev] - y[dev,d,t]),
                                            name="Min_heat_2_"+dev+"_"+timetag)
        
        for dev in ("eh","chp","boiler","pellet"):
            for d in days:
                for t in time_steps:
                    # Abbreviations
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    mod_lvl = devs[dev]["mod_lvl"]
                    eta     = devs[dev]["eta"][d,t]
                    omega   = devs[dev]["omega"][d,t]
                    
                    model.addConstr(heat[dev,d,t] <= heat_nom[dev,d,t],
                                    name="Max_heat_operation_"+dev+"_"+timetag)
                    
                    model.addConstr(heat[dev,d,t] >= heat_nom[dev,d,t] * mod_lvl,
                                    name="Min_heat_operation_"+dev+"_"+timetag)                    
  
                    model.addConstr(power[dev,d,t] == 1/eta * heat[dev,d,t],
                                    name="Power_equation_"+dev+"_"+timetag)
                            
                    model.addConstr(energy[dev,d,t] == 1/omega * (heat[dev,d,t] + power[dev,d,t]),
                                    name="Energy_equation_"+dev+"_"+timetag)
                                    
        #Compute nominal power consumption of HP:
        for dev in ("hp_air","hp_geo"):
            for d in days:
                for t in time_steps:
                    model.addConstr(heat_nom[dev,d,t] == power_nom[dev,d,t] * 
                                                         devs[dev]["cop_a2w35"],
                                    name="Power_nom_"+dev+"_"+str(d)+"_"+str(t))

        # Heat output between mod_lvl*Q_nom and Q_nom (P_nom for heat pumps)
        # Power and Energy directly result from Heat output                          
        for dev in ("hp_air","hp_geo"):
            for d in days:
                for t in time_steps:
                    # Abbreviations
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    mod_lvl = devs[dev]["mod_lvl"]
                    omega   = devs[dev]["omega"][d,t]
                                           
                    model.addConstr(power[dev,d,t] <= power_nom[dev,d,t],
                                 name="Max_pow_operation_"+dev+"_"+timetag)
                    
                    model.addConstr(power[dev,d,t] >= power_nom[dev,d,t] * mod_lvl,
                                 name="Min_pow_operation_"+dev+"_"+timetag)
                
                    for temp in b_TVL.keys():
                        model.addConstr(lin_TVL[temp,dev,d,t] <= M * b_TVL[temp])
                        model.addConstr(heat[dev,d,t] - lin_TVL[temp,dev,d,t] >= 0)
                        model.addConstr(heat[dev,d,t] - lin_TVL[temp,dev,d,t] <= M * (1 - b_TVL[temp]))
                
                    model.addConstr(power[dev,d,t] == sum(lin_TVL[temp,dev,d,t] / 
                                                          devs[dev]["cop_w"+temp][d,t] 
                                                          for temp in b_TVL.keys()),
                                                          name="Min_pow_operation_"+dev+"_"+timetag)
                                                          
                    model.addConstr(energy[dev,d,t] == 1/omega * (heat[dev,d,t] + power[dev,d,t]),
                                                                name="Energy_equation_"+dev+"_"+timetag)

        #%% Solar components

        for dev in solar:
            for d in days:
                for t in time_steps:
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    eta_inverter = 0.97
                    eta_th = devs[dev]["eta_th"][d][t]
                    eta_el = eta_inverter * devs[dev]["eta_el"][d][t]
                    solar_irrad = clustered["solar_irrad"][d][t]

                    model.addConstr(heat[dev,d,t] <= eta_th * area[dev] * 
                                                     solar_irrad,
                                                     name="Solar_thermal_"+dev+timetag)
                    
                    model.addConstr(power[dev,d,t] <= eta_el * area[dev] * 
                                                      solar_irrad,
                                                      name="Solar_electrical_"+dev+timetag)
                                                      
        dev = "pv" 
        model.addConstr(pv_power == area[dev] * devs[dev]["p_nom"] / devs[dev]["area_mean"])
                               
        #%% Storages      
                               
        # Nominal storage content (SOC)
        for dev in storage:
            for d in days:
                #Inits
                model.addConstr(soc_nom[dev] >= soc_init[dev,d], 
                                                name="SOC_nom_inits_"+dev+"_"+str(d))
                for t in time_steps:
                    # Regular storage loads
                    model.addConstr(soc_nom[dev] >= soc[dev,d,t],
                                                    name="SOC_nom_"+dev+"_"+str(d)+"_"+str(t))
                    
        # SOC repetitions
        for dev in storage:
            for d in range(params["days"]):
                if np.max(clustered["weights"]) > 1:
                    model.addConstr(soc[dev,d,params["time_steps"]-1] == soc_init[dev,d],
                                                                         name="repetitions_"+dev+"_"+str(d))
                      
        #Just TES
        dev = "tes"
        
        k_loss = devs[dev]["k_loss"]
        eta_ch = devs[dev]["eta_ch"]
        eta_dch = devs[dev]["eta_dch"]
        
        for d in days:
            for t in time_steps:
                if t == 0:
                    if np.max(clustered["weights"]) == 1:
                        if d == 0:
                           soc_prev = soc_init[dev,d]
                        else:
                           soc_prev = soc[dev,d-1,params["time_steps"]-1]
                    else:
                        soc_prev = soc_init[dev,d]
                else:
                    soc_prev = soc[dev,d,t-1]
                
                timetag = "_" + str(d) + "_" + str(t)
                
                charge = eta_ch * ch[dev,d,t]
                discharge = 1 / eta_dch * dch[dev,d,t]
                
                model.addConstr(soc[dev,d,t] == (1 - k_loss) * soc_prev + 
                                dt * (charge - discharge),
                                name="Storage_bal_"+dev+timetag)

        #Just Bat
        dev = "bat"
        
        k_loss = devs[dev]["k_loss"]
        eta_ch = devs[dev]["eta"]
        eta_dch = devs[dev]["eta"]
        
        for d in days:
            for t in time_steps:
                if t == 0:
                    if np.max(clustered["weights"]) == 1:
                        if d == 0:
                           soc_prev = soc_init[dev,d]
                        else:
                           soc_prev = soc[dev,d-1,params["time_steps"]-1]
                    else:
                        soc_prev = soc_init[dev,d]
                else:
                    soc_prev = soc[dev,d,t-1]

                timetag = "_" + str(d) + "_" + str(t)
                
                charge = eta_ch * ch[dev,d,t]
                discharge = 1 / eta_dch * dch[dev,d,t]
    
                model.addConstr(soc[dev,d,t] == (1 - k_loss) * soc_prev + 
                                dt * (charge - discharge),
                                name="Storage_bal_"+dev+timetag)             
    
                model.addConstr(ch[dev,d,t] <= x[dev] * devs[dev]["P_ch_fix"] + 
                                capacity[dev] * devs[dev]["P_ch_var"],
                                name="P_ch_max"+timetag)
    
                model.addConstr(dch[dev,d,t] <= x[dev] * devs[dev]["P_dch_fix"] + 
                                capacity[dev] * devs[dev]["P_dch_var"],
                                name="P_dch_max"+timetag)
        
                            
        #%% Thermal balance and electricity balance
                            
        # Differentiation for dhw-heating: either electric or via heating system
        if options["dhw_electric"]:    
            
            #Thermal balance
            dev = "tes"        
            for d in days:
                for t in time_steps:                
                    model.addConstr(dch[dev,d,t] == heat_mod[d,t], 
                                                    name="Thermal_max_discharge_"+str(d)+"_"+str(t))
                    model.addConstr(ch[dev,d,t] == sum(heat[dv,d,t] for dv in (heater+solar)),
                                                    name="Thermal_max_charge_"+str(d)+"_"+str(t))
            #Electricity balance            
            for d in days:
                for t in time_steps:
                    # For components without hp-tariff (p_use["bat"] referring to discharge)
                    model.addConstr(clustered["electricity"][d,t] +
                                    clustered["dwh"][d,t] +
                                    eh_split["eh_w/o_hp",d,t] + 
                                    ch["bat",d,t] == p_grid["grid_hou",d,t] + 
                                                     sum(p_use[dev,d,t] 
                                                     for dev in ("pv","bat","chp")),
                                                     name="El_bal_w/o_HPtariff"+str(d)+"_"+str(t))
 
                    # For components with hp-tariff (p_hp["bat"] referring to discharge)
                    model.addConstr(power["hp_air",d,t] + 
                                    power["hp_geo",d,t] + 
                                    eh_split["eh_w/_hp",d,t] == p_grid["grid_hp",d,t] + 
                                                                sum(p_hp[dev,d,t] 
                                                                for dev in ("pv","bat","chp")),
                                                                name="El_bal_w/_HPtariff"+str(d)+"_"+str(t))    
        
        else:                
            #Thermal balance
            dev = "tes"        
            for d in days:
                for t in time_steps:                
                    model.addConstr(dch[dev,d,t] == heat_mod[d,t] + clustered["dhw"][d,t], 
                                                    name="Thermal_max_discharge_"+str(d)+"_"+str(t))
                    model.addConstr(ch[dev,d,t] == sum(heat[dv,d,t] for dv in (heater+solar)),
                                                    name="Thermal_max_charge_"+str(d)+"_"+str(t))
            #Electricity balance            
            for d in days:
                for t in time_steps:
                    # For components without hp-tariff (p_use["bat"] referring to discharge)
                    model.addConstr(clustered["electricity"][d,t] +
                                    eh_split["eh_w/o_hp",d,t] + 
                                    ch["bat",d,t] == p_grid["grid_hou",d,t] + 
                                                     sum(p_use[dev,d,t] 
                                                     for dev in ("pv","bat","chp")),
                                                     name="El_bal_w/o_HPtariff"+str(d)+"_"+str(t))
 
                    # For components with hp-tariff (p_hp["bat"] referring to discharge)
                    model.addConstr(power["hp_air",d,t] + 
                                    power["hp_geo",d,t] + 
                                    eh_split["eh_w/_hp",d,t] == p_grid["grid_hp",d,t] + 
                                                                sum(p_hp[dev,d,t] 
                                                                for dev in ("pv","bat","chp")),
                                                                name="El_bal_w/_HPtariff"+str(d)+"_"+str(t))    
                    
        
        #Split CHP and PV generation and bat discharge Power into self-consumed, sold and transferred powers
        for d in days:
            for t in time_steps:
                dev = "bat"
                model.addConstr(p_sell[dev,d,t] + 
                                p_use[dev,d,t] + 
                                p_hp[dev,d,t] == dch[dev,d,t],
                                name="power=sell+use+hp_"+dev+"_"+str(d)+"_"+str(t))
                dev = "pv"
                model.addConstr(p_sell[dev,d,t] + 
                                p_use[dev,d,t] + 
                                p_hp[dev,d,t] == power[dev,d,t],
                                name="power=sell+use+hp_"+dev+"_"+str(d)+"_"+str(t))
                dev = "chp"
                model.addConstr(p_sell[dev,d,t] + 
                                p_use[dev,d,t] + 
                                p_hp[dev,d,t] == power[dev,d,t],
                                name="power=sell+use+hp_"+dev+"_"+str(d)+"_"+str(t))
                    
        # Split EH power consumption into cases with and without heat pump installed
        dev = "eh"              
        for d in days:
            for t in time_steps:
                model.addConstr(eh_split["eh_w/o_hp",d,t] + 
                                eh_split["eh_w/_hp",d,t] == power["eh",d,t])
                                
                model.addConstr(eh_split["eh_w/_hp",d,t]  <= 
                                                  (x["hp_air"] + x["hp_geo"]) * 
                                                  devs[dev]["Q_nom_max"])   
                                                  
                model.addConstr(eh_split["eh_w/o_hp",d,t] <= (2 - x["hp_air"] 
                                                                - x["hp_geo"]) * 
                                                                devs[dev]["Q_nom_max"])                    
                            
        # Heat pump's operation depends on storage temperature
        for d in days:
            for t in time_steps:
                # Abbreviations
                dT_relative = devs["hp_air"]["dT_max"] / devs["tes"]["dT_max"]
                # Residual storage content
                resSC = (devs["tes"]["volume_max"] * devs["tes"]["dT_max"]
                         * params["rho_w"] * params["c_w"] * (1 - dT_relative)
                         / 3600000)                
                model.addConstr(soc["tes",d,t] <= soc_nom["tes"] * dT_relative 
                      + (1 - y["hp_air",d,t]) * resSC,
                      name="Heat_pump_act_"+str(d)+"_"+str(t))      
                
        # Design heat load following DIN EN 12831 has to be covered
        if options["Design_heat_load"]:
            delta_temp = clustered["inside_temp"] - clustered["standard_temp"] 
            model.addConstr(dsh == (H_t + 0.5 * 0.34 * building["dimensions"]["Volume"]) *
                                                             delta_temp / 1000)
        
            model.addConstr(dsh <= sum(capacity[dev] 
                                       for dev in ("boiler","chp","eh")) +
                                       sum(capacity[hp] * devs[hp]["cop_a2w55"]
                                       for hp in ("hp_air", "hp_geo")),
                                       name="Design_heat_load")
        else:
            model.addConstr(dsh == 0 )
     
#%% CO2-Emissions
     
        emission_pellet = (eco["pel"]["pel_sta"]["emi"] * 
                           sum(clustered["weights"][d] * dt * 
                           sum(heat["pellet",d,t] 
                           for t in time_steps) 
                           for d in days))

        emissions_gas = sum(eco["gas"][tar]["emi"] * 
                        sum((G[tar]["boiler",n] + G[tar]["chp",n]) 
                        for n in x_tariff["gas"][tar].keys())
                        for tar in gas_tariffs)
        
        emissions_grid = sum(eco["el"][tar]["emi"] * 
                         sum((El[tar]["grid_hou",n] + El[tar]["grid_hp",n])
                         for n in x_tariff["el"][tar].keys()) 
                         for tar in el_tariffs)
               
        emissions_feedin = 0.569 * sum(clustered["weights"][d] * dt * 
                                   sum(sum(p_sell[dev,d,t] 
                                   for dev in ("pv","bat","chp"))
                                   for t in time_steps)
                                   for d in days)
        
        model.addConstr(emission == emission_pellet + emissions_gas + 
                                    emissions_grid - emissions_feedin)
                                                          
#%% Subsidies: 
                                                          
                                                          
        #%% EEG for PV
        dev = "pv"        
        # Sold electricity from PV
        model.addConstr(p_sell_pv["total"] == sum(clustered["weights"][d] * 
                                              sum(p_sell[dev,d,t]
                                              for t in time_steps)
                                              for d in days) * dt)   
        
        if options["EEG"]:            
            pv_powerstages = ("10","40","750","10000")
            
            # Differentiation of funding rate depending on installed PV-power                       
            model.addConstr(pv_power <= sum(float(n) *  b_eeg[n] 
                                        for n in pv_powerstages))
            
            model.addConstr(x[dev] >= sum(b_eeg[n] for n in pv_powerstages))
 
            model.addConstr(p_sell_pv["total"] == sum(p_sell_pv[n] 
                                                      for n in pv_powerstages))
            for n in pv_powerstages:
                model.addConstr(1.0 / M * p_sell_pv[n]  <= M * b_eeg[n])

            # Calculation of total earnings from sold electricity
            model.addConstr(subsidy[dev] == eco["b"]["eex"] * eco["crf"] * 
                                            sum(p_sell_pv[n] * sub_par["eeg"][n]
                                            for n in pv_powerstages),
                                            name="Feed_in_rev_"+dev)
            
            # If EEG is available: subsidy instead of revenue
            model.addConstr(revenue[dev] == 0)
                                       
        else:            
            # If EEG is not available: revenue instead of subsidy
            model.addConstr(subsidy[dev] == 0)            
            model.addConstr(revenue[dev] == eco["b"]["eex"] * eco["crf"] * dt *
                                            eco["price_sell_el"] *
                                            p_sell_pv["total"],
                                            name="Feed_in_rev_"+dev)                                               
                                    
        #%% CHP        
        dev = "chp"   
        
        # There are two subsidy-possibilities for chps
        # 1. Remuneration system in accordance with the KWKG; In this context 
        # the law differentiate between large and small chps 
        # 2. Investment subsidy for small chps 
        model.addConstr(subsidy[dev] == sub["micro"] + 
                                        sub["large"] + 
                                        sub["bafa"],
                                        name = "Chp_subsidy_combination") 
        
        # Total installed CHP-power
        power_chp = capacity[dev] * devs[dev]["sigma"] 
        
        # Self consumed electricity from CHP                            
        model.addConstr(p_chp_total["use"] == dt * sum(clustered["weights"][d] *
                                                   sum(p_use[dev,d,t]                             
                                                   for t in time_steps) 
                                                   for d in days))
                                                  
        # Sold electricity from CHP
        model.addConstr(p_chp_total["sell"] == dt * sum(clustered["weights"][d] *
                                                    sum(p_sell[dev,d,t]                           
                                                    for t in time_steps) 
                                                    for d in days))

        #BAFA-Subsidy for Mirco-CHP
        #Program has three parts: basic-subsidy, thermal-efficiency-bonus and 
        #power-efficiency-bonus
        #Further informations:
        #http://www.bafa.de/DE/Energie/Energieeffizienz/Kraft_Waerme_Kopplung/Mini_KWK/mini_kwk_node.html
        
        if options["Bafa_chp"]:   
            
            model.addConstr(power_chp >= sum(chp_powerstep[i] for i in range(1,5)), 
                            name = "chp_sum_powerstep")

            model.addConstr(chp_powerstep[1] == x[dev],  name = "chp_powerstep1")
            model.addConstr(chp_powerstep[2] <= 3,  name = "chp_powerstep1")
            model.addConstr(chp_powerstep[3] <= 6,  name = "chp_powerstep2")
            model.addConstr(chp_powerstep[4] <= 10, name = "chp_powerstep3")          
            
            # Bounds for Basic CHP Subsidy                                   
            model.addConstr(sub_chp_basic <= 3500 * x[dev], name = "chp_sub_basic_ub")
            model.addConstr(sub_chp_basic <= 1900 * chp_powerstep[1] + 
                                              100 * chp_powerstep[2] + 
                                               30 * chp_powerstep[3] + 
                                               10 * chp_powerstep[4],
                                            name = "chp_sub_basic_calcutation")     
           
            # Calculate annual subsidy value
            model.addConstr(sub["bafa"] == eco["crf"] * 
                                            (1 + 0.25 * devs[dev]["therm_eff_bonus"] 
                                               + 0.6  * devs[dev]["power_eff_bonus"]) *	
                                             sub_chp_basic,
                                             name = "chp_bafa_total_calculation")           
      
        else:
            model.addConstr(sub["bafa"] == 0)
                      
        #KWKG for CHP 
        if options["KWKG"]:            
            
            # Divide into micro and bigger sized chp units
            p_micro = 2.0 # kW
            
            model.addConstr(x[dev] >= sum(b_kwkg[n] 
                                      for n in b_kwkg.keys()))
                        
            model.addConstr(p_micro  >= lin_chp_kwkg * 
                                        devs[dev]["sigma"],
                                        name = "kwkg_micro")
                            
            # Linearization:
            model.addConstr(lin_chp_kwkg <= devs[dev]["Q_nom_max"] * 
                                            b_kwkg["micro"])  
            
            model.addConstr(capacity[dev] - lin_chp_kwkg >= 0)  

            model.addConstr(capacity[dev] - lin_chp_kwkg <= devs[dev]["Q_nom_max"] * 
                                                            (1-b_kwkg["micro"]))                    
                            
            model.addConstr(sub["micro"]  <= M * b_kwkg["micro"],
                            name = "b_kwkg_micro_var")
                        
            # Subsidies for micro chp units
            # For micro chp units either lump or variable subsidies (maximum) 
            # according to http://www.fico.com/en/node/8140?file=5125 p. 7
            
            max_lump = (eco["crf"] * sub_par["kwkg"]["t_50"] * 
                        sub_par["kwkg"]["lump"] * p_micro)
                       
            max_var  = (eco["crf"] * eco["b"]["eex"] * 8760 * 
                        sub_par["kwkg"]["sell_50"] * p_micro)
            
            model.addConstr(sub["micro_lump"] <= eco["crf"] * 
                                                 sub_par["kwkg"]["t_50"] * 
                                                 sub_par["kwkg"]["lump"] * 
                                                 power_chp,
                                                 name="sub_chp_micro_lump")           
            
            model.addConstr(sub["micro_var"]  <= eco["crf"] * eco["b"]["eex"] * dt *
                                                 sum(clustered["weights"][d] * 
                                                 sum(sub_par["kwkg"]["self_50"] * 
                                                 (p_use[dev,d,t] + p_hp[dev,d,t]) + 
                                                 sub_par["kwkg"]["sell_50"] * 
                                                 p_sell[dev,d,t] 
                                                 for t in time_steps) 
                                                 for d in days),
                                                 name="sub_chp_micro_var")                                 
                                        
            model.addConstr(sub["micro"] >= sub["micro_lump"])
            
            model.addConstr(sub["micro"] >= sub["micro_var"])
            
            model.addConstr(sub["micro"] <= sub["micro_lump"] + 
                                            max_lump * (1 - x_chp["lump","micro"]))
                                            
            model.addConstr(sub["micro"] <= sub["micro_var"]  + 
                                            max_var * (1 - x_chp["var","micro"]))
                                            
            model.addConstr(x_chp["lump","micro"] + x_chp["var","micro"] == 1)      
                                                 
            # Subsidies for bigger sized chp units        
            # Differentiation of funding rate depending on installed CHP-power                  
            chp_powerstages = ("50", "100", "250", "2000", "10000")
                                          
            model.addConstr(power_chp <= sum(float(n) * b_kwkg[n] 
                                         for n in chp_powerstages)) 
            
            for n in chp_powerstages:
                model.addConstr(1.0 / M * p_sell_chp[n] <= M * b_kwkg[n])

            for n in ("50", "100"):
                model.addConstr(1.0 / M * p_use_chp[n]   <= M * b_kwkg[n]) 
             
            model.addConstr(1.0 / M * p_use_chp["10000"] <= M * (b_kwkg["250"] + 
                                                                b_kwkg["2000"] + 
                                                                b_kwkg["10000"]))

            # Different funding rates for sold and consumed electricity                     
            model.addConstr(p_chp_total["use"] == sum(p_use_chp[n] 
                                                  for n in p_use_chp.keys()))

            model.addConstr(p_chp_total["sell"] == sum(p_sell_chp[n] 
                                                   for n in chp_powerstages))

            model.addConstr(sub["large"] <= eco["crf"] * eco["b"]["eex"] * 
                                            (sum(p_sell_chp[n] * 
                                             sub_par["kwkg"]["sell_"+n]
                                             for n in chp_powerstages) + 
                                             sum(p_use_chp[n] * 
                                             sub_par["kwkg"]["self_"+n] 
                                             for n in ("50", "100"))),
                                             name="Sub_var_chp")  

            # Restriction because of annual operating hours
            # The KWKG supports just 60.000 or 30.000 full load hours (depending of elec power)
            # Noz possible to differentiate between sold and consumed power in this context
            # "average_value" is an estimated value.
            model.addConstr(sub["large"] <= eco["crf"] * eco["b"]["eex"] / eco["t_calc"] * 
                                            (lin_kwkg["50"] * sub_par["kwkg"]["t_50"] * 
                                            sub_par["kwkg"]["ave_50"]   +
                                            sum(lin_kwkg[n] * sub_par["kwkg"]["t_100"] * 
                                            sub_par["kwkg"]["ave_"+n] 
                                            for n in ("100", "250", "2000", "10000"))),
                                            name = "Sub_chp_average")
            # Linearization
            model.addConstr(power_chp >= sum(lin_kwkg[n] 
                                         for n in chp_powerstages))
                        
            for n in chp_powerstages: 
                model.addConstr(lin_kwkg[n] <= b_kwkg[n] * float(n))
            
        else:
            model.addConstr(sub["micro"] == 0)
            model.addConstr(sub["large"] == 0)
                     
        #%% KfW-Subsidy for Battery
        
        dev = "bat"
        if options["KfW"]:
            model.addConstr(subsidy[dev] <= eco["crf"] * sub_par["bat"]["sub_bat_max"] * 
                                            devs["pv"]["p_nom"] * lin_bat_sub * 
                                            sub_par["bat"]["share_max"],
                                            name="Bat_Subsidies_1")
            
            model.addConstr(subsidy[dev] <= (c_inv["pv"] + c_inv["bat"] - eco["crf"] * 
                                             sub_par["bat"]["sub_bat"] * devs["pv"]["p_nom"] * 
                                             lin_bat_sub) * sub_par["bat"]["share_max"],
                                             name="Bat_Subsidies_2")
            
            # linearization contraints because of pv_pow * x_bat
            model.addConstr(lin_bat_sub <= A_max * x[dev])
            model.addConstr(area["pv"] - lin_bat_sub >= 0)
            model.addConstr(area["pv"] - lin_bat_sub <= (1 - x[dev]) * A_max)
        
        else:
            model.addConstr(subsidy[dev] == 0)
            
        # Bestrict sold electricity from PV to 70% of the rated power without
        # battery storage and 50% with storage system       
        
        dev = "pv"
        # linearization constraints
        model.addConstr(lin_pv_bat <= A_max * x["bat"])
        model.addConstr(lin_pv_bat >= devs[dev]["area_min"] * x["bat"])
        model.addConstr(area[dev] - lin_pv_bat >= 0)
        model.addConstr(area[dev] - lin_pv_bat <= (1 - x["bat"]) * A_max)
        
        if options["EEG"] and options["KfW"]:
            # With EEG and KfW --> cap PV exports at 70 or 50%
            for d in days:
                for t in time_steps:
                    model.addConstr(p_sell[dev,d,t] <= 0.7 * devs[dev]["p_nom"] * (area[dev] - lin_pv_bat) +
                                                       0.5 * devs[dev]["p_nom"] * lin_pv_bat,
                                                       name='restrict sold elec')
        
        elif options["EEG"] and not options["KfW"]:
            # No KfW support --> always cap PV exports at 70%
            for d in days:
                for t in time_steps:
                    model.addConstr(p_sell[dev,d,t] <= 0.7 * devs[dev]["p_nom"] * (area[dev] - lin_pv_bat) + 
                                                       0.7 * devs[dev]["p_nom"] * lin_pv_bat,
                                                       name='restrict sold elec')
        
        elif not options["EEG"] and options["KfW"]:
            # No EEG, but with KfW support --> cap PV exports at 50% with BAT, and no limit without BAT
            for d in days:
                for t in time_steps:
                    model.addConstr(p_sell[dev,d,t] <= 1.0 * devs[dev]["p_nom"] * (area[dev] - lin_pv_bat) +
                                                       0.5 * devs[dev]["p_nom"] * lin_pv_bat[n],
                                                       name='restrict sold elec')
        
        else:
            # Neither EEG nor KfW --> do not limit PV exports
            for d in days:
                for t in time_steps:
                    model.addConstr(p_sell[dev,d,t] <= 1.0 * devs[dev]["p_nom"] * area[dev],
                                                       name='restrict sold elec')    
            
        #%% MAP-Subsidy for STC  
                   
        #The "Marktanreizprogramm" MAP is a subsidy-program for STC by BAFA
        #The prorgam has three parts: basic, innovation and additional subsidy
        #Further Information:
        #http://www.bafa.de/DE/Energie/Heizen_mit_Erneuerbaren_Energien/Solarthermie/solarthermie_node.html 
        
        dev = "stc"                    
        if options["Bafa_stc"]:            
            
            #It is only possible to get either basic_fix, basic_var or inno
            model.addConstr(b_bafa_stc["basic_fix"] + 
                            b_bafa_stc["basic_var"] + 
                            b_bafa_stc["inno"] <= x["stc"],                          
                            name = "stc_bafa_x_stc")
            
            model.addConstr(b_bafa_stc["basic_fix"] + b_bafa_stc["basic_var"] + 
                            b_bafa_stc["inno"] <= x["tes"],
                            name = "stc_bafa_x_tes")
            
            #Thermal storage restriction
            #At least 50 l/m² are necessary
            model.addConstr(volume * 1000 >= sub_par[dev]["min_storage"] * 
                                             lin_sub_stc, 
                                             name = "stc_bafa_tes_restr")
            
            # Linearization for storage constraint
            model.addConstr(lin_sub_stc <= A_max * (b_bafa_stc["basic_fix"] + 
                                                    b_bafa_stc["basic_var"] + 
                                                    b_bafa_stc["inno"]),
                                                    name = "stc_bafa_lin_1") 
            
            model.addConstr(area[dev] - lin_sub_stc >= 0, name = "stc_bafa_lin_2")  
            
            model.addConstr(area[dev] - lin_sub_stc <=  A_max * (1 - 
                                                    (b_bafa_stc["basic_fix"] + 
                                                     b_bafa_stc["basic_var"] + 
                                                     b_bafa_stc["inno"])),
                                                     name = "stc_bafa_lin_3")         
                                                    
            #Basic program
            #Area restriction   
            #At least 9 m² are necessary
            model.addConstr(area[dev] / sub_par[dev]["basic_area_min"] >= 
                                                    (b_bafa_stc["basic_var"] + 
                                                     b_bafa_stc["basic_fix"]),
                                                     name = "stc_bafa_basic_area_restr")   

            #Just for old buildings
            model.addConstr(sub_bafa_stc["basic_fix"] <= sub_par[dev]["basic_fix"] * 
                                                         b_bafa_stc["basic_fix"] * 
                                                         alpha,
                                                         name = "stc_bafa_basic_fix")
            
            model.addConstr(sub_bafa_stc["basic_var"] <=  sub_par[dev]["basic_var"] * 
                                                          area[dev],
                                                          name = "stc_bafa_basic_var")   
                 
            model.addConstr(sub_bafa_stc["basic_var"] <= sub_par[dev]["basic_var"] * 
                                                         sub_par[dev]["basic_area_max"] * 
                                                         b_bafa_stc["basic_var"] * 
                                                         alpha,
                                                         name = "stc_bafa_basic_ub")                                 
            
            #Innovation prorgram
            #Annual gain restriction
            #At least 300kWh/m2 are necessary
            model.addConstr(float(devs[dev]["annual_gain"]) >= sub_par[dev]["annual_gain"] * 
                                                               b_bafa_stc["inno"],
                                                               name = "stc_bafa_gain_restr")            
            
            #Area restriction
            #At least 20 m² are necessary           
            model.addConstr(area[dev] / 
                            sub_par[dev]["inno_area_min"] >= b_bafa_stc["inno"],
                                             name = "stc_bafa_inno_area_restr")        
            
            #Program only available for MFH
            model.addConstr(sub_bafa_stc["inno"] <= (sub_par["stc"]["inno_new_b"] + 
                                                     sub_par["stc"]["inno_existing_b"] * 
                                                     alpha) * area[dev] * MFH,
                                                     name = "stc_bafa_inno_var")
            
            model.addConstr(sub_bafa_stc["inno"] <= (sub_par["stc"]["inno_new_b"] + 
                                                     sub_par["stc"]["inno_existing_b"] * 
                                                     alpha) * b_bafa_stc["inno"] * MFH *                                                     
                                                     sub_par["stc"]["inno_area_max"],
                                                     name = "stc_bafa_inno_ub")            
            
            #Additional program
            #STC in combination with HP is necessary
            model.addConstr(x["stc"] >= b_bafa_stc["add1"], name = "stc_bafa_add_1")
                            
            model.addConstr(x["hp_air"] + x["hp_geo"]  >= b_bafa_stc["add1"],
                                                          name = "stc_bafa_add_2")
            
            #Additional program only available if basic or inno program available          
            model.addConstr(b_bafa_stc["add1"] <= (b_bafa_stc["basic_fix"] + 
                                                   b_bafa_stc["basic_var"] +
                                                   b_bafa_stc["inno"]),
                                                   name = "stc_bafa_add_3")
                                                   
            #Additional Building-Efficiency-Subsidy
            model.addConstr(sub_bafa_stc["build_eff"] <= M * b_sub_restruc["kfw_eff_55"], 
                                                            name = "stc_bafa_b_e_1")
           
            model.addConstr(sub_bafa_stc["build_eff"] <= sub_par[dev]["build_eff"] * 
                                                        (sub_bafa_stc["inno"] + 
                                                         sub_bafa_stc["basic_fix"] +
                                                         sub_bafa_stc["basic_var"]), 
                                                         name = "stc_bafa_b_e_2")                                       
           
            #Calculation of annaul subsid value      
            model.addConstr(subsidy[dev] == eco["crf"] * (sub_bafa_stc["basic_fix"] + 
                                                          sub_bafa_stc["basic_var"] + 
                                                          sub_bafa_stc["inno"] + 
                                                          b_bafa_stc["add1"] * 
                                                          sub_par[dev]["stc_hp_combi"] +
                                                          sub_bafa_stc["build_eff"]),
                                                          name = "stc_bafa_total_value")
        
        else: 
            model.addConstr(subsidy[dev] == 0)

        #%% MAP-Subsidy for HP  
                   
        #The "Marktanreizprogramm" MAP is a subsidy-program for HP by BAFA
        #The prorgam has three parts: basic, innovation and additional subsidy
        #Further Information:
        #http://www.bafa.de/DE/Energie/Heizen_mit_Erneuerbaren_Energien/Waermepumpen/waermepumpen_node.html
        
        if options["Bafa_hp"]:
            for dev in ("hp_air", "hp_geo"):
                
                model.addConstr(energy_hp[dev]["total_heat"] == dt * 
                                                  sum(clustered["weights"][d] * 
                                                  sum(heat[dev,d,t] 
                                                  for t in time_steps) 
                                                  for d in days))
                                                      
                model.addConstr(energy_hp[dev]["total_power"] == dt * 
                                                  sum(clustered["weights"][d] * 
                                                  sum(power[dev,d,t] 
                                                  for t in time_steps) 
                                                  for d in days))
                        
                #It is only possible to get either basic_fix, basic_var, 
                #inno_fix or inno_var
                model.addConstr(b_bafa_hp[dev]["basic_fix"] + 
                                b_bafa_hp[dev]["basic_var"] + 
                                b_bafa_hp[dev]["inno_fix"] + 
                                b_bafa_hp[dev]["inno_var"] <= x[dev],
                                name = "hp_bafa_x_hp")      
                
                #Basic program
                #For the basic_program  the seasonal coefficient of performance  
                #has to at least 3.5                 
                model.addConstr(energy_hp[dev]["total_heat"] / M >= 
                                sub_par[dev]["basic_scop"] / M * 
                                energy_hp[dev]["total_power"] - M * 
                                (1 - (b_bafa_hp[dev]["basic_fix"] + 
                                      b_bafa_hp[dev]["basic_var"])))                
                                            
                model.addConstr(sub_bafa_hp[dev]["basic"] <= ((sub_par[dev]["basic_fix"] + 
                                                               sub_par[dev]["basic_fix_pc"] * 
                                                               devs[dev]["pc"]) *
                                                               b_bafa_hp[dev]["basic_fix"] + 
                                                               sub_par[dev]["basic_var"] * 
                                                               lin_hp_sub_basic[dev]),
                                                               name = "hp_bafa_basic_sub")                
                
                model.addConstr(sub_bafa_hp[dev]["basic"] <= sub_par[dev]["basic_var"] *
                                                             sub_par[dev]["max_cap"] * alpha * 
                                                             (b_bafa_hp[dev]["basic_var"] + 
                                                              b_bafa_hp[dev]["basic_fix"]),
                                                             name = "hp_bafa_basic_sub_ub")
                
                # Linearization because of capacity[dev] * b_bafa_hp["basic_var"]
                model.addConstr(lin_hp_sub_basic[dev] <= devs[dev]["Q_nom_max"] * 
                                                         b_bafa_hp[dev]["basic_var"],
                                                         name = "hp_bafa_lin_basic_1")
                
                model.addConstr(capacity[dev] - lin_hp_sub_basic[dev] >= 0,
                                          name = "hp_bafa_lin_basic_2")
                
                model.addConstr(capacity[dev] - lin_hp_sub_basic[dev] <= (1 - b_bafa_hp[dev]["basic_var"]) *
                                                                          devs[dev]["Q_nom_max"],
                                                                          name = "hp_bafa_lin_basic_3")  
               
                #Innovation program
                #For the basic_program the seasonal coefficient of performance  
                #has to at least 4.5 
                model.addConstr(energy_hp[dev]["total_heat"] / M >= 
                                               sub_par[dev]["inno_scop"] / M * 
                                               energy_hp[dev]["total_power"] - M * 
                                               (1 - (b_bafa_hp[dev]["inno_fix"] + 
                                                     b_bafa_hp[dev]["inno_var"])))            
        
                model.addConstr(sub_bafa_hp[dev]["inno"] <= ((sub_par[dev]["inno_fix"] + 
                                                              sub_par[dev]["inno_fix_pc"] * 
                                                              devs[dev]["pc"]) * alpha +
                                                             (sub_par[dev]["basic_fix"] + 
                                                              sub_par[dev]["basic_fix_pc"] * 
                                                              devs[dev]["pc"]) * (1-alpha)) +
                                                              b_bafa_hp[dev]["inno_fix"] +
                                                             (sub_par[dev]["basic_var"] +
                                                              sub_par[dev]["inno_var"] * alpha) * 
                                                              lin_hp_sub_inno[dev],
                                                              name = "hp_bafa_inno_sub")
                
                model.addConstr(sub_bafa_hp[dev]["inno"] <= (sub_par[dev]["basic_var"] *
                                                             sub_par[dev]["max_cap"] +
                                                             sub_par[dev]["inno_var"] *
                                                             sub_par[dev]["max_cap"] * alpha) * 
                                                            (b_bafa_hp[dev]["inno_var"] + 
                                                             b_bafa_hp[dev]["inno_fix"]),
                                                             name = "hp_bafa_inno_sub_ub") 
                
                # Linearization because of capacity[dev] * b_bafa_hp["inno_var"]
                model.addConstr(lin_hp_sub_inno[dev] <= devs[dev]["Q_nom_max"] * 
                                                        b_bafa_hp[dev]["inno_var"],
                                                        name = "hp_bafa_lin_inno_1")
                
                model.addConstr(capacity[dev] - lin_hp_sub_inno[dev] >= 0,
                                                    name = "hp_bafa_lin_inno_2")
                
                model.addConstr(capacity[dev] - lin_hp_sub_inno[dev] <= (1 - b_bafa_hp[dev]["inno_var"]) * 
                                                                        devs[dev]["Q_nom_max"],
                                                                        name = "hp_bafa_lin_inno_3")
                
                #Additional program
                #Only available if HP is "Smart-Grid-Ready"
                #Only available if basic- or inno-program is available
                #Only available if storage has at least 30l/kW
                model.addConstr(b_bafa_hp[dev]["add1"] <= devs[dev]["Smart_Grid"] *
                                                         (b_bafa_hp[dev]["basic_fix"] + 
                                                          b_bafa_hp[dev]["basic_var"] + 
                                                          b_bafa_hp[dev]["inno_fix"] + 
                                                          b_bafa_hp[dev]["inno_var"]),
                                                          name = "hp_bafa_add")
                                                          
                #Thermal storage restriction
                model.addConstr(volume * 1000 >= sub_par[dev]["stor_restr"] * 
                                                 lin_hp_sub_add[dev], 
                                                 name = "hp_bafa_tes_restr_"+dev)    
            
                # Linearization for storage constraint
                model.addConstr(lin_hp_sub_add[dev] <= M * b_bafa_hp[dev]["add1"],
                                               name = "hp_bafa_lin_add_1_"+dev) 
            
                model.addConstr(capacity[dev] - lin_hp_sub_add[dev] >= 0,
                                               name = "hp_bafa_lin_add_2_"+dev)  
            
                model.addConstr(capacity[dev] - lin_hp_sub_add[dev] <=  M * 
                                                  (1 - b_bafa_hp[dev]["add1"]),
                                              name =  "hp_bafa_lin_add_3_"+dev)
                                              
                #Additional Building-Efficiency-Subsidy
                model.addConstr(sub_bafa_hp[dev]["build_eff"] <= M * b_sub_restruc["kfw_eff_55"], 
                                                            name = dev+"_bafa_b_e_1")
           
                model.addConstr(sub_bafa_hp[dev]["build_eff"] <= sub_par[dev]["build_eff"] * 
                                                                (sub_bafa_hp[dev]["inno"] + 
                                                                 sub_bafa_hp[dev]["basic"]), 
                                                                 name = dev+"_bafa_b_e_2")
                
                #Calculation of annaul subsidy value  
                model.addConstr(subsidy[dev] == eco["crf"] * (sub_bafa_hp[dev]["basic"] + 
                                                              sub_bafa_hp[dev]["inno"] + 
                                                              b_bafa_hp[dev]["add1"] * 
                                                              sub_par[dev]["smart_grid"]+
                                                              sub_bafa_hp[dev]["build_eff"]),
                                                              name = "hp_bafa_total_value")
        
        else: 
            for dev in ("hp_air", "hp_geo"):            
                model.addConstr(subsidy[dev] == 0)

        #%% MAP-Subsidy for Pellet
                   
        #The "Marktanreizprogramm" MAP is a subsidy-program for Pellet heatings by BAFA
        #The prorgam has three parts: basic, innovation and additional subsidy
        #Further Information:
        #http://www.bafa.de/DE/Energie/Heizen_mit_Erneuerbaren_Energien/Biomasse/biomasse_node.html
        
        dev = "pellet"  
        if options["Bafa_pellet"]:            
            
            #It is only possible to get either basic_storage, basic_fix, 
            #basic_var, inno_storage or inno_fix            
            model.addConstr(b_bafa_pellet["basic_fix"] + 
                            b_bafa_pellet["basic_storage"] +
                            b_bafa_pellet["basic_var"] + 
                            b_bafa_pellet["inno_fix"] +
                            b_bafa_pellet["inno_storage"] <= x["pellet"],
                                                             name = "pellet_bafa_x_pellet")

            #Capacity restriction: At least 5kW are necessary
            model.addConstr(b_bafa_pellet["basic_fix"] + 
                            b_bafa_pellet["basic_storage"] +
                            b_bafa_pellet["basic_var"] + 
                            b_bafa_pellet["inno_fix"] +
                            b_bafa_pellet["inno_storage"] <= capacity[dev] / 
                                                             sub_par[dev]["min_cap"],
                                                             name = "pellet_bafa_cap_restr")   

            #Thermal storage restriction: At least 30 l/kW are necessary
            model.addConstr(volume * 1000 >= sub_par[dev]["stor_restr"] * 
                                             lin_sub_pellet["storage"], 
                                             name = "stc_bafa_tes_restr")
            
            # Linearization for storage constraint
            model.addConstr(lin_sub_pellet["storage"] <= devs[dev]["Q_nom_max"] * 
                                                        (b_bafa_pellet["basic_storage"] + 
                                                         b_bafa_pellet["inno_storage"]),
                                                         name = "pellet_bafa_lin_storage_1") 
            
            model.addConstr(capacity[dev] >= lin_sub_pellet["storage"], 
                                             name = "pellet_bafa_lin_storage_2")  
            
            model.addConstr(capacity[dev] <=lin_sub_pellet["storage"] + 
                                            devs[dev]["Q_nom_max"] * (1 - 
                                           (b_bafa_pellet["basic_storage"] + 
                                            b_bafa_pellet["inno_storage"])),
                                            name = "pellet_bafa_lin_storage_3")        
                                                            
            # Linearization because of capacity[dev] * b_bafa_pellet["basic_var"]
            model.addConstr(lin_sub_pellet["basic"] <= devs[dev]["Q_nom_max"] * 
                                                       b_bafa_pellet["basic_var"],
                                                       name = "pellet_bafa_lin_basic_1")
            
            model.addConstr(capacity[dev] >= lin_sub_pellet["basic"], 
                                             name = "pellet_bafa_lin_basic_2")
            
            model.addConstr(capacity[dev] <= lin_sub_pellet["basic"] + 
                                            (1 - b_bafa_pellet["basic_var"]) *
                                             devs[dev]["Q_nom_max"],
                                             name = "pellet_bafa_lin_basic_3")  

            #Basic-Subsidy: Just for existing buildings
            model.addConstr(sub_bafa_pellet["basic"] <= (sub_par[dev]["basic_fix"] * 
                                                         b_bafa_pellet["basic_fix"] +
                                                         sub_par[dev]["basic_storage"] * 
                                                         b_bafa_pellet["basic_storage"] +
                                                         sub_par[dev]["basic_var"] * 
                                                         lin_sub_pellet["basic"]) *
                                                         alpha,
                                                         name = "pellet_bafa_basic")
                                                         
            #Innovation-Subsidy
            model.addConstr(sub_bafa_pellet["inno"] <=  devs[dev]["inno_ability"] *            
                                                         (b_bafa_pellet["inno_fix"] *                                                         
                                                          (sub_par["pellet"]["inno_fix_new"] + 
                                                           sub_par["pellet"]["inno_fix_old"] * 
                                                           alpha) +
                                                          b_bafa_pellet["inno_storage"] *                                                         
                                                          (sub_par["pellet"]["inno_fix_new_stor"] + 
                                                           sub_par["pellet"]["inno_fix_old_stor"] * 
                                                           alpha)), name = "pellet_bafa_inno")
            
            #Additional program
            #STC in combination with Pellet is necessary
            model.addConstr(x["stc"] >= b_bafa_pellet["add1"], 
                                        name = "pellet_bafa_add_1")
                            
            model.addConstr(x["pellet"] >= b_bafa_pellet["add1"], 
                                           name = "pellet_bafa_add_2")
            
            #Additional program only available if basic or inno program available          
            model.addConstr(b_bafa_pellet["add1"] <= (b_bafa_pellet["basic_fix"] + 
                                                      b_bafa_pellet["basic_storage"] +
                                                      b_bafa_pellet["basic_var"] + 
                                                      b_bafa_pellet["inno_fix"] +
                                                      b_bafa_pellet["inno_storage"]),
                                                      name = "pellet_bafa_add_3")
           
            #Additional Building-Efficiency-Subsidy
            model.addConstr(sub_bafa_pellet["build_eff"] <= M * b_sub_restruc["kfw_eff_55"], 
                                                            name = "pellet_bafa_b_e_1")
           
            model.addConstr(sub_bafa_pellet["build_eff"] <= sub_par[dev]["build_eff"] * 
                                                           (sub_bafa_pellet["inno"] + 
                                                            sub_bafa_pellet["basic"]), 
                                                            name = "pellet_bafa_b_e_2")
            
            #Calculation of annaul subsid value      
            model.addConstr(subsidy[dev] == eco["crf"] * (sub_bafa_pellet["basic"] + 
                                                          sub_bafa_pellet["inno"] +                                       
                                                          b_bafa_pellet["add1"] * 
                                                          sub_par[dev]["stc_pellet_combi"]) + 
                                                          sub_bafa_pellet["build_eff"],
                                                          name = "pellet_bafa_total_value")
        
        else: 
            model.addConstr(subsidy[dev] == 0)
                                    
        #%% Restructuring measures: It possible to select different restructuring scenarios for the four aspects:
        # Windows, Walls, Rooftop and Ground. For every sector there is also free possibility with a the highest U-value

        #It is only possible to choose one scenrio per shellpart
        for dev in building_components:    
            model.addConstr(sum(x_restruc[dev,n] for n in restruc_scenarios) == 1)
         
        # Investment costs for restruturing measures
        # For Rooftop, GroundFloor and Outerwall the costs are calculated in 
        # relation to the thickness of the additional insulation in comparision
        # to the standard-scenario. The standard scenario is free of cost. 
        for dev in ("Rooftop", "GroundFloor", "OuterWall"):
            model.addConstr(c_inv[dev] == building["dimensions"]["Area"] * 
                                          (1-shell_eco[dev]["rval"]) *
                                          eco["crf"] * building["dimensions"][dev] *
                                          (sum(x_restruc[dev,n] * (shell_eco[dev]["c_const"] + 
                                           shell_eco[dev]["c_var"] * 100 *
                                           building["U-values"][n][dev]["thick_insu_add"])                                                                     
                                           for n in ("retrofit", "adv_retr")) + 
                                           x_restruc[dev,"standard"] * 0),
                                           name = "C_inv_restruc_"+dev)
             
        # For Windows the costs are calculated in relation to the U-value of the
        # chosen Window. The standard scenario is free of cost.
        dev = "Window"
        model.addConstr(c_inv[dev] == building["dimensions"]["Area"] * 
                                      (1-shell_eco[dev]["rval"]) *
                                      eco["crf"] * building["dimensions"][dev] *
                                      (sum(x_restruc[dev,n] * (shell_eco[dev]["c_const"] + 
                                       shell_eco[dev]["c_var"] * 
                                       building["U-values"][n][dev]["U-Value"])                                                                     
                                       for n in ("retrofit", "adv_retr")) + 
                                       x_restruc[dev,"standard"] * 0),
                                       name = "C_inv_restruc_"+dev)
                                          
        
        #%%Calculation of space heating in accordance with DIN V 4108
        # For every timestep die heating demand is calculated in considering of 
        # the transmissionen and ventilation losses as well as internal and solar gains
        for d in days:
            for t in time_steps:
                 model.addConstr(heat_mod[d,t] >= Q_Ht[d,t] - Q_s[d,t] - clustered["int_gains"][d,t]) 
              
        #Transmission losses for windows, wall, rooftop and ground incl. surcharge for thermal bridges 
        #as a function of the selected u-values and the temperature difference:
        
        #Correction factors for components that have no contact with the ambient ait
        Fx = {}
        Fx["Window"] = 1
        Fx["OuterWall"] = 1 
        Fx["GroundFloor"] = 0.6
        Fx["Rooftop"] = 1
        
        model.addConstr(H_t == building["dimensions"]["Area"] * 
                               (sum(building["dimensions"][dev] * Fx[dev] * 
                                sum(x_restruc[dev,n] * building["U-values"][n][dev]["U-Value"] 
                                for n in restruc_scenarios) for dev in building_components)
                                + 0.05 * sum(building["dimensions"][dev] for dev in building_components)))
                                      
        for d in days:
            for t in time_steps:
                model.addConstr(Q_Ht[d,t] == clustered["delta_T"][d,t] / 1000 * H_t)                                     
                                           
        #Solar Gains for all windowareas as a function of the solar radiation 
        #of the respective direction:
                                            
        #Correction factors in accordance with DIN V 4108 and EnEV                                    
        F_solar = 0.9 * 1 * 0.7 * 0.85
        
        # In Real the g-value depends on the chosen Window. 
        # Possibility to differentiate in the future 
        g_value = 0.7                       
        
        for d in days:
            for t in time_steps:
                model.addConstr(Q_s[d,t] == F_solar * g_value *     
                                            (building["dimensions"]["Window_east"] * 
                                             clustered["solar_e"][d,t] + 
                                             building["dimensions"]["Window_west"] * 
                                             clustered["solar_w"][d,t] +
                                             building["dimensions"]["Window_north"] * 
                                             clustered["solar_n"][d,t] + 
                                             building["dimensions"]["Window_south"] * 
                                             clustered["solar_s"][d,t]))
                                                                                                                          
        #%%KfW-Subsidies for individual measures
                                                                                                                                  
        #Subsidy is only available if chosen restruction scenario satisfies the necessary Standard 
        for dev in building_components:                                                                                                            
            model.addConstr(sum(x_restruc[dev,n] * building["U-values"][n][dev]["U-Value"]
                            for n in restruc_scenarios) <= 
                            sub_par["building"]["u_value"][dev] + (1.0 - b_sub_restruc[dev]) * M)                                                                                                         
             
        #5000€ grant for every individual measure but max. 10% of the respective investment                                                                                                       
        if options["kfw_single_mea"]:
            for dev in building_components:                 
                model.addConstr(subsidy[dev] <= eco["crf"] * 
                                                (1.0 - shell_eco[dev]["rval"]) * 
                                                b_sub_restruc[dev] * sub_par["building"]["grant"]["ind_mea"])   
                
                model.addConstr(subsidy[dev] <= sub_par["building"]["share_max"]["ind_mea"] * c_inv[dev])        

        else:                              
            for dev in building_components:  
                model.addConstr(subsidy[dev] == 0)    

        #%%KfW-Subsides for Efficient Buildings (KfW-Effizienzhaeuser)
       
        #Calculation of the Primary Energy demand in accordance with DIN 4108
        #Just the Transmission losses are variable with regard to the restruction
        #measures. Ventilation losses, internal and solar gains are determined 
        #with a static method (such as for the reference building)
        
        #There are different heating concepts that are regaderd:       
        model.addConstr(sum(heating_concept[n] for n in heating_concept.keys()) == 1)
        
        for n in heating_concept.keys():
            model.addConstr(heating_concept[n]  >= sum(ep_table[dev][n] * x[dev] +
                                                       (1 - ep_table[dev][n]) * (1 - x[dev]) 
                                                       for dev in ("boiler", "chp", "eh", "hp_air", 
                                                                   "hp_geo","pellet","stc")) + 
                                                        ep_table["TVL35"][n] * b_TVL["35"] +
                                                       (1 - ep_table["TVL35"][n]) * (1 - b_TVL["35"]) - 7) 
                                                                              
        model.addConstr(x["boiler"] + x["eh"] <= 1)
        model.addConstr(x["chp"] + x["eh"] <= 1)
        model.addConstr(x["chp"] + x["stc"] <= 1)
        model.addConstr(x["eh"] <= x["hp_air"] + x ["hp_geo"])
        model.addConstr(x["pellet"] + x["hp_geo"] + x["hp_air"] <= 1)

        #Linearization: Product of H_t (continuous) and heating_concept (binary)               
        for n in heating_concept.keys():                
            model.addConstr(lin_H_t[n] <= M * heating_concept[n])                                         
            
            model.addConstr(H_t - lin_H_t[n] >= 0)        
            
            model.addConstr(H_t - lin_H_t[n] <= M * (1 - heating_concept[n]))
                

        #Determination of the primary energy demand 
        model.addConstr(Q_p_DIN == 1/1000 * 
                                    (ref_building["f_ql"] * sum(ep_table["ep"][n] * lin_H_t[n] for n in lin_H_t.keys()) +  
                                     ref_building["H_v"] * ref_building["f_ql"] + ref_building["Q_tw"] -      
                                     ref_building["eta"] * (ref_building["Q_i"] + ref_building["Q_s"]) * 
                                     sum(heating_concept[n] * ep_table["ep"][n] for n in heating_concept.keys())))

                          
        #There are two restrictions for subsidies for kfw-efficiency-buildings
        #Specific transmission losses and primary energy demand have to be lower 
        #than the respective values for an reference building
        #The "efficiency-factor" differentiates between the different levels of
        #kfw-efficiency buildings
        
        total_shell = (building["dimensions"]["Area"] * 
                       sum(building["dimensions"][n] 
                       for n in building_components))
        
        for dev in kfw_standards:
            model.addConstr(H_t / total_shell <= 
                            sub_par["building"]["eff_fact_H"][dev] * 
                            ref_building["H_t_spec"] + 
                            (1.0 - b_sub_restruc[dev]) * M) 
                                 
            model.addConstr(Q_p_DIN <= sub_par["building"]["eff_fact_Q"][dev] * 
                                       ref_building["Q_p"] + 
                                       (1.0 - b_sub_restruc[dev]) * M)
                                                                        
        #Just one Subsidy-Package is available
        model.addConstr(sum(b_sub_restruc[n] for n in kfw_standards) <= 1.0)
        
        #Either subsidies for individual measurers OR for efficiency buildings
        for dev in building_components:
            model.addConstr(sum(b_sub_restruc[n] for n in kfw_standards) + b_sub_restruc[dev]<= 1.0)                                        
               
        if options["kfw_eff_buildings"]:
            for dev in kfw_standards:
                model.addConstr(subsidy[dev] <= eco["crf"] * 
                                                (1 - shell_eco["Window"]["rval"]) * 
                                                b_sub_restruc[dev] * sub_par["building"]["grant"][dev])
                                                
                model.addConstr(subsidy[dev] <= sub_par["building"]["share_max"][dev] * sum(c_inv[n] for n in building_components))     

        else:                              
            for dev in kfw_standards:
                model.addConstr(subsidy[dev] == 0)                         
        
#%% Define Scenarios 
        
        model.addConstr(0.001 * emission <= max_emi)       

        model.addConstr(c_total <= max_cost)
                
        if options["scenario"] == "free":
            pass
        
        elif options ["scenario"] == "example":
#            model.addConstr(x["hp_geo"] == 1)
            model.addConstr(x["chp"] == 1)
#            model.addConstr(heating_concept[1] == 1)
            for i in building_components:
                model.addConstr(x_restruc[i,"standard"] == 1)
#            model.addConstr(x_restruc["OuterWall","standard"] == 1)
#            model.addConstr(x_restruc["Rooftop","standard"] == 1)
#            model.addConstr(x_restruc["GroundFloor","standard"] == 1)
#            model.addConstr(b_sub_restruc["kfw_eff_100"] == 1)      
#            model.addConstr(b_sub_restruc["window"] == 1)
            
        #%% Set start values and branching priority
        if options["load_start_vals"]:
            with open(options["filename_start_vals"], "r") as fin:
                for line in fin:
                    line_split = line.replace("\"", "").split()
                    (model.getVarByName(line_split[0])).Start = float(line_split[1])

        for key in x.keys():
            x[key].BranchPriority = 100       

#%% Set Parameters and start optimization
        
        #Set solver parameters
        model.Params.TimeLimit = params["time_limit"]
        model.Params.MIPGap = params["mip_gap"]
        model.Params.NumericFocus = 3
#        model.Params.MIPFocus = 3
        model.Params.Aggregate = 1

        #Execute calculation
        model.optimize()
                        
 #%%Check feasibility
                       
#        model.computeIIS()
#        model.write("model.ilp")
#        print('\nConstraints:')
#        for c in model.getConstrs():
#            if c.IISConstr:
#                print('%s' % c.constrName)
#        print('\nBounds:')
#        for v in model.getVars():
#            if v.IISLB > 0 :
#                print('Lower bound: %s' % v.VarName)
#            elif v.IISUB > 0:
#                print('Upper bound: %s' % v.VarName)   

#%% Retrieve results

        #Purchase        
        res_x = {dev : x[dev].X  for dev in devs}
        
        # Operation
        res_y = {}
        for dev in heater:
            res_y[dev] = np.array([[y[dev,d,t].X for t in time_steps] for d in days])

        # Tariffs
        res_x_tariff = {"el":{}, "gas":{}}
        for key in ("el", "gas"):
            for tar in x_tariff[key].keys():
                res_x_tariff[key][tar] = {}
                for dev in x_tariff[key][tar].keys():
                    res_x_tariff[key][tar][dev] = x_tariff[key][tar][dev].X

        res_x_gas    = {tar: x_gas[tar].X for tar in x_gas.keys()}
        res_x_el     = {tar: x_el[tar].X  for tar in x_el.keys()}

        # heat and electricity output
        res_power = {}
        res_heat  = {}
        for dev in (heater + solar):
            res_power[dev] = np.array([[power[dev,d,t].X for t in time_steps] for d in days])
            res_heat[dev]  = np.array([[heat[dev,d,t].X  for t in time_steps] for d in days])

        res_energy = {}
        for dev in heater:
            res_energy[dev] = np.array([[energy[dev,d,t].X for t in time_steps] for d in days])
        
        # Gas/El consumption        
        res_G_total  = {dev: G_total[dev].X  for dev in G_total.keys()}
        res_El_total = {dev: El_total[dev].X for dev in El_total.keys()}
        res_G  = {}
        res_El = {}
        for tar in gas_tariffs:
            res_G[tar] = {}
            for dev in ("boiler","chp"):
                for n in x_tariff["gas"][tar].keys():
                    res_G[tar][dev,n] = G[tar][dev,n].X
        for tar in el_tariffs:
            res_El[tar] = {}
            for dev in ("grid_hou","grid_hp"):
                for n in x_tariff["el"][tar].keys():
                    res_El[tar][dev,n] = El[tar][dev,n].X

        # State of charge for storage systems
        res_soc = {}
        for dev in storage:
            res_soc[dev] = np.array([[soc[dev,d,t].X for t in time_steps] for d in days])
    
        # Purchased power from the grid for either feeding a hp tariff component or a different (standard/eco tariff)
        res_p_grid          = {}
        res_p_grid["house"] = np.array([[p_grid["grid_hou",d,t].X for t in time_steps] for d in days])
        res_p_grid["hp"]    = np.array([[p_grid["grid_hp",d,t].X  for t in time_steps] for d in days])

        # Charge and discharge power for storage
        res_ch  = {}
        res_dch = {}
        for dev in ("bat","tes"):           
            res_ch[dev]  = np.array([[ch[dev,d,t].X  for t in time_steps] for d in days])
            res_dch[dev] = np.array([[dch[dev,d,t].X for t in time_steps] for d in days])

        # Power going from an electricity offering component to the demand/the grid/a hp tariff component
        res_p_use  = {}
        res_p_sell = {}
        res_p_hp   = {}
        for dev in ("pv", "bat","chp"):
            res_p_use[dev]  = np.array([[p_use[dev,d,t].X  for t in time_steps] for d in days])
            res_p_sell[dev] = np.array([[p_sell[dev,d,t].X for t in time_steps] for d in days])
            res_p_hp[dev]   = np.array([[p_hp[dev,d,t].X   for t in time_steps] for d in days])
        
        # Costs
        res_c_inv   = {dev: c_inv[dev].X    for dev in c_inv.keys()}
        res_c_om    = {dev: c_om[dev].X     for dev in c_om.keys()}
        res_c_dem   = {dev: c_dem[dev].X    for dev in c_dem.keys()}
        res_c_fix   = {dev: c_fix[dev].X    for dev in c_fix.keys()}
        res_rev     = {dev: revenue[dev].X  for dev in revenue.keys()}
        res_sub     = {dev: subsidy[dev].X  for dev in subsidy.keys()}
        
        res_c_total =   (sum(res_c_inv[key]  for key in c_inv.keys())
                       + sum(res_c_om[key]    for key in c_om.keys())
                       + sum(res_c_dem[key]   for key in c_dem.keys())
                       + sum(res_c_fix[key]   for key in c_fix.keys())
                       - sum(res_rev[key] for key in revenue.keys())
                       - sum(res_sub[key] for key in subsidy.keys()))  
        
        
        res_soc_init = {}
        for dev in storage:
            res_soc_init[dev] = np.array([soc_init[dev,d].X for d in days])
            
        res_soc_nom = {dev: soc_nom[dev].X for dev in storage}
        res_power_nom = {}
        res_heat_nom = {}
        for dev in heater:
            res_heat_nom[dev] = np.array([[heat_nom[dev,d,t].X for t in time_steps] for d in days])

        for dev in ("hp_air","hp_geo"):
            res_power_nom[dev] = np.array([[power_nom[dev,d,t].X for t in time_steps] for d in days])        
       
        res_cap = {dev : capacity[dev].X for dev in capacity.keys()}
        
        res_eh_split = {}
        for dev in ("eh_w/o_hp","eh_w/_hp"):
            res_eh_split[dev] = np.array([[eh_split[dev,d,t].X for t in time_steps] for d in days])
            
        res_heat_mod = {}  
        res_heat_mod[d,t] = np.array([[heat_mod[d,t].X for t in time_steps] for d in days])
        
        res_Ht = H_t.X/total_shell
        
        res_Qp_DIN = Q_p_DIN.X
        
        res_Q_Ht = {}
        res_Q_Ht[d,t] = np.array([[Q_Ht[d,t].X for t in time_steps] for d in days])
        
        res_Qs = {}
        res_Qs[d,t] = np.array([[Q_s[d,t].X for t in time_steps] for d in days])

        res_x_restruc = {}
        for n in restruc_scenarios:
            for dev in building_components:
                res_x_restruc[dev,n] = x_restruc[dev,n].X 
            
        res_heating_concept = {}
        res_lin_Ht = {}
        for n in heating_concept.keys():
            res_heating_concept[n] = heating_concept[n].X
            
        for n in heating_concept.keys():    
            res_lin_Ht[n] = lin_H_t[n].X
              
        res_b_sub_restruc = {dev : b_sub_restruc[dev].X for dev in b_sub_restruc.keys()}
        res_heating_concept = {n : heating_concept[n].X  for n in heating_concept.keys()}
        

        res_sub_chp = {n: sub[n].X for n in sub.keys()}
        
        # Emissions 
#        res_emission_max = max_emi
        res_emission = emission.X / 1000
        
        if options["store_start_vals"]:
            with open(options["filename_start_vals"], "w") as fout:
                for var in model.getVars():
                    if var.VType == "B":
                        fout.write(var.VarName + "\t" + str(int(var.X)) + "\n")

        # Save results 
        with open(options["filename_results"], "wb") as fout:
            pickle.dump(res_x, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_y, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_x_tariff, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_x_gas, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_x_el, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_power, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_heat, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_energy, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_p_grid, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_G, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_G_total, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_El, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_El_total, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_soc, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_soc_init, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_ch, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_dch, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_p_use, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_p_sell, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_p_hp, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_c_inv, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_c_om, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_c_dem, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_c_fix, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_c_total, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_rev, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_sub, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_emission, fout, pickle.HIGHEST_PROTOCOL)  
            pickle.dump(model.ObjVal, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(model.Runtime, fout, pickle.HIGHEST_PROTOCOL)  
            pickle.dump(model.MIPGap, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_soc_nom, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_power_nom, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_heat_nom, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_cap, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_heat_mod, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_b_sub_restruc, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_x_restruc, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_Ht, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_Qs, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_Qp_DIN, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_heating_concept, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_lin_Ht, fout, pickle.HIGHEST_PROTOCOL)         
            pickle.dump(res_sub_chp, fout, pickle.HIGHEST_PROTOCOL)         
                      
        # Return results
        return(res_c_total, res_emission)

    except gp.GurobiError as e:
        print("")        
        print("Error: "+e.message)