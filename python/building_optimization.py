#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on Thu Oct 01 10:35:56 2015
@author: srm
"""

from __future__ import division
import gurobipy as gp
import numpy as np
import pickle

#%% Start:

def compute(eco, devs, clustered, params, options, building, ref_building, 
            shell_eco, sub_par, ep_table, max_emi, max_cost):
    """
    Compute the optimal building energy system consisting of pre-defined 
    devices (devs) for a given building. Furthermore the program can choose
    between different restructuring measures for selected building parts.
    The optimization target can either be the econmic optimum or the ecological
    optimum. 
    The program takes hereby several german subsidy programs for buildings into
    account. 
    
    Parameters
    ----------
    eco : dict
        - b : price-dynamic cash value factor
        - crf : capital recovery factor
        - el : electricity prices
        - energy_tax : additional tax on gas price
        - gas : gas prices
        - inst_costs : installation costs for different devices
        - pel : pellet prices
        - prChange : price changes
        - price_sell_el : price for sold electricity (chp / pv)
        - rate : interest rate        
        - q : interest rate + 1
        - sub_CHP : subsidies for electricity from CHP units
        - t_calc : calculation time
        - tax : value added tax
        
    devs : dict
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
        
    clustered : dict
        - dhw : Domestic hot water load profile
        - electricity : Electricity load profile
        - int_gains : internal gains profile 
        - solar e/n/s/w : solar irradiation for windows
        - solar_roof : solar irradiation on rooftop
        - temp_ambient : Ambient temperature
        - temp_delta : difference between indoor and ambient temperature
        - temp_design : Design temperature for heating system
        - temp_indoor : indoor temperature        
        - weights : Weight factors from the clustering algorithm
        
    params : dict
        - c_w : heat capacity of water
        - days : quantity of clustered days
        - dt : time step length (h)
        - mip_gap : Solver setting (-)
        - rho_w : density of water
        - time_limit : Solver setting (s)
        - time_steps : time steps per day
        
    options : dict
        -      
        
    building : dict
        - U-values : Heat transition coefficients for different scenarios
        - dimensions : Building dimensions
        - usable_roof : Share of usable rooftop area from total area
        
    ref_building : dict
        - H_t_spec: specific transmission coefficient of reference building
        - H_v : ventilation coefficient of reference building
        - Q_i : internal gains of reference building
        - Q_s : solar gains of reference building
        - Q_tw : dhw demand of reference building
        - eta : share of usability of internal and solar gains
        - f_ql : 
            
    shell_eco: dict
        - GroundFloor : ecomomic parameters for GroundFloor    
        - OuterWall : ecomomic parameters for OuterWall
        - Rooftop : ecomomic parameters for Rooftop
        - Window : ecomomic parameters for Window        
         
    sub_par : dict
        - bat : parameters for battery subsidy program
        - building : parameters for subsidy programs for building shell
        - eeg : parameters for eeg
        - hp_air : parameters for hp_air subsidy program
        - hp_geo : parameters for hp_geo subsidy program
        - kwkg : parameters for kwkg
        - pellet : parameters for pellet subsidy program
        - stc : parameters for stc subsidy program
        
    ep_table : dict 
        - TVL35 : 
        - boiler : 
        - chp : 
        - eh :
        - ep : 
        - hp_air :
        - hp_geo : 
        - pellet : 
        - stc :
            
    max_emi : float
        - Upper bound for CO2 emissions
        
    max_cost : float
        - Upper bound for annual costs
        
    """
    
    # Extract parameters
    dt = params["dt"]
    time_steps = range(params["time_steps"])
    days       = range(params["days"])    
    
    M = 10000
    
    # Define subsets
    heater  = ("boiler", "chp", "eh", "hp_air", "hp_geo","pellet")
    storage = ("bat", "tes")
    solar   = ("pv", "stc")
    
    subsidy_devs = ("chp", "bat", "hp_air", "hp_geo", "stc", "pellet", "pv")
    
    building_components = ("Window","OuterWall","GroundFloor","Rooftop")
    
    restruc_scenarios   = ("standard", "retrofit", "adv_retr")
    
    kfw_standards       = ("kfw_eff_55","kfw_eff_70","kfw_eff_85",
                           "kfw_eff_100","kfw_eff_115")

    # Maximal for solar collectors and pv useable Rooftoparea
    A_max = (building["usable_roof"] * 
             building["dimensions"]["Area"] * 
             building["dimensions"]["Rooftop"])
    
    try:
        model = gp.Model("Design computation")
        
#%% Define variables
        
        #%% Economic variables 
        
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
                   for dev in ("kwkg", "bafa")} 

        #%% Technical variables
                                   
        # Purchase and activation decision variables        
        x = {}  # Purchase (all devices)         
        for dev in devs.keys():
            x[dev] = model.addVar(vtype="B", name="x_"+dev)

        # Acitivation heater 
        y = {}  
        for d in days:
            for t in time_steps:
                timetag = "_"+str(d)+"_"+str(t)
                for dev in heater:
                    y[dev,d,t] = model.addVar(vtype="B", name="y_"+dev+"_"+timetag) 
                y["stc",d,t] = model.addVar(vtype="B", name="y_"+"stc"+"_"+timetag) 
        
        # Capacities (thermal output, area, volume,...)
        capacity = {}
        for dev in devs.keys():
            capacity[dev] = model.addVar(vtype="C", name="Capacity_"+dev , lb = 0) 
       
        # Power, Heat and Energy for heater and solar components      
        power_nom = {}
        power = {}
        heat_nom = {}        
        heat = {}
        energy = {}
          
        for d in days:
            for t in time_steps:
                timetag = "_"+str(d)+"_"+str(t)
                
                for dev in heater:
                    heat_nom[dev,d,t] = model.addVar(vtype="C", 
                                                     name="Q_nom_"+dev+"_"+timetag)
                
                for dev in ("hp_air", "hp_geo"):
                    power_nom[dev,d,t] = model.addVar(vtype="C", name="P_nom_"
                                                              +dev+"_"+timetag) 
                    
                    heat[dev,d,t] = model.addVar(vtype="C",  name="Q_"+dev+"_"
                                                                      +timetag)
                    
                    power[dev,d,t] = model.addVar(vtype="C", name="P_"+dev+"_"
                                                                      +timetag)
                
                for dev in ("pellet","boiler"):
                    heat[dev,d,t] = model.addVar(vtype="C", name="Q_"+dev+"_"
                                                                      +timetag)
                    
                    energy[dev,d,t] = model.addVar(vtype="C", name="E_"+dev+"_"
                                                                      +timetag)
                
                dev = "eh"
                power[dev,d,t] = model.addVar(vtype="C", name="P_"+dev+"_"+timetag)
                
                heat[dev,d,t] = model.addVar(vtype="C", name="Q_"+dev+"_"+timetag)
                
                dev = "chp"
                power[dev,d,t] = model.addVar(vtype="C", name="P_"+dev+"_"+timetag)
                
                heat[dev,d,t] = model.addVar(vtype="C", name="Q_"+dev+"_"+timetag)
                
                energy[dev,d,t] = model.addVar(vtype="C", name="E_"+dev+"_"+timetag)
                
                dev = "pv"
                power[dev,d,t] = model.addVar(vtype="C", name="P_"+dev+"_"+timetag)
                
                dev = "stc"
                heat[dev,d,t] = model.addVar(vtype="C", name="Q_"+dev+"_"+timetag)
                    
        # State of charge (SOC) for storage systems
        ch = {}
        dch = {}
        soc = {}
        soc_nom = {}
        soc_init = {}
        
        for dev in storage:
            soc_nom[dev] = model.addVar(vtype="C", name="SOC_nom_"+dev)
            for d in days:
                soc_init[dev,d] = model.addVar(vtype="C", name="SOC_init_"
                                                           +dev + "_" + str(d))
                for t in time_steps:
                    timetag = "_"+str(d)+"_"+str(t)

                    soc[dev,d,t] = model.addVar(vtype="C", name="SOC_"+dev+"_"
                                                              +timetag, lb = 0)
                    
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
        
        # Deciscion if individual measure is allowed although the individual 
        # U-value is too high
        b_ind_mea= model.addVar(vtype = "B", name = "b_ind_mea")

        # Variable for chosen heating concept (relevant for primary energy demand)
        heating_concept = {}
        lin_H_t = {}        
        for n in ep_table["ep"].keys():
            heating_concept[n] = model.addVar(vtype = "B", 
                                              name = "heating_concept_"+str(n))
            
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
                        lin_TVL[temp,dev,d,t] = model.addVar(vtype = "C", 
                                           name = "lin_TVL_"+str(temp), lb = 0) 
         
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
        
        #Battery subsidy program (KfW 275)       
        b_pv_power = {}
        lin_pv_power = {} 
        
        for i in ("kfw", "eeg"):
            lin_pv_power[i] = model.addVar(vtype="C", name = "lin_pv_power_" + i)
            b_pv_power[i]   = model.addVar(vtype="B", name = "b_pv_power_" + i)

        #KWKG for CHP

        p_chp_total = {}
        for usage in ("use","sell","total"):
            p_chp_total[usage] = model.addVar(vtype = "C",
                                            name ="p_chp_total_"+str(usage)) 
                        
        sub_kwkg_temp = model.addVar(vtype="C", name = "sub_kwkg_temp", lb = 0)
            
        b_kwkg = {}
        lin_kwkg_1 = {}
        lin_kwkg_2 = {}
        for n in sub_par["kwkg"]["vls"].keys():   
            b_kwkg[n] = model.addVar(vtype="B", name="b_sub_kwkg_"+str(n))
            lin_kwkg_1[n] = model.addVar(vtype = "C", name = "lin_kwkg_1_" + str(n), lb = 0)
            lin_kwkg_2[n] = model.addVar(vtype = "C", name = "lin_kwkg_2_" + str(n), lb = 0)
                                            
        #BAFA for MINI-CHP
        x_chp = {}
        for dev in ("micro","mini","large"):
            x_chp[dev] = model.addVar(vtype="B", name="x_chp_"+dev)        
                
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
            lin_hp_sub_basic[dev] = model.addVar(vtype="C", 
                                          name="lin_hp_sub_basic_"+dev, lb = 0)
        
        lin_hp_sub_inno = {}
        for dev in ("hp_air", "hp_geo"):
            lin_hp_sub_inno[dev] = model.addVar(vtype="C", 
                                           name="lin_hp_sub_inno_"+dev, lb = 0)   
            
        lin_hp_sub_add = {}
        for dev in ("hp_air", "hp_geo"):
            lin_hp_sub_add[dev] = model.addVar(vtype="C", 
                                            name="lin_hp_sub_add_"+dev, lb = 0)
                
        b_bafa_hp= {}
        for dev in ("hp_air", "hp_geo"):
            b_bafa_hp[dev] = {}
            for i in ("basic_fix", "basic_var", "inno_var", "inno_fix", "add1"):
                b_bafa_hp[dev][i] = model.addVar(vtype = "B", 
                                                    name = "b_bafa_"+dev+"_"+i)
            
        sub_bafa_hp = {}
        for dev in ("hp_air", "hp_geo"):
            sub_bafa_hp[dev] = {}
            for i in ("basic", "inno", "build_eff"):
                sub_bafa_hp[dev][i] = model.addVar(vtype = "C", 
                                          name = "sub_bafa_"+dev+"_"+i, lb = 0)
                
        energy_hp = {}
        for dev in ("hp_air", "hp_geo"):
            energy_hp[dev] = {}
            for i in ("total_heat", "total_power"):
                energy_hp[dev][i] = model.addVar(vtype = "C", 
                                         name = "energy_hp_"+dev+"_"+i, lb = 0)
        
        #PELLET           
        b_bafa_pellet = {}
        for i in ("basic_fix", "basic_storage", "basic_var", 
                  "inno_fix", "inno_storage", "add1"):
            b_bafa_pellet[i] = model.addVar(vtype = "B", 
                                                     name = "b_bafa_pellet_"+i)
            
        sub_bafa_pellet = {}
        for i in ("basic", "inno", "build_eff"):
            sub_bafa_pellet[i] = model.addVar(vtype = "C", 
                                           name = "sub_bafa_pellet_"+i, lb = 0)

        lin_sub_pellet = {}
        for i in ("basic", "inno", "storage"):        
            lin_sub_pellet[i]= model.addVar(vtype = "C", 
                                            name = "lin_sub_pellet_"+i, lb = 0)            
                

            
#%% Objectives      
                   
        c_total = model.addVar(vtype="C", name="c_total", lb= -gp.GRB.INFINITY)
        
        emission = model.addVar(vtype="C", name= "CO2_emission",
                                                          lb= -gp.GRB.INFINITY)      
                
        # Update
        model.update()

#%% Set Objective

        if options["opt_costs"]:
            model.setObjective(c_total, gp.GRB.MINIMIZE)
        
        else:
            model.setObjective(emission, gp.GRB.MINIMIZE)

#%% Define Constraints

        # Differentiation between old and new buildings because of different 
        # regulations in the "Marktanreizprogramm" for HP and STC
        if options["New_Building"]:
            alpha = 0
            model.addConstr(b_TVL["35"] == 1)
       
        else: 
            alpha = 1
            model.addConstr(b_TVL["55"] == 1)
            
        # Flow temperature is either 35 or 55°c
        # Choice depends on the age of the building       
        model.addConstr(b_TVL["35"] + b_TVL["55"] == 1)        
            
        # Differentiation between SFH and MFH because of different 
        # regulations in the "Marktanreizprogramm" STC 
        if options["MFH"]:
            MFH = 1
        else:
            MFH = 0      
            
        #%% Capacitybounds:
        for d in days:
            for t in time_steps:
                for dev in heater:
                    model.addConstr(capacity[dev] >= heat_nom[dev,d,t],                      
                                    name="Capacity_"+dev+"_"+str(d)+"_"+str(t))
        
        #Heater
        for dev in heater:
            model.addConstr(capacity[dev] >= x[dev] * devs[dev]["Q_nom_min"],
                            name="Capacity_min_"+dev)
        
            model.addConstr(capacity[dev] <= x[dev] * devs[dev]["Q_nom_max"],
                            name="Capacity_max_"+dev)
                    
        #Solar Components               
        for dev in solar:
            # Minimum area for each device
            model.addConstr(capacity[dev] >= x[dev] * devs[dev]["area_min"],
                            name="Minimum_area_"+dev)
            
            # Maximum area for each device
            model.addConstr(capacity[dev] <= x[dev] * A_max,
                            name="Maximum_area_"+dev)
                            
        # Area of stc + pv <= A_max
        model.addConstr(sum(capacity[dev] for dev in solar) <= A_max,
                        name="Maximum_total_area")
        
        #Thermal Energy Storage
        dev = "tes"
        model.addConstr(x["tes"] == 1)
        
        model.addConstr(capacity[dev] >= x[dev] * devs[dev]["volume_min"], 
                                                  name="Storage_Volume_min")
        
        model.addConstr(capacity[dev] <= x[dev] * devs[dev]["volume_max"], 
                                                  name="Storage_Volume_max")  
        
        model.addConstr(soc_nom[dev] == capacity[dev] * params["rho_w"] * 
                                        params["c_w"] * devs[dev]["dT_max"] / 
                                        3600000, name="Storage_Volume")
        
        #Battery storage
        dev = "bat"
        model.addConstr(capacity[dev] == soc_nom[dev], name="Capacity_"+dev)
        
        model.addConstr(soc_nom[dev] >= x[dev] * devs[dev]["cap_min"],
                                                 name="Battery_capacity_min")
        
        model.addConstr(soc_nom[dev] <= x[dev] * devs[dev]["cap_max"],
                                                 name="Battery_capacity_max")  

#%% Economic constraints
        
        model.addConstr(c_total ==  (sum(c_inv[key]   for key in c_inv.keys())       
                                   + sum(c_om[key]    for key in c_om.keys())
                                   + sum(c_dem[key]   for key in c_dem.keys())
                                   + sum(c_fix[key]   for key in c_fix.keys())
                                   - sum(revenue[key] for key in revenue.keys())
                                   - sum(subsidy[key] for key in subsidy.keys())))     
        
        #%% Investments
        
        #Devices
        for dev in devs.keys():
            model.addConstr(c_inv[dev] == eco["crf"] * (1-devs[dev]["rval"]) *
                                         (x[dev] * (devs[dev]["c_inv_fix"] + 
                                          eco["inst_costs"]["EFH"][dev] * (1 - MFH) + 
                                          eco["inst_costs"]["MFH"][dev] * MFH) +                                         
                                          capacity[dev] * devs[dev]["c_inv_var"]),
                                          name="Investment_costs_"+dev)
            
        # Investment costs for restruturing measures
        # For Rooftop, GroundFloor and Outerwall the costs are calculated in 
        # relation to the thickness of the additional insulation in comparision
        # to the standard-scenario. The standard scenario is free of cost. 
        for dev in ("Rooftop", "GroundFloor", "OuterWall"):
            model.addConstr(c_inv[dev] == building["dimensions"]["Area"] * 
                                          eco["crf"] * (1-shell_eco[dev]["rval"]) *                 
                                          building["dimensions"][dev] *
                                          (x_restruc[dev,"standard"] * 0 + 
                                           sum(x_restruc[dev,n] * 
                                          (shell_eco[dev]["c_const"] + 
                                           shell_eco[dev]["c_var"] * 100 *
                                           building["U-values"][n][dev]["thick_insu_add"])
                                           for n in ("retrofit", "adv_retr"))),
                                           name = "C_inv_restruc_"+dev)
             
        # For Windows the costs are calculated in relation to the U-value of the
        # chosen Window. The standard scenario is free of cost.
        dev = "Window"
        model.addConstr(c_inv[dev] == building["dimensions"]["Area"] * 
                                      eco["crf"] * (1-shell_eco[dev]["rval"]) *
                                      building["dimensions"][dev] *
                                      (x_restruc[dev,"standard"] * 0 +
                                       sum(x_restruc[dev,n] * 
                                      (shell_eco[dev]["c_const"] + 
                                       shell_eco[dev]["c_var"] * 
                                       building["U-values"][n][dev]["U-Value"])
                                       for n in ("retrofit", "adv_retr"))),
                                       name = "C_inv_restruc_"+dev)
        
        #%% Operation and maintenance
        
        for dev in devs.keys():
            model.addConstr(c_om[dev] == eco["b"]["infl"] * eco["crf"] * 
                                         devs[dev]["c_om_rel"] * 
                                        (x[dev] * devs[dev]["c_inv_fix"] +
                                         capacity[dev] * devs[dev]["c_inv_var"]),
                                         name="O&M_costs_"+dev)

        #%% Demand related costs:

        # Gas:
        # Exactly one gas tariff if at least one chp or boiler is installed        
        for dev in ("chp", "boiler"):
            model.addConstr(x[dev] <= sum(x_gas[key] 
                                      for key in x_gas.keys()),
                                      name="single_gas_tariff_"+dev)
            
        model.addConstr(1 <= sum(x_gas[key] 
                             for key in x_gas.keys()),
                             name="single_gas_tariff_overall")

        for tar in gas_tariffs:
            # Choose one tariff level for the dertermined gas tariff
            model.addConstr(x_gas[tar] == sum(x_tariff["gas"][tar][n] 
                                          for n in x_tariff["gas"][tar].keys()),
                                          name="gas_levels_"+tar+"_"+str(n))
            
            # The tariff level is restricted by the consumed gas amount
            for n in x_tariff["gas"][tar].keys():
                model.addConstr(x_tariff["gas"][tar][n] * 
                                eco["gas"][tar]["lb"][n] <= (G[tar]["boiler",n] + 
                                                             G[tar]["chp",n]) * 0.001,
                                                             name="gas_level_lb"+tar+"_"+str(n))
                
                model.addConstr(x_tariff["gas"][tar][n] * 
                                eco["gas"][tar]["ub"][n] >= (G[tar]["boiler",n] + 
                                                             G[tar]["chp",n]) * 0.001,
                                                             name="gas_level_ub"+tar+"_"+str(n))
                
        # Divide because of energy tax
        for dev in ("boiler","chp"):   
            # Total amount of gas used
            model.addConstr(G_total[dev] == sum(sum(G[tar][dev,n] 
                                            for n in x_tariff["gas"][tar].keys())
                                            for tar in gas_tariffs))
                    
            model.addConstr(G_total[dev] == sum(dt * clustered["weights"][d] * 
                                            sum(energy[dev,d,t] 
                                            for t in time_steps)
                                            for d in days))
            # Variable gas costs
            if dev == "chp":
                model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["gas"] *                                
                                              sum(sum(G[tar][dev,n] * 
                                              (eco["gas"][tar]["var"][n] - eco["energy_tax"])
                                              for n in x_tariff["gas"][tar].keys())
                                              for tar in gas_tariffs),
                                               name="c_dem_"+dev)
            else: 
                model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["gas"] *                                
                                              sum(sum(G[tar][dev,n] * 
                                              eco["gas"][tar]["var"][n]
                                              for n in x_tariff["gas"][tar].keys())
                                              for tar in gas_tariffs)  ,
                                              name="c_dem_"+dev)

        # Electricity:                   
        # Choose one tariff for general electricity purchase                
        non_hp_tariffs = sum(x_el[tar] 
                         for tar in x_el.keys() 
                         if eco["el"][tar]["hp"] == 0)
        
        model.addConstr(non_hp_tariffs == 1, name="single_el_tariff")

        # If a HP is installed, the HP tariff is available
        hp_tariffs = sum(x_el[tar] 
                     for tar in x_el.keys() 
                     if eco["el"][tar]["hp"] == 1)
        
        if options["HP tariff"]:
            # Allow special heat pump tariffs
            model.addConstr(hp_tariffs <= x["hp_air"] + x["hp_geo"],
                            name="optional_hp_tariff")
        else:
            # Prohibit special heat pump tariffs
            model.addConstr(hp_tariffs <= 0, 
                            name="optional_hp_tariff")

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
                model.addConstr(x_tariff["el"][tar][n] * 
                                eco["el"][tar]["lb"][n] <= (El[tar]["grid_hou",n] + 
                                                            El[tar]["grid_hp",n]) * 0.001,
                                                            name="el_level_lb_"+tar+"_"+str(n))
                
                model.addConstr(x_tariff["el"][tar][n] * 
                                eco["el"][tar]["ub"][n] >= (El[tar]["grid_hou",n] + 
                                                            El[tar]["grid_hp",n]) * 0.001,
                                                            name="el_level_ub_"+tar+"_"+str(n))
            
        # Devide because of optional HP tariff
        for dev in ("grid_hou", "grid_hp"):
            # Total amount of electricity used
            model.addConstr(El_total[dev] == sum(sum(El[tar][dev,n] 
                                             for n in x_tariff["el"][tar].keys())
                                             for tar in el_tariffs))
            
            model.addConstr(El_total[dev] == sum(clustered["weights"][d] * 
                                             sum(p_grid[dev,d,t] 
                                             for t in time_steps)
                                             for d in days) * dt)
        
            # Variable electricity costs
            model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["el"] *                             
                                          sum(sum(El[tar][dev,n] * 
                                          eco["el"][tar]["var"][n]
                                          for n in x_tariff["el"][tar].keys())
                                          for tar in el_tariffs),
                                          name="c_dem_"+dev)
               
        # Pellets
        dev = "pellet"
        model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["pel"] * 
                                      eco["pel"]["pel_sta"]["var"][0] * dt *      
                                      sum(clustered["weights"][d] *  
                                      sum(energy[dev,d,t]
                                      for t in time_steps) 
                                      for d in days), 
                                      name="c_dem_"+dev)     
        
        #%% Fixed administration costs: 
                                      
        # Electricity
        model.addConstr(c_fix["el"] == sum(sum(x_tariff["el"][tar][n] * 
                                       eco["el"][tar]["fix"][n]
                                       for n in x_tariff["el"][tar].keys())
                                       for tar in el_tariffs),
                                       name="c_fix_el")
                          
        # Gas
        model.addConstr(c_fix["gas"] == sum(sum(x_tariff["gas"][tar][n] * 
                                        eco["gas"][tar]["fix"][n]
                                        for n in x_tariff["gas"][tar].keys())
                                        for tar in gas_tariffs),
                                        name="c_fix_gas")
                                                                                                                           
        #%% Revenues for selling chp-electricity to the grid
        
        dev = "chp"        
        model.addConstr(revenue[dev] == eco["b"]["eex"] * eco["crf"] * dt * 
                                        eco["price_sell_el"] *
                                        sum(clustered["weights"][d] * 
                                        sum(p_sell[dev,d,t]
                                        for t in time_steps) 
                                        for d in days),
                                        name="Feed_in_rev_"+dev)
                                                   
#%% TECHNICAL CONSTRAINTS
                                        
                                        
#%%Calculation of space heating in accordance with DIN V 4108

        #Transmission losses for windows, wall, rooftop and ground incl. surcharge for thermal bridges 
        #as a function of the selected u-values and the temperature difference:
        
        #It is only possible to choose one scenrio per shellpart
        for dev in building_components:    
            model.addConstr(sum(x_restruc[dev,n] for n in restruc_scenarios) == 1)
            
        #In Accordance to EnEV 2009 the restructuring measures for the individual
        #building parts have to fulfill the required U-Values. If the complete 
        #building has at least KfW-100 status, the individual building parts
        #do not have to fulfill this criteria
        
        for dev in building_components:
            for n in ("retrofit", "adv_retr"):  
            
                u_ref = ref_building["U-values"][dev]
                u_var = building["U-values"][n][dev]["U-Value"]
                
                total_shell = (building["dimensions"]["Area"] * 
                               sum(building["dimensions"][n] 
                               for n in building_components))
                
                Q_p_ref = ref_building["Q_p"]
                H_t_ref = ref_building["H_t_spec"]
                                       
                model.addConstr(x_restruc[dev,n] <=  u_ref / u_var + b_ind_mea)
                                
                model.addConstr(H_t / total_shell <= H_t_ref + (1 - b_ind_mea) * M) 
                                 
                model.addConstr(Q_p_DIN <= Q_p_ref + (1.0 - b_ind_mea) * M)
        
        #Correction factors for components that have no contact with the ambient ait
        Fx = {}
        Fx["Window"] = 1
        Fx["OuterWall"] = 1 
        Fx["GroundFloor"] = 0.6
        Fx["Rooftop"] = 1
        
        model.addConstr(H_t == building["dimensions"]["Area"] * 
                               (sum(building["dimensions"][dev] * Fx[dev] * 
                                sum(x_restruc[dev,n] * 
                                building["U-values"][n][dev]["U-Value"] 
                                for n in restruc_scenarios) 
                                for dev in building_components)
                                + 0.05 * sum(building["dimensions"][dev] 
                                         for dev in building_components)))
                                      
        for d in days:
            for t in time_steps:
                model.addConstr(Q_Ht[d,t] == clustered["temp_delta"][d,t] / 1000 * H_t)                                     
                                           
        
        #Ventilation Losses
        vol = 0.76 * building["dimensions"]["Area"] * building["dimensions"]["Volume"]
        ro_cp = 0.34 #Wh/m³K
        n = 0.7 #1/h 
        
        H_v = ro_cp * n * vol
      
        # Total heating losses
        G_t = 3380 #Kd - Gradtagzahl
        f_na = 0.95 #Parameter for switching off the heater in the night
        f_ql = 0.024 * G_t * f_na
        
        Q_l =  H_v * f_ql / 8760 #kWh
        
        #Solar Gains for all windowareas as a function of the solar radiation 
        #of the respective direction:
                                            
        #Correction factors in accordance with DIN V 4108 and EnEV                                    
        F_solar = 0.9 * 1 * 0.7 * 0.85
        
        for d in days:
            for t in time_steps:
                model.addConstr(Q_s[d,t] == F_solar * sum(x_restruc["Window",n] * 
                                            building["U-values"][n]["Window"]["G-Value"] 
                                            for n in restruc_scenarios)  *     
                                            (building["dimensions"]["Window_east"] * 
                                             clustered["solar_e"][d,t] + 
                                             building["dimensions"]["Window_west"] * 
                                             clustered["solar_w"][d,t] +
                                             building["dimensions"]["Window_north"] * 
                                             clustered["solar_n"][d,t] + 
                                             building["dimensions"]["Window_south"] * 
                                             clustered["solar_s"][d,t]))
                                
        # For every timestep die heating demand is calculated in considering of 
        # the transmissionen and ventilation losses as well as internal and solar gains
        for d in days:
            for t in time_steps:
                 model.addConstr(heat_mod[d,t] >= Q_Ht[d,t] + Q_l - Q_s[d,t] - clustered["int_gains"][d,t])
                 
                 model.addConstr(heat_mod[d,t] <= Q_Ht[d,t] + Q_l) 

#%% Heating systems
    
        # Devices can be switched on only if they have been purchased       
        for dev in heater:
            model.addConstr(params["time_steps"] * 
                            params["days"] * 
                            x[dev] >= sum(sum(y[dev,d,t] 
                                      for t in time_steps) 
                                      for d in days), 
                                      name="Activation_"+dev)
                                  
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
                        
                    model.addConstr(capacity[dev] <= heat_nom[dev,d,t] + 
                                                     q_nom_max * 
                                                     (x[dev] - y[dev,d,t]),
                                                     name="Max_heat_2_"+dev+"_"+timetag)
                    
                    model.addConstr(capacity[dev] >= heat_nom[dev,d,t] + 
                                                     q_nom_min * 
                                                     (x[dev] - y[dev,d,t]),
                                                     name="Min_heat_2_"+dev+"_"+timetag)
        
        for dev in ("boiler","pellet"):
            for d in days:
                for t in time_steps:
                    # Abbreviations
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    model.addConstr(heat[dev,d,t] <= heat_nom[dev,d,t],
                                                     name="Max_heat_operation_"
                                                     +dev+"_"+timetag)
                    
                    model.addConstr(heat[dev,d,t] >= heat_nom[dev,d,t] * 
                                                     devs[dev]["mod_lvl"],
                                                     name="Min_heat_operation_"
                                                     +dev+"_"+timetag)                    
                            
                    model.addConstr(heat[dev,d,t] == energy[dev,d,t] * 
                                                     devs[dev]["eta"],
                                                     name="Energy_equation_"
                                                     +dev+"_"+timetag)       
        
        dev = "chp"
        for d in days:
            for t in time_steps:
                # Abbreviations
                timetag = "_" + str(d) + "_" + str(t)
                
                mod_lvl = devs[dev]["mod_lvl"]
                omega   = devs[dev]["omega"]
                sigma   = devs[dev]["sigma"]
                
                model.addConstr(heat[dev,d,t] <= heat_nom[dev,d,t],
                                name="Max_heat_operation_"+dev+"_"+timetag)
                
                model.addConstr(heat[dev,d,t] >= heat_nom[dev,d,t] * mod_lvl,
                                name="Min_heat_operation_"+dev+"_"+timetag)                    
  
                model.addConstr(power[dev,d,t] == sigma * heat[dev,d,t],
                                name="Power_equation_"+dev+"_"+timetag)
                        
                model.addConstr(energy[dev,d,t] * omega == (heat[dev,d,t] + 
                                                            power[dev,d,t]),
                                                            name="Energy_equation_"+dev+"_"+timetag)
                    
        dev = "eh"
        for d in days:
            for t in time_steps:
                # Abbreviations
                timetag = "_" + str(d) + "_" + str(t)

                model.addConstr(heat[dev,d,t] <= heat_nom[dev,d,t],
                                                 name="Max_heat_operation_"
                                                 +dev+"_"+timetag)
                
                model.addConstr(heat[dev,d,t] >= heat_nom[dev,d,t] * 
                                                 devs[dev]["mod_lvl"],
                                                 name="Min_heat_operation_"
                                                 +dev+"_"+timetag)                    
  
                model.addConstr(heat[dev,d,t] == power[dev,d,t] * 
                                                 devs[dev]["eta"],
                                                 name="Power_equation_"
                                                 +dev+"_"+timetag)
                                                 
        for dev in ("hp_air","hp_geo"):
            for d in days:
                for t in time_steps:

                    timetag = "_" + str(d) + "_" + str(t)
                    
                    mod_lvl = devs[dev]["mod_lvl"]
                    
                    model.addConstr(heat_nom[dev,d,t] == power_nom[dev,d,t] * 
                                                         devs[dev]["cop_a2w35"],
                                                         name="Power_nom_"+dev+"_"+timetag)
                                           
                    model.addConstr(power[dev,d,t] <= power_nom[dev,d,t],
                                                      name="Max_pow_operation_"
                                                      +dev+"_"+timetag)
                    
                    model.addConstr(power[dev,d,t] >= power_nom[dev,d,t] * 
                                                      mod_lvl,
                                                      name="Min_pow_operation_"
                                                      +dev+"_"+timetag)
                
                    model.addConstr(power[dev,d,t] == sum(lin_TVL[temp,dev,d,t] / 
                                                      devs[dev]["cop_w"+temp][d,t] 
                                                      for temp in b_TVL.keys()),
                                                      name="Min_pow_operation_"
                                                      +dev+"_"+timetag)
                    
                    for temp in b_TVL.keys():
                        model.addConstr(lin_TVL[temp,dev,d,t] <= M * b_TVL[temp])
                        
                        model.addConstr(heat[dev,d,t] - lin_TVL[temp,dev,d,t] >= 0)
                        
                        model.addConstr(heat[dev,d,t] - lin_TVL[temp,dev,d,t] <=
                                                          M * (1 - b_TVL[temp]))
                
#%% Solar components

        dev = "pv"
        eta_inverter = 0.97
        model.addConstr(pv_power == capacity[dev] * devs[dev]["p_nom"] / 
                                                    devs[dev]["area_mean"])  
        for d in days:
            for t in time_steps:
                timetag = "_" + str(d) + "_" + str(t)
                
                model.addConstr(power[dev,d,t] <= capacity[dev] * 
                                                  devs[dev]["eta_el"][d][t] *
                                                  eta_inverter *
                                                  clustered["solar_roof"][d][t],
                                                  name="Solar_electrical_"
                                                  +dev+"_"+timetag)
                                                      
        dev = "stc"
        for d in days:
            for t in time_steps:
                timetag = "_" + str(d) + "_" + str(t)

                model.addConstr(heat[dev,d,t] <= capacity[dev] * 
                                                 devs[dev]["eta_th"][d][t] *
                                                 clustered["solar_roof"][d][t],
                                                 name="Solar_thermal_"
                                                 +dev+"_"+timetag)
                               
#%% Storages      
                               
        # Nominal storage content (SOC)
        for dev in storage:
            for d in days:
                #Inits
                model.addConstr(soc_nom[dev] >= soc_init[dev,d], 
                                                name="SOC_nom_inits_"
                                                +dev+"_"+str(d))
                for t in time_steps:
                    # Regular storage loads
                    model.addConstr(soc_nom[dev] >= soc[dev,d,t],
                                                    name="SOC_nom_"
                                                    +dev+"_"+str(d)+"_"+str(t))
                    
        # SOC repetitions
        for dev in storage:
            for d in range(params["days"]):
                if np.max(clustered["weights"]) > 1:
                    model.addConstr(soc_init[dev,d] == soc[dev,d,params["time_steps"]-1],
                                                       name="repetitions_" +dev+"_"+str(d))
                      
        #TES
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

        #BAT
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
    
                model.addConstr(soc[dev,d,t] == (1 - k_loss) * soc_prev + dt *
                                                (charge - discharge),
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
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    model.addConstr(dch[dev,d,t] == heat_mod[d,t], 
                                                    name="Thermal_max_discharge"
                                                    +timetag)
                    
                    model.addConstr(ch[dev,d,t]  == heat["stc",d,t] + 
                                                    sum(heat[dv,d,t] 
                                                    for dv in heater),
                                                    name="Thermal_max_charge"+
                                                    timetag)
          
            #Electricity balance            
            for d in days:
                for t in time_steps:
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    # For components without hp-tariff (p_use["bat"] referring to discharge)
                    model.addConstr(clustered["electricity"][d,t] +
                                    clustered["dhw"][d,t] +
                                    eh_split["eh_w/o_hp",d,t] + 
                                    ch["bat",d,t] == p_grid["grid_hou",d,t] + 
                                                     sum(p_use[dev,d,t] 
                                                     for dev in ("pv","bat","chp")),
                                                     name="El_bal_w/o_HPtariff"
                                                     +timetag)
 
                    # For components with hp-tariff (p_hp["bat"] referring to discharge)
                    model.addConstr(power["hp_air",d,t] + 
                                    power["hp_geo",d,t] + 
                                    eh_split["eh_w/_hp",d,t] == p_grid["grid_hp",d,t] + 
                                                                sum(p_hp[dev,d,t] 
                                                                for dev in ("pv","bat","chp")),
                                                                name="El_bal_w/_HPtariff"
                                                                +timetag)    
        
        else:     
            
            #Thermal balance
            dev = "tes"        
            for d in days:
                for t in time_steps:    
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    model.addConstr(dch[dev,d,t] == heat_mod[d,t] + 
                                                    clustered["dhw"][d,t], 
                                                    name="Thermal_max_discharge"
                                                    +timetag)
                    
                    model.addConstr(ch[dev,d,t] == heat["stc",d,t] + 
                                                   sum(heat[dv,d,t] 
                                                   for dv in heater),
                                                   name="Thermal_max_charge"
                                                   +timetag)
            #Electricity balance            
            for d in days:
                for t in time_steps:
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    # For components without hp-tariff (p_use["bat"] referring to discharge)
                    model.addConstr(clustered["electricity"][d,t] +
                                    eh_split["eh_w/o_hp",d,t] + 
                                    ch["bat",d,t] == p_grid["grid_hou",d,t] + 
                                                     sum(p_use[dev,d,t] 
                                                     for dev in ("pv","bat","chp")),
                                                     name="El_bal_w/o_HPtariff"
                                                     +timetag)
 
                    # For components with hp-tariff (p_hp["bat"] referring to discharge)
                    model.addConstr(power["hp_air",d,t] + 
                                    power["hp_geo",d,t] + 
                                    eh_split["eh_w/_hp",d,t] == p_grid["grid_hp",d,t] + 
                                                                sum(p_hp[dev,d,t] 
                                                                for dev in ("pv","bat","chp")),
                                                                name="El_bal_w/_HPtariff"
                                                                +timetag)    
                    
        
        #Split CHP and PV generation and bat discharge Power into 
        #self-consumed, sold and transferred powers
        for d in days:
            for t in time_steps:
                timetag = "_" + str(d) + "_" + str(t)
                
                dev = "bat"
                model.addConstr(dch[dev,d,t] == p_sell[dev,d,t] + 
                                                p_use[dev,d,t] + 
                                                p_hp[dev,d,t],
                                                name="power=sell+use+hp_"
                                                +dev+timetag)
                
                for dev in ("pv", "chp"):
                    model.addConstr(power[dev,d,t] == p_sell[dev,d,t] + 
                                                      p_use[dev,d,t] + 
                                                      p_hp[dev,d,t],
                                                      name="power=sell+use+hp_"
                                                      +dev+timetag)
                    
        # Split EH power consumption into cases with and without heat pump installed
        dev = "eh"              
        for d in days:
            for t in time_steps:
                model.addConstr(power["eh",d,t] == eh_split["eh_w/o_hp",d,t] + 
                                                   eh_split["eh_w/_hp",d,t])
                                
                model.addConstr(eh_split["eh_w/_hp",d,t]  <= (x["hp_air"] + 
                                                              x["hp_geo"]) * 
                                                              devs[dev]["Q_nom_max"])   
                                                  
                model.addConstr(eh_split["eh_w/o_hp",d,t] <= (1 - x["hp_air"] 
                                                                - x["hp_geo"]) * 
                                                                  devs[dev]["Q_nom_max"])                    
                            
#%% HP and STC operation depends on storage temperature
                
        for dev in ("hp_geo", "hp_air", "stc"):
            for d in days:
                for t in time_steps:
                    timetag = "_" + str(d) + "_" + str(t)
                    
                    # Abbreviations
                    dT_relative = (devs[dev]["dT_max"] / 
                                   devs["tes"]["dT_max"])
                    
                    # Residual storage content
                    resSC = (devs["tes"]["volume_max"] * 
                             devs["tes"]["dT_max"] *
                             params["rho_w"] * 
                             params["c_w"] * 
                             (1 - dT_relative) / 
                             3600000)     
                    
                    model.addConstr(soc["tes",d,t] <= soc_nom["tes"] * 
                                                      dT_relative +
                                                      (1 - y[dev,d,t]) * resSC,
                                                      name="Renew_heater_act_"
                                                      +dev+timetag)      
                
#%% Design heat load following DIN EN 12831 has to be covered
        
        if options["Design_heat_load"]:
            
            delta_temp = clustered["temp_indoor"] - clustered["temp_design"] 
            
            model.addConstr(dsh == (H_t + 0.5 * 0.34 * 
                                    building["dimensions"]["Volume"] * 
                                    building["dimensions"]["Area"]) *
                                    delta_temp / 1000,
                                    name = "dsh1")
        
            model.addConstr(dsh <= sum(capacity[dev] 
                                       for dev in ("boiler","chp","eh")) +
                                       sum(capacity[hp] * devs[hp]["cop_a2w55"]
                                       for hp in ("hp_air", "hp_geo")),
                                       name="dsh2")
        
        else:
            
            model.addConstr(dsh == 0 )
     
#%% CO2-Emissions
     
        emission_pellet = (eco["pel"]["pel_sta"]["emi"] * 
                           sum(clustered["weights"][d] * dt * 
                           sum(energy["pellet",d,t] 
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
               
        emissions_feedin = 0.566 * sum(clustered["weights"][d] * dt * 
                                   sum(sum(p_sell[dev,d,t] 
                                   for dev in ("pv","bat","chp"))
                                   for t in time_steps)
                                   for d in days)
        
        model.addConstr(emission == emission_pellet + 
                                    emissions_gas + 
                                    emissions_grid - 
                                    emissions_feedin)
                                                          
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
            model.addConstr(subsidy[dev] == eco["crf"] * sub_par["eeg_temp"] *
                                            sum(p_sell_pv[n] * sub_par["eeg"][n]
                                            for n in pv_powerstages),
                                            name="Feed_in_rev_"+dev)
                                            
            model.addConstr(subsidy[dev] <= M * b_pv_power["eeg"])
            
            model.addConstr(b_pv_power["eeg"] <= x["pv"])
            
            # If EEG is available: subsidy instead of revenue
            model.addConstr(revenue[dev] == 0)
                                       
        else:            
            # If EEG is not available: revenue instead of subsidy
            model.addConstr(subsidy[dev] == 0)
            
            model.addConstr(revenue[dev] == eco["b"]["eex"] * eco["crf"] *
                                            eco["price_sell_el"] *
                                            p_sell_pv["total"],
                                            name="Feed_in_rev_"+dev)    

        #%% KfW-Subsidy for Battery
        
        dev = "bat"
        
        if options["kfw_battery"]:
            
            model.addConstr(subsidy[dev] <= eco["crf"] * 
                                            sub_par["bat"]["share_max"] *                            
                                            sub_par["bat"]["sub_bat_max"] *                                             
                                            pv_power,                                            
                                            name="Bat_Subsidies_1")
            
            model.addConstr(subsidy[dev] <= c_inv["pv"] + c_inv["bat"] -                            
                                            eco["crf"] * 
                                            sub_par["bat"]["share_max"] *                                                                                          
                                            sub_par["bat"]["sub_bat"] *                                              
                                            pv_power,            
                                            name="Bat_Subsidies_2")
            
            model.addConstr(subsidy[dev] <= M * b_pv_power["kfw"])
            
            model.addConstr(b_pv_power["kfw"] <= x["bat"])
        
        else:
            
            model.addConstr(subsidy[dev] == 0)
          
            
        #%% For EEG and KfW-Bat program:
        
        # Bestrict sold electricity from PV to 70% of the rated power without
        # battery storage and 50% with storage system       
        
        dev = "pv" 
        
        for d in days:
            for t in time_steps:                                                
                model.addConstr(p_sell["pv",d,t] + 
                                p_sell["bat",d,t] <= devs[dev]["p_nom"]/
                                                     devs[dev]["area_mean"] * 
                                                     (capacity[dev] - 0.3 * 
                                                      lin_pv_power["eeg"]))

        for d in days:
            for t in time_steps:                                                
                model.addConstr(p_sell["pv",d,t] + 
                                p_sell["bat",d,t] <= devs[dev]["p_nom"]/
                                                     devs[dev]["area_mean"] * 
                                                     (capacity[dev] - 0.5 * 
                                                      lin_pv_power["kfw"]))

        # Linearization of b_pv_power[i] * capacity["pv"]
        for i in ("eeg", "kfw"):  
            model.addConstr(lin_pv_power[i] <= A_max * b_pv_power[i])
            
            model.addConstr(lin_pv_power[i] >= devs[dev]["area_min"] * 
                                               b_pv_power[i])
            
            model.addConstr(capacity[dev] - lin_pv_power[i] >= 0)
            
            model.addConstr(capacity[dev] - lin_pv_power[i] <= (1 - b_pv_power[i]) * A_max)
        
                                                                               
        #%% CHP        
        dev = "chp"   
        
        # There are two subsidy-possibilities for chps
        # 1. Remuneration system in accordance with the KWKG
        # 2. Investment subsidy for small chps
        
        model.addConstr(subsidy[dev] == sub["kwkg"] + 
                                        sub["bafa"],
                                        name = "chp_sub") 
                                            
        #BAFA-Subsidy for Mirco-CHP
        #Program has three parts: basic-subsidy, thermal-efficiency-bonus and 
        #power-efficiency-bonus - Further informations:
        #http://www.bafa.de/DE/Energie/Energieeffizienz/Kraft_Waerme_Kopplung/Mini_KWK/mini_kwk_node.html
        
        if options["Bafa_chp"]:   
            
            # Only devices with p_el <= 20 kW can achieve a subsidy
            # For the modeling we distinguish betweeen three power-categories: 
            # micro: < 1kW, mini: 1 - 20 kW, large: >20kW
            
            model.addConstr(x["chp"] == x_chp["micro"] + 
                                        x_chp["mini"] + 
                                        x_chp["large"],
                                        name = "chp_size")
            
            power_chp = capacity[dev] * devs[dev]["sigma"]
                       
            model.addConstr(power_chp <= 1 * x_chp["micro"] + 
                                        20 * x_chp["mini"] +
                                         M * x_chp["large"], 
                                         name = "chp_sum_powerstep_ub")          
            
            model.addConstr(power_chp >= sum(chp_powerstep[i] 
                                         for i in chp_powerstep.keys()), 
                                         name = "chp_sum_powerstep")

            model.addConstr(chp_powerstep[1] == 1 * x_chp["mini"], 
                                                name = "chp_powerstep1")
            
            model.addConstr(chp_powerstep[2] <= 3 * x_chp["mini"],
                                                name = "chp_powerstep1")
            
            model.addConstr(chp_powerstep[3] <= 6 * x_chp["mini"],
                                                name = "chp_powerstep2")
            
            model.addConstr(chp_powerstep[4] <= 10 * x_chp["mini"],
                                                name = "chp_powerstep3")          
            
            # Bounds for Basic CHP Subsidy                                   
            model.addConstr(sub_chp_basic <= sub_par["bafa_chp"]["sub_basic_max"] * 
                                             x_chp["mini"] + 
                                             sub_par["bafa_chp"]["sub_step_1"] * 
                                             x_chp["micro"], 
                                             name = "chp_sub_basic_ub")
            
            model.addConstr(sub_chp_basic <= sub_par["bafa_chp"]["sub_step_1"] * 
                                             (x_chp["micro"] + chp_powerstep[1]) + 
                                             sub_par["bafa_chp"]["sub_step_2"] * 
                                             chp_powerstep[2] + 
                                             sub_par["bafa_chp"]["sub_step_3"] * 
                                             chp_powerstep[3] + 
                                             sub_par["bafa_chp"]["sub_step_4"] * 
                                             chp_powerstep[4],
                                             name = "chp_sub_basic_calcutation")     
           
            # Calculate annual subsidy value
            model.addConstr(sub["bafa"] == eco["crf"] * sub_chp_basic * (1 + 
                                           sub_par["bafa_chp"]["share_therm_eff"] * 
                                           devs[dev]["therm_eff_bonus"] +
                                           sub_par["bafa_chp"]["share_elec_eff"] * 
                                           devs[dev]["power_eff_bonus"]),
                                           name = "chp_bafa_total_calculation")           
      
        else:            
            model.addConstr(sub["bafa"] == 0)
                      
        #KWKG for CHP 
        if options["KWKG"]:
            
            # Total electricity produced by CHP per year
            model.addConstr(p_chp_total["total"] == dt * sum(clustered["weights"][d] *
                                                         sum(p_sell[dev,d,t] + 
                                                             p_use[dev,d,t] + 
                                                             p_hp[dev,d,t]
                                                             for t in time_steps) 
                                                             for d in days))
    
            # Self consumed electricity from CHP                            
            model.addConstr(p_chp_total["use"] == dt * sum(clustered["weights"][d] *
                                                       sum(p_use[dev,d,t] + 
                                                           p_hp[dev,d,t]                            
                                                           for t in time_steps) 
                                                           for d in days))
                                                      
            # Sold electricity from CHP
            model.addConstr(p_chp_total["sell"] == dt * sum(clustered["weights"][d] *
                                                        sum(p_sell[dev,d,t]                           
                                                        for t in time_steps) 
                                                        for d in days))
                
            # Differentiation between discrete categories of full load hours
            model.addConstr(sum(b_kwkg[n] for n in b_kwkg.keys()) <= 1)
            
            # Constant annual payment - In the following the interest effect
            # has to be considered!
            model.addConstr(sub_kwkg_temp == p_chp_total["use"] * 
                                             sub_par["kwkg"]["self_50"] + 
                                             p_chp_total["sell"] * 
                                             sub_par["kwkg"]["sell_50"])
            
            # Here the full load hours per year are determined
            # The amount of full load hours per year decides in how many years
            # the kwkg-subsidy is paid 
            model.addConstr(p_chp_total["total"] <= sum(lin_kwkg_1[n] * 
                                                        sub_par["kwkg"]["vls"][n]
                                                        for n in sub_par["kwkg"]["vls"].keys()))
            
            #Linearization part 1: b_kwkg[n] * capacity["chp"]                   
            U = 50 #kWh        
            for n in b_kwkg.keys():
                model.addConstr(lin_kwkg_1[n] <= U * b_kwkg[n])
                model.addConstr(devs["chp"]["sigma"] * capacity["chp"] - lin_kwkg_1[n] >= 0)
                model.addConstr(devs["chp"]["sigma"] * capacity["chp"] - lin_kwkg_1[n] <= U * (1-b_kwkg[n]))
                
            #Linearization part 2: b_kwkg[n] * sub_kwkg_temp                  
            U = 40000 #€
            for n in b_kwkg.keys():
                model.addConstr(lin_kwkg_2[n] <= U * b_kwkg[n])
                model.addConstr(sub_kwkg_temp - lin_kwkg_2[n] >= 0)
                model.addConstr(sub_kwkg_temp - lin_kwkg_2[n] <= U * (1-b_kwkg[n])) 
            
            # Here the correct annuity is determined (incl. interest effect)
            model.addConstr(sub["kwkg"] == eco["crf"] * sum(lin_kwkg_2[n] * 
                                                            sub_par["kwkg"]["i"][n]
                                                            for n in sub_par["kwkg"]["i"].keys()))
                                
        else:            
            model.addConstr(sub["kwkg"] == 0)
            
        #%% MAP-Subsidy for STC  
                   
        #The "Marktanreizprogramm" MAP is a subsidy-program for STC by BAFA
        #The prorgam has three parts: basic, innovation and additional subsidy
        #Further Information:
        #http://www.bafa.de/DE/Energie/Heizen_mit_Erneuerbaren_Energien/Solarthermie/solarthermie_node.html 
        
        dev = "stc"                    
        if options["Bafa_stc"]:            
            
            #It is only possible to get either basic_fix, basic_var or inno
            model.addConstr(x["stc"] >= b_bafa_stc["basic_fix"] + 
                                        b_bafa_stc["basic_var"] + 
                                        b_bafa_stc["inno"],                          
                                        name = "stc_bafa_x_stc")
            
            model.addConstr(x["tes"] >= b_bafa_stc["basic_fix"] + 
                                        b_bafa_stc["basic_var"] + 
                                        b_bafa_stc["inno"],
                                        name = "stc_bafa_x_tes")
            
            #Thermal storage restriction
            #At least 50 l/m² are necessary
            model.addConstr(capacity["tes"] * 
                            params["rho_w"] >= sub_par[dev]["min_storage"] * 
                                               lin_sub_stc, 
                                               name = "stc_bafa_tes_restr")
            
            # Linearization for storage constraint
            model.addConstr(lin_sub_stc <= A_max * (b_bafa_stc["basic_fix"] + 
                                                    b_bafa_stc["basic_var"] + 
                                                    b_bafa_stc["inno"]),
                                                    name = "stc_bafa_lin_1") 
            
            model.addConstr(capacity[dev] - lin_sub_stc >= 0,
                                                    name = "stc_bafa_lin_2")  
            
            model.addConstr(capacity[dev] - lin_sub_stc <=  A_max * (1 - 
                                                    (b_bafa_stc["basic_fix"] + 
                                                     b_bafa_stc["basic_var"] + 
                                                     b_bafa_stc["inno"])),
                                                     name = "stc_bafa_lin_3")         
                                                    
            #Basic program
            #Area restriction   
            #At least 9 m² are necessary
            model.addConstr(capacity[dev] / sub_par[dev]["basic_area_min"] >= 
                                                    (b_bafa_stc["basic_var"] + 
                                                     b_bafa_stc["basic_fix"]),
                                                     name = "stc_bafa_basic_area_restr")   

            #Just for old buildings
            model.addConstr(sub_bafa_stc["basic_fix"] <= sub_par[dev]["basic_fix"] * 
                                                         b_bafa_stc["basic_fix"] * 
                                                         alpha,
                                                         name = "stc_bafa_basic_fix")
            
            model.addConstr(sub_bafa_stc["basic_var"] <= sub_par[dev]["basic_var"] * 
                                                         capacity[dev],
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
            model.addConstr(b_bafa_stc["inno"] <= capacity[dev] / 
                                                  sub_par[dev]["inno_area_min"],
                                                  name = "stc_bafa_inno_area_restr")        
            
            #Program only available for MFH
            model.addConstr(sub_bafa_stc["inno"] <= (sub_par["stc"]["inno_new_b"] + 
                                                     sub_par["stc"]["inno_existing_b"] * 
                                                     alpha) * capacity[dev] * MFH,
                                                     name = "stc_bafa_inno_var")
            
            model.addConstr(sub_bafa_stc["inno"] <= (sub_par["stc"]["inno_new_b"] + 
                                                     sub_par["stc"]["inno_existing_b"] * 
                                                     alpha) * b_bafa_stc["inno"] * MFH *                                                     
                                                     sub_par["stc"]["inno_area_max"],
                                                     name = "stc_bafa_inno_ub")            
            
            #Additional program
            #STC in combination with HP is necessary
            model.addConstr(x["stc"] >= b_bafa_stc["add1"], name = "stc_bafa_add_1")
                            
            model.addConstr(x["hp_air"] + x["hp_geo"] >= b_bafa_stc["add1"],
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
            model.addConstr(subsidy[dev] == eco["crf"] * 
                                             (sub_bafa_stc["basic_fix"] + 
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
                model.addConstr(x[dev] >= b_bafa_hp[dev]["basic_fix"] + 
                                          b_bafa_hp[dev]["basic_var"] + 
                                          b_bafa_hp[dev]["inno_fix"] + 
                                          b_bafa_hp[dev]["inno_var"],
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
                #has to be at least 4.5 or higher 
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
                model.addConstr(capacity["tes"] * 
                                params["rho_w"] >= sub_par[dev]["stor_restr"] * 
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
                model.addConstr(subsidy[dev] == eco["crf"] * 
                                                (sub_bafa_hp[dev]["basic"] + 
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
            model.addConstr(x["pellet"] >= b_bafa_pellet["basic_fix"] + 
                                           b_bafa_pellet["basic_storage"] +
                                           b_bafa_pellet["basic_var"] + 
                                           b_bafa_pellet["inno_fix"] +
                                           b_bafa_pellet["inno_storage"],
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
            model.addConstr(capacity["tes"] * 
                            params["rho_w"] >= sub_par[dev]["stor_restr"] * 
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
                                                                                                                          
        #%%KfW-Subsidies for individual measures
                                                                                                                                  
        #Subsidy is only available if chosen restruction scenario satisfies the necessary Standard 
        for dev in building_components:                                                                                                            
            model.addConstr(sum(x_restruc[dev,n] * 
                                building["U-values"][n][dev]["U-Value"]
                                for n in restruc_scenarios) <= sub_par["building"]["u_value"][dev] + 
                                                               (1.0 - b_sub_restruc[dev]) * M)                                                                                                         
             
        #5000€ grant for every individual measure but max. 10% of the respective investment                                                                                                       
        if options["kfw_single_mea"]:
            for dev in building_components:                 
                model.addConstr(subsidy[dev] <= eco["crf"] * 
                                                (1.0 - shell_eco[dev]["rval"]) * 
                                                b_sub_restruc[dev] * 
                                                sub_par["building"]["grant"]["ind_mea"] * 
                                                (1-MFH))   
                
                share_max = sub_par["building"]["share_max"]["ind_mea"]
                
                model.addConstr(subsidy[dev] <= c_inv[dev] * share_max)        

        else:                              
            for dev in building_components:  
                model.addConstr(subsidy[dev] == 0)    

        #%%KfW-Subsides for Efficient Buildings (KfW-Effizienzhaeuser)
       
        #Calculation of the Primary Energy demand in accordance with DIN 4108
        #Just the Transmission losses are variable with regard to the restruction
        #measures. Ventilation losses, internal and solar gains are determined 
        #with a static method (such as for the reference building)
        
        #There are different heating concepts that are regaderd:       
        model.addConstr(1 == sum(heating_concept[n] 
                             for n in heating_concept.keys()))
        
        for n in heating_concept.keys():
            model.addConstr(heating_concept[n] >= sum(ep_table[dev][n] * x[dev] +
                                                 (1 - ep_table[dev][n]) * (1 - x[dev]) 
                                                  for dev in ("boiler", "chp", "eh", "hp_air", 
                                                              "hp_geo","pellet","stc")) + 
                                                  ep_table["TVL35"][n] * b_TVL["35"] +
                                                  (1 - ep_table["TVL35"][n]) * 
                                                  (1 - b_TVL["35"]) - 7) 
                                                                              
        model.addConstr(x["boiler"] + x["eh"] <= 1)
        model.addConstr(x["chp"] + x["eh"] <= 1)
        model.addConstr(x["chp"] + x["stc"] <= 1)
        model.addConstr(x["eh"] <= x["hp_air"] + x ["hp_geo"])
        model.addConstr(x["pellet"] + x["hp_geo"] + x["hp_air"] + x["chp"] <= 1)

        #Linearization: Product of H_t (continuous) and heating_concept (binary)               
        for n in heating_concept.keys():                
            model.addConstr(lin_H_t[n] <= M * heating_concept[n])                                         
            
            model.addConstr(H_t - lin_H_t[n] >= 0)        
            
            model.addConstr(H_t - lin_H_t[n] <= M * (1 - heating_concept[n]))
                

        #Determination of the primary energy demand 
        model.addConstr(Q_p_DIN == 1/1000 * (ref_building["f_ql"] * 
                                             sum(ep_table["ep"][n] * lin_H_t[n] 
                                             for n in lin_H_t.keys()) +  
                                             ref_building["H_v"] * ref_building["f_ql"] + 
                                             ref_building["Q_tw"] - ref_building["eta"] * 
                                             (ref_building["Q_i"] + ref_building["Q_s"]) * 
                                             sum(heating_concept[n] * ep_table["ep"][n] 
                                             for n in heating_concept.keys())))
                          
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
        model.addConstr(1 >= sum(b_sub_restruc[n] 
                             for n in kfw_standards))
        
        #Either subsidies for individual measurers OR for efficiency buildings
        for dev in building_components:
            model.addConstr(1 >= b_sub_restruc[dev] + 
                                 sum(b_sub_restruc[n] 
                                 for n in kfw_standards))                                        
               
        if options["kfw_eff_buildings"]:
            for dev in kfw_standards:
                model.addConstr(subsidy[dev] <= eco["crf"] * 
                                                (1 - shell_eco["Window"]["rval"]) * 
                                                b_sub_restruc[dev] * 
                                                sub_par["building"]["grant"][dev] * 
                                                (1 - MFH))
                                                
                model.addConstr(subsidy[dev] <= sub_par["building"]["share_max"][dev] * 
                                                sum(c_inv[n] for n in building_components))     

        else:                              
            for dev in kfw_standards:
                model.addConstr(subsidy[dev] == 0)                         
        
#%% Define Scenarios 
        
        model.addConstr(0.001 * emission <= max_emi)       

        model.addConstr(c_total <= max_cost)
                
        if options["scenario"] == "free":
            pass
        
        elif options ["scenario"] == "benchmark":
            model.addConstr(x["boiler"] == 1)            
            for i in building_components:
                model.addConstr(x_restruc[i,"standard"] == 1)
        
        elif options ["scenario"] == "s1":
            for i in building_components:
                model.addConstr(x_restruc[i,"standard"] == 1)
                model.addConstr(x_restruc[i,"retrofit"] == 0)
            model.addConstr(x["chp"] == 1)
            model.addConstr(x["boiler"] == 0)
            model.addConstr(x["hp_air"] == 0)
            model.addConstr(x["hp_geo"] == 0)
            model.addConstr(x["stc"] == 0)
            model.addConstr(x["pv"] == 0)
            model.addConstr(x["bat"] == 0)
            model.addConstr(x["pellet"] == 0)
            
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
        model.Params.MIPFocus = 3
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
        for dev in ("pellet","stc","boiler","hp_geo","hp_air","eh","chp"):
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
        res_energy = {}
        for dev in ("boiler", "chp", "hp_air", "hp_geo", "eh", "stc", "pellet"): 
            res_heat[dev]  = np.array([[heat[dev,d,t].X  for t in time_steps] for d in days])
        for dev in ("hp_air", "hp_geo", "eh"):
            res_power[dev] = np.array([[power[dev,d,t].X for t in time_steps] for d in days])      
        for dev in ("boiler", "chp", "pellet"):
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
        
        res_b_pv_power = {i: b_pv_power[i].X for i in ("kfw", "eeg")}
        res_lin_pv_power = {i: lin_pv_power[i].X for i in ("kfw", "eeg")}
        
        res_p_chp_total = {}
        for n in p_chp_total.keys():
            res_p_chp_total[n] = p_chp_total[n].X
                    
        res_lin_kwkg_1={}
        res_lin_kwkg_2={}
        res_b_kwkg={}
        for n in b_kwkg.keys():
            res_lin_kwkg_2[n] = lin_kwkg_2[n].X
            res_lin_kwkg_1[n] = lin_kwkg_1[n].X
            res_b_kwkg[n] = b_kwkg[n].X
       
        res_sub_kwkg_temp = sub_kwkg_temp.X
        
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
            pickle.dump(res_b_pv_power, fout, pickle.HIGHEST_PROTOCOL)         
            pickle.dump(res_lin_pv_power, fout, pickle.HIGHEST_PROTOCOL)    
            pickle.dump(res_p_chp_total, fout, pickle.HIGHEST_PROTOCOL)      
            pickle.dump(res_lin_kwkg_2, fout, pickle.HIGHEST_PROTOCOL)         
            pickle.dump(res_lin_kwkg_1, fout, pickle.HIGHEST_PROTOCOL)    
            pickle.dump(res_b_kwkg, fout, pickle.HIGHEST_PROTOCOL)      
            pickle.dump(res_sub_kwkg_temp, fout, pickle.HIGHEST_PROTOCOL)      

        # Return results
        return(res_c_total, res_emission)

    except gp.GurobiError as e:
        print("")        
        print("Error: "+e.message)