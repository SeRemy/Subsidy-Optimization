#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: srm
"""

from __future__ import division
import pandas as pd
import gurobipy as gp
import numpy as np
import pickle

#%% Start:

def compute(eco, devs, clustered, df_vent, 
            params, options, building, shell_eco, 
            max_emi, max_cost, vent):
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
        - ventilation_loss : window profile for ventilation loss
        
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
    
    vent : dict
        eco     - phi_heat_recovery : Rückwärmezahl
                - price_a           : y-Achsenabschnitt Preiskurve
                - price_b           : Steigung Preiskurve
                    
        sci     - rho_a_ref         : density of air on sea level
                - cp_air            : heat capacity air
                - c_wnd             : coefficient to consider velocity of wind
                - c_st              : coefficient to consider thermal draft
                    
        tec     - h_w_st            : wirksame Höhe des thermischen Auftriebes (Annahme)
                - A_w_tot           : gesamte Fensteröffnungsfläche (Annahme)
                - e_z               : Volumenstromkoeffizient (Annahme)
                
        n_50_table

                
    """
    
    # Extract parameters
    dt = params["dt"]
    time_steps = range(params["time_steps"])
    days       = range(params["days"])    
        
    # Define subsets
    heater  = ("boiler", "chp", "eh", "hp_air", "hp_geo", "pellet", "boiler_gas_old", "boiler_oil_old")
    storage = ("bat", "tes")
    solar   = ("pv", "stc")
	
    building_components = ("Window","OuterWall","GroundFloor","Rooftop")
    
    restruc_scenarios   = ("standard", "retrofit", "adv_retr")

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
                 for dev in ("boiler", "bat", "chp", "eh", "GroundFloor", "hp_air", "hp_geo", "tes", 
                             "OuterWall", "pellet", "pv", "Rooftop", "stc", "vent", "Window",
                             "boiler_gas_old", "boiler_oil_old")}
                     
        c_om   = {dev: model.addVar(vtype="C", name="c_om_"+dev)
                 for dev in list(devs.keys())}
                     
        c_dem  = {dev: model.addVar(vtype="C", name="c_dem_"+dev)
                 for dev in ("boiler", "chp", "pellet", "grid_house", "grid_hp",
                             "boiler_gas_old", "boiler_oil_old")}   
                 
        c_fix  = {dev: model.addVar(vtype="C", name="c_fix_"+dev)
                 for dev in ("el", "gas")}    
        
        # Revenues and Subsidies                
        revenue = {dev: model.addVar(vtype="C", name="revenue_"+dev)
                  for dev in ("chp", "pv")} 
                             

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
                
                for dev in ("pellet","boiler", "boiler_gas_old", "boiler_oil_old"):
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
                
                p_grid["grid_house",d,t] = model.addVar(vtype="C", name="p_grid_house"+timetag)
                
                p_grid["grid_hp",d,t]  = model.addVar(vtype="C", name="p_grid_hp"+timetag)
                
                # Note: bat is referring to the discharge power
                for dev in ("pv", "bat","chp"):
                    p_use[dev,d,t]  = model.addVar(vtype="C", name="P_use_"+dev+timetag)
                    
                    p_sell[dev,d,t] = model.addVar(vtype="C", name="P_sell_"+dev+timetag)
                    
                    p_hp[dev,d,t]   = model.addVar(vtype="C", name="P_hp_"+dev+timetag)

        # Split EH for HP tariff
        eh_split = {}
        
        for d in days:
            for t in time_steps:
                timetag = "_"+str(d)+"_"+str(t)                
                eh_split["eh_w/o_hp",d,t] = model.addVar(vtype="C", 
                                                    name="p_eh_w/o_hp"+timetag)
                
                eh_split["eh_w/_hp",d,t]  = model.addVar(vtype="C", 
                                                     name="p_eh_w/_hp"+timetag)
                        
#%% Variables for restructuring measures
            
        # Variable for building-shell components
        x_restruc  ={}
        for dev in building_components:
            for n in restruc_scenarios:
                x_restruc[dev,n] = model.addVar(vtype="B", name="x_"+dev+"_"+str(n))
               
        # Heating demand depending on to the chosen building shell components
        heat_mod = {}  
        for d in days:
            for t in time_steps:
                heat_mod[d,t] = model.addVar(vtype = "C", name = "heat_mod", lb = 0)
        
        # Transmission losses
        
        # Transmission coefficient in accordance with DIN V 4108
        H_t = model.addVar(vtype = "C", name = "H_t", lb = 0) 
        
        Q_Ht = {}  
        for d in days:
            for t in time_steps:
                Q_Ht[d,t] = model.addVar(vtype = "C", name = "HT")
        
        # Ventilation losses
        
        ventilation_concept = {}
        for n in vent["n_50_table"]["n_50"].keys():
            ventilation_concept[n] = model.addVar(vtype = "B", 
                                              name = "ventilation_concept"+str(n))
            
        x_vent_concept = {}
        for n in vent["x_vent_table"]["x_vent"].keys():
            x_vent_concept[n] = model.addVar(vtype = "B", 
                                              name = "x_vent_concept"+str(n))
                    
        Q_vent_loss = {}
        for d in days:
            for t in time_steps:
                Q_vent_loss[d,t] = model.addVar(vtype = "C", name = "Qvent_loss")
        

        Q_v_Inf_wirk = {}        
        for d in days:
            for t in time_steps:                
                Q_v_Inf_wirk[d,t] = model.addVar(vtype ="C", name = "Q_v_Inf_wirk")
                
        n_total = {}
        for d in days:
            for t in time_steps:
                n_total[d,t] = model.addVar(vtype ="C", name = "n_total")
                
        # ventilation system
        x_vent = model.addVar(vtype="B", name="x_vent") # Add purchase decision variable for ventilation system
        n_50 = model.addVar(vtype ="C", name="n_50")    # Add n_50 as variable 
        
        # Real solar gains
        Q_s = {}  
        for d in days:
            for t in time_steps:
                Q_s[d,t] = model.addVar(vtype = "C", name = "Qs")               
                
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
                    
#%% Set Objectives      
                   
        c_total = model.addVar(vtype="C", name="c_total", lb= -gp.GRB.INFINITY)
        
        emission = model.addVar(vtype="C", name= "CO2_emission", lb= -gp.GRB.INFINITY)      

        model.update()

        if options["opt_costs"]:
            model.setObjective(c_total, gp.GRB.MINIMIZE)
                    
        else:
            model.setObjective(emission, gp.GRB.MINIMIZE)

#%% Define Constraints

        # Differentiation between old and new buildings because of different 
        # regulations in the "Marktanreizprogramm" for HP and STC
#        if options["New_Building"]:
#            model.addConstr(b_TVL["35"] == 1)
#       
#        else: 
#            model.addConstr(b_TVL["55"] == 1)
            
        # Flow temperature is either 35 or 55°c
        # Choice depends on the age of the building       
        model.addConstr(b_TVL["35"] + b_TVL["55"] == 1)  
        
        model.addConstr(b_TVL["55"] == 1) #DUMMY!

        # Differentiation between SFH and MFH
        if options["ClusterB"]:
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
                                   - sum(revenue[key] for key in revenue.keys())))    

        model.addConstr(c_total <= max_cost)								   
        
        #%% Investments
        
        #Devices
        for dev in devs.keys():
            model.addConstr(c_inv[dev] == eco["crf"] * devs[dev]["rval"] *
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
                                          eco["crf"] * shell_eco[dev]["rval"] *                 
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
                                      eco["crf"] * shell_eco[dev]["rval"] *
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
            model.addConstr(c_om[dev] == eco["b"]["infl"] * devs[dev]["c_om_rel"] * c_inv[dev])

        #%% Demand related costs:
        
        #Electricity
        dev = "grid_house"            
        el_total_house = (dt * sum(clustered["weights"][d] * sum(p_grid[dev,d,t] 
                          for t in time_steps) for d in days) * dt)
        
        model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["el"] * 
                                      el_total_house * eco["el"]["el_sta"]["var"][0])
                    
        dev = "grid_hp"
        el_total_hp = (dt * sum(clustered["weights"][d] * sum(p_grid[dev,d,t] 
                       for t in time_steps) for d in days) * dt)
        
        model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["el"] *  
                                       el_total_hp * eco["el"]["el_hp"]["var"][0])
                
        #Gas:
        dev = "chp"
        gas_total_chp = (dt * sum(clustered["weights"][d] * sum(energy[dev,d,t] 
                         for t in time_steps) for d in days))
        
        model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["gas"] * gas_total_chp *
                                     (eco["gas"]["gas_sta"]["var"][0] - eco["energy_tax"])) 
                                                                
        dev = "boiler"
        gas_total_boi = (dt * sum(clustered["weights"][d] * sum(energy[dev,d,t] 
                         for t in time_steps) for d in days))
        
        model.addConstr(c_dem[dev] == (eco["crf"] * eco["b"]["gas"] * 
                                       gas_total_boi * eco["gas"]["gas_sta"]["var"][0]))
									   
        dev = "boiler_gas_old"
        gas_total_boi_old = (dt * sum(clustered["weights"][d] * sum(energy[dev,d,t] 
                         for t in time_steps) for d in days))
        
        model.addConstr(c_dem[dev] == (eco["crf"] * eco["b"]["gas"] * 
                                       gas_total_boi_old * eco["gas"]["gas_sta"]["var"][0]))							   
        
        #Pellet
        dev = "pellet"
        
        pel_total = (dt * sum(clustered["weights"][d] * sum(energy[dev,d,t]
                     for t in time_steps) for d in days))
        
        model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["pel"] * pel_total *
                                      eco["pel"]["pel_sta"]["var"][0])
									  
		#Oil
        dev = "boiler_oil_old"
        
        oil_total_old = (dt * sum(clustered["weights"][d] * sum(energy[dev,d,t]
                     for t in time_steps) for d in days))
        
        model.addConstr(c_dem[dev] == eco["crf"] * eco["b"]["oil"] * oil_total_old *
                                      eco["oil"]["oil_sta"]["var"][0])        
	
        #%% Fixed administration costs:                    
                         
        # Electricity
        model.addConstr(c_fix["el"] == eco["el"]["el_sta"]["fix"][0])
                                                 
        # Gas
        model.addConstr(c_fix["gas"] == eco["gas"]["gas_sta"]["fix"][0])
                                                                                                                           
        #%% Revenues for selling chp-electricity to the grid
        
        for dev in ("chp", "pv"):      
            model.addConstr(revenue[dev] == eco["b"]["eex"] * eco["crf"] * dt * 
                                            eco["price_sell_el"] *
                                            sum(clustered["weights"][d] * 
                                            sum(p_sell[dev,d,t]
                                            for t in time_steps) 
                                            for d in days),
                                        name="Feed_in_rev_"+dev)
                                            
                                                                                           
#%% TECHNICAL CONSTRAINTS                                        
                                        
		#%%Space heating consumption in accordance with DIN V 4108
        		
        for d in days:
            for t in time_steps:
                if clustered["temp_mean_daily"][d] >= 15:
                        model.addConstr(heat_mod[d,t] == 0)
                else:  
                        model.addConstr(heat_mod[d,t] >= Q_Ht[d,t] + Q_vent_loss[d,t] - Q_s[d,t] - clustered["int_gains"][d,t])
                        model.addConstr(heat_mod[d,t] <= Q_Ht[d,t] + Q_vent_loss[d,t]) 


        #Transmission losses for windows, wall, rooftop and ground incl. surcharge for thermal bridges 
        #as a function of the selected u-values and the temperature difference:
        
        #It is only possible to choose one scenrio per shellpart
        for dev in building_components:    
            model.addConstr(sum(x_restruc[dev,n] for n in restruc_scenarios) == 1)

		#Transmission losses
          
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
        
        df_windows=pd.DataFrame()
        
        for d in days:
            if clustered["temp_mean_daily"][d] <-5:
                    df_windows[d]=df_vent["<-5"]
            elif clustered["temp_mean_daily"][d] <0:
                    df_windows[d]=df_vent["<0"]
            elif clustered["temp_mean_daily"][d] <3:
                    df_windows[d]=df_vent["<3"]
            elif clustered["temp_mean_daily"][d] <6:
                    df_windows[d]=df_vent["<6"]
            elif clustered["temp_mean_daily"][d] <9:
                    df_windows[d]=df_vent["<9"]
            elif clustered["temp_mean_daily"][d] <12:
                    df_windows[d]=df_vent["<12"]
            elif clustered["temp_mean_daily"][d] <15:
                    df_windows[d]=df_vent["<15"]
            elif clustered["temp_mean_daily"][d] <18:
                    df_windows[d]=df_vent["<18"]
            elif clustered["temp_mean_daily"][d] <21:
                    df_windows[d]=df_vent["<21"]
            elif clustered["temp_mean_daily"][d] <24:
                    df_windows[d]=df_vent["<24"]
            elif clustered["temp_mean_daily"][d] <27:
                    df_windows[d]=df_vent["<27"]
            else:
                    df_windows[d]=df_vent[">27"]
                
		#Window profiles regarding daily average ambient temperature

        air_flow1 = {}                          # Zwischenwert für Maximum (linke Seite)
        air_flow2 = {}                          # Zwischenwert für MaximuM (rechte Seite)
        air_flow  = {}                          # Max von air_flow1 & 2
        
        for d in days:
            for t in time_steps:
                air_flow1[d,t] = (1/3 * vent["sci"]["C_D"] * 
								  3600 * (vent["sci"]["g"] * 
								  vent["tec"]["h_w_st"] * 
								  clustered["temp_delta"][d,t] /
                                 (clustered["temp_ambient"][d,t] + 273)) ** 0.5)
								 
                air_flow2[d,t] = (0.05 * (1.36 * clustered["wind_speed"][d,t] *
									vent["sci"]["ln_H_z"]) * 3600) 
                
                air_flow[d,t] = (air_flow1[d,t] ** 2 + air_flow2[d,t] ** 2)**0.5
    
        factor_q_v = building["dimensions"]["Area"]/70*vent["tec"]["A_w_tot"]/2
        
        Q_v_vol = {}
        Q_v_arg_in = {}
        for d in days: # einströmender Luftmassenstrom
            for t in time_steps:
                if clustered["temp_mean_daily"][d] >= 15:
                    Q_v_vol[d,t]=0
                    Q_v_arg_in[d,t]=0
                else:
                    Q_v_vol[d,t] = (factor_q_v*air_flow[d,t]*df_windows[d][t])
                    Q_v_arg_in[d,t] = (Q_v_vol[d,t]*(clustered["temp_ambient"][d,t]+273.15)/(273.15+20)*
                                      clustered["temp_delta"][d,t]*0.34/1000)

    #% Infiltration nach DIN 1946-6        
        
        if MFH == 0:
            
            for n in range(18,36):
                model.addConstr(ventilation_concept[n] == 0)
    
            for n in range(18):
                model.addConstr(ventilation_concept[n] >=   sum(vent["n_50_table"]["SFH"]["Window"][scen][n] * x_restruc["Window", scen] + 
                                                            (1 - vent["n_50_table"]["SFH"]["Window"][scen][n]) * (1 - x_restruc["Window", scen]) 
                                                            for scen in ("standard", "retrofit","adv_retr")) + 
                
                                                            sum(vent["n_50_table"]["SFH"]["Rooftop"][scen][n] * x_restruc["Rooftop", scen] + 
                                                            (1 - vent["n_50_table"]["SFH"]["Rooftop"][scen][n]) * (1 - x_restruc["Rooftop", scen]) 
                                                            for scen in ("standard", "retrofit","adv_retr")) + 
                                                            
                                                            vent["n_50_table"]["x_vent"][n] * x_vent +
                                                            (1 - vent["n_50_table"]["x_vent"][n]) * 
                                                            (1 - x_vent) - 6) 
        else:
            for n in range(18,36):
                model.addConstr(ventilation_concept[n] >=   sum(vent["n_50_table"]["MFH"]["Window"][scen][n] * x_restruc["Window", scen] +
                                                            (1 - vent["n_50_table"]["MFH"]["Window"][scen][n]) * (1 - x_restruc["Window", scen]) 
                                                            for scen in ("standard", "retrofit","adv_retr")) + 
                                                            
                                                            sum(vent["n_50_table"]["MFH"]["Rooftop"][scen][n] * x_restruc["Rooftop", scen] +
                                                            (1 - vent["n_50_table"]["MFH"]["Rooftop"][scen][n]) * (1 - x_restruc["Rooftop", scen]) 
                                                            for scen in ("standard", "retrofit","adv_retr")) + 
                                                            
                                                            vent["n_50_table"]["x_vent"][n] * x_vent +
                                                            (1 - vent["n_50_table"]["x_vent"][n]) * 
                                                            (1 - x_vent) - 6)                 
                                                            
            for n in range(18):
                model.addConstr(ventilation_concept[n] == 0)
                                                     
        model.addConstr(n_50 == sum(ventilation_concept[n] * vent["n_50_table"]["n_50"][n] for n in ventilation_concept.keys()))
        
        for n in range(9):
            model.addConstr(x_vent_concept[n]          >=   sum(vent["x_vent_table"]["Window"][scen][n] * x_restruc["Window", scen] +
                                                            (1 - vent["x_vent_table"]["Window"][scen][n]) * (1 - x_restruc["Window", scen])
                                                            for scen in ("standard", "retrofit","adv_retr")) +
                                                            
                                                            sum(vent["x_vent_table"]["Rooftop"][scen][n] * x_restruc["Rooftop", scen] +
                                                            (1 - vent["x_vent_table"]["Rooftop"][scen][n]) * (1 - x_restruc["Rooftop", scen])
                                                            for scen in ("standard", "retrofit","adv_retr"))
                                                            
                                                            - 5)
                                                            
															
        model.addConstr(1 == sum(x_vent_concept[n] for n in x_vent_concept.keys()))

        model.addConstr(1 == sum(ventilation_concept[n] for n in ventilation_concept.keys()))
           
        model.addConstr(x_vent <= sum(x_vent_concept[n] * vent["x_vent_table"]["x_vent"][n] for n in x_vent_concept.keys()))
        
        
        Q_v_Inf_vol ={}
        
        for d in days:
            for t in time_steps:
                if clustered["temp_mean_daily"][d] >= 15:
                    model.addConstr(Q_v_Inf_wirk[d,t] == 0)
                    model.addConstr(n_total[d,t] == 0)
                else:
                    Q_v_Inf_vol[d,t] =  (vent["tec"]["e_z"] * n_50  *
                                        building["dimensions"]["Area"]*building["dimensions"]["Volume"])
                    model.addConstr(Q_v_Inf_wirk[d,t] == Q_v_Inf_vol[d,t] * 0.34 *(clustered["temp_ambient"][d,t]+273.15)/
                                                    (273.15+20)*clustered["temp_delta"][d,t]/1000)    
                    
                    model.addConstr(n_total[d,t] == (Q_v_Inf_vol[d,t]+Q_v_vol[d,t])/(building["dimensions"]["Area"]*
                                                building["dimensions"]["Volume"]))
                         
        # Lüftungswärmeverluste        
        for d in days:
            for t in time_steps:
                model.addConstr(Q_vent_loss[d,t] == Q_v_arg_in[d,t] + Q_v_Inf_wirk[d,t])
                
#        
#        #Lüftungswärmeverluste        
#        for d in days:
#            for t in time_steps:
#                model.addConstr(Q_vent_loss[d,t] == 0)
                                                    
        
        #Solar Gains for all windowareas as a function of the solar radiation 
        #of the respective direction:
        #Correction factors in accordance with DIN V 4108 and EnEV                                    
        F_solar = 0.9 * 1 * 0.7 * 0.85
        
        for d in days:
            for t in time_steps:
                model.addConstr(Q_s[d,t] == F_solar * sum(x_restruc["Window",n] * 
                                            building["U-values"][n]["Window"]["G-Value"] 
                                            for n in restruc_scenarios)  *   
                                            building["dimensions"]["Area"] *
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
        
        for dev in ("boiler","pellet", "boiler_gas_old", "boiler_oil_old"):
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
                                                            name="Energy_equation_"+
                                                            dev+"_"+timetag)
                    
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
                    
                    M = devs[dev]["Q_nom_max"]
                    for temp in b_TVL.keys():
                        model.addConstr(lin_TVL[temp,dev,d,t] <= M * b_TVL[temp])
                        
                        model.addConstr(heat[dev,d,t] - lin_TVL[temp,dev,d,t] >= 0)
                        
                        model.addConstr(heat[dev,d,t] - lin_TVL[temp,dev,d,t] <=
                                                          M * (1 - b_TVL[temp]))
                
#%% Solar components

        dev = "pv"
        eta_inverter = 0.97
        
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
                                    ch["bat",d,t] == p_grid["grid_house",d,t] + 
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
                                    ch["bat",d,t] == p_grid["grid_house",d,t] + 
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
                
#%% CO2-Emissions
            
        emission_pellet = eco["pel"]["pel_sta"]["emi"] * pel_total

        emissions_gas = eco["gas"]["gas_sta"]["emi"] * (gas_total_chp + gas_total_boi + gas_total_boi_old)
		
        emissions_oil = eco["oil"]["oil_sta"]["emi"] * oil_total_old
        
        emissions_grid = eco["el"]["el_sta"]["emi"] * (el_total_hp + el_total_house)
               
        emissions_feedin = 0.566 * sum(clustered["weights"][d] * dt * 
                                   sum(sum(p_sell[dev,d,t] 
                                   for dev in ("pv","bat","chp"))
                                   for t in time_steps) for d in days)
        
        model.addConstr(emission == emission_pellet + 
                                    emissions_gas +
                							  emissions_oil +
                                    emissions_grid - 
                                    emissions_feedin)
									        
        model.addConstr(0.001 * emission <= max_emi)

#%% Define Scenarios
         
        if options["scenario"] == "free":
            pass
        
        elif options ["scenario"] == "benchmark":
            model.addConstr(x["boiler"] == 1)
            model.addConstr(x["boiler_gas_old"] == 0)
            model.addConstr(x["boiler_oil_old"] == 0)
            model.addConstr(x["chp"] == 0)
            model.addConstr(x["hp_geo"] == 0)
            model.addConstr(x["hp_air"] == 0)
            model.addConstr(x["eh"] == 0)
            model.addConstr(x["pellet"] == 0)
            model.addConstr(x["bat"] == 0)
            model.addConstr(x["stc"] == 0)
            model.addConstr(x["pv"] == 0)
            model.addConstr(x_vent == 0)
            for i in building_components:
                model.addConstr(x_restruc[i,"standard"] == 1)
     
	 
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
        model.Params.TimeLimit = 250
        model.Params.MIPGap = 0.02
        model.Params.NumericFocus = 3
        model.Params.MIPFocus = 3
        model.Params.Aggregate = 1

        #Execute calculation
        model.optimize()
                        
 #%%Check feasibility
#                       
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
        for dev in ("pellet", "stc", "boiler", "hp_geo", "hp_air", "eh", "chp", "boiler_gas_old", "boiler_oil_old"):
            res_y[dev] = np.array([[y[dev,d,t].X for t in time_steps] for d in days])

        # heat and electricity output
        res_power = {}
        res_heat  = {}
        res_energy = {}
        for dev in ("boiler", "chp", "hp_air", "hp_geo", "eh", "stc", "pellet", "boiler_gas_old", "boiler_oil_old"): 
            res_heat[dev]  = np.array([[heat[dev,d,t].X for t in time_steps] for d in days])
       
        for dev in ("hp_air", "hp_geo", "eh"):
            res_power[dev] = np.array([[power[dev,d,t].X for t in time_steps] for d in days]) 
     
        for dev in ("boiler", "chp", "pellet"):
            res_energy[dev] = np.array([[energy[dev,d,t].X for t in time_steps] for d in days])

        # State of charge for storage systems
        res_soc = {}
        for dev in storage:
            res_soc[dev] = np.array([[soc[dev,d,t].X for t in time_steps] for d in days])
    
        # Purchased power from the grid for either feeding a hp tariff component or a different (standard/eco tariff)
        res_p_grid = {}
        res_p_grid["house"] = np.array([[p_grid["grid_house",d,t].X 
                                        for t in time_steps] for d in days])
    
        res_p_grid["hp"]    = np.array([[p_grid["grid_hp",d,t].X  
                                        for t in time_steps] for d in days])

        # Charge and discharge power for storage
        res_ch  = {}
        res_dch = {}
        for dev in ("bat","tes"):           
            res_ch[dev]  = np.array([[ch[dev,d,t].X for t in time_steps] for d in days])
    
            res_dch[dev] = np.array([[dch[dev,d,t].X for t in time_steps] for d in days])

        # Power going from an electricity offering component to the demand/the grid/a hp tariff component
        res_p_use  = {}
        res_p_sell = {}
        res_p_hp   = {}
        for dev in ("pv", "bat","chp"):
            res_p_use[dev]  = np.array([[p_use[dev,d,t].X  
                                        for t in time_steps] for d in days])
    
            res_p_sell[dev] = np.array([[p_sell[dev,d,t].X 
                                        for t in time_steps] for d in days])
    
            res_p_hp[dev]   = np.array([[p_hp[dev,d,t].X  
                                        for t in time_steps] for d in days])
        
        # Costs
        res_c_inv   = {dev: c_inv[dev].X    for dev in c_inv.keys()}
        res_c_om    = {dev: c_om[dev].X     for dev in c_om.keys()}
        res_c_dem   = {dev: c_dem[dev].X    for dev in c_dem.keys()}
        res_c_fix   = {dev: c_fix[dev].X    for dev in c_fix.keys()}
        res_rev     = {dev: revenue[dev].X  for dev in revenue.keys()}
        
        res_c_total =   (sum(res_c_inv[key]  for key in c_inv.keys())
                       + sum(res_c_om[key]   for key in c_om.keys())
                       + sum(res_c_dem[key]  for key in c_dem.keys())
                       + sum(res_c_fix[key]  for key in c_fix.keys())
                       - sum(res_rev[key]    for key in revenue.keys()))  

        res_power_nom = {}
        res_heat_nom = {}
        for dev in heater:
            res_heat_nom[dev] = np.array([[heat_nom[dev,d,t].X 
                                          for t in time_steps] for d in days])

        for dev in ("hp_air","hp_geo"):
            res_power_nom[dev] = np.array([[power_nom[dev,d,t].X 
                                           for t in time_steps] for d in days])        
       
        res_cap = {dev : capacity[dev].X for dev in capacity.keys()}
        
        res_eh_split = {}
        for dev in ("eh_w/o_hp","eh_w/_hp"):
            res_eh_split[dev] = np.array([[eh_split[dev,d,t].X 
                                          for t in time_steps] for d in days])
            
        res_heat_mod = {}  
        res_heat_mod[d,t] = np.array([[heat_mod[d,t].X for t in time_steps] for d in days])
                
        res_Q_Ht = {}
        res_Q_Ht[d,t] = np.array([[Q_Ht[d,t].X for t in time_steps] for d in days])
        
        res_Q_vent_loss = {}
        res_Q_vent_loss[d,t] = np.array([[Q_vent_loss[d,t].X for t in time_steps] for d in days])
        
        res_Q_v_Inf_wirk = {}
        res_Q_v_Inf_wirk[d,t] = np.array([[Q_v_Inf_wirk[d,t].X for t in time_steps] for d in days])
        
        res_n_total = {}
        res_n_total[d,t] = np.array([[n_total[d,t].X for t in time_steps] for d in days])
        
#        res_n_50 = n_50.X
        
        res_Qs = {}
        res_Qs[d,t] = np.array([[Q_s[d,t].X for t in time_steps] for d in days])

        res_x_restruc = {}
        for n in restruc_scenarios:
            for dev in building_components:
                res_x_restruc[dev,n] = x_restruc[dev,n].X 

        # Emissions 
        #res_emission_max = max_emi
        res_emission = emission.X / 1000
        
        res_x_vent  = x_vent.X
        res_n_50    = n_50.X
        
        if options["store_start_vals"]:
            with open(options["filename_start_vals"], "w") as fout:
                for var in model.getVars():
                    if var.VType == "B":
                        fout.write(var.VarName + "\t" + str(int(var.X)) + "\n")

        # Save results 
        with open(options["filename_results"], "wb") as fout:
            pickle.dump(res_x, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_y, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_power, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_heat, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_energy, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_p_grid, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_soc, fout, pickle.HIGHEST_PROTOCOL)
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
            pickle.dump(res_emission, fout, pickle.HIGHEST_PROTOCOL)  
            pickle.dump(model.Runtime, fout, pickle.HIGHEST_PROTOCOL)  
            pickle.dump(model.MIPGap, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_cap, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_heat_mod, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_x_restruc, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_Qs, fout, pickle.HIGHEST_PROTOCOL)     
            pickle.dump(res_Q_vent_loss, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_n_total, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_Q_v_Inf_wirk, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_Q_Ht, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_x_vent, fout, pickle.HIGHEST_PROTOCOL)
            pickle.dump(res_n_50, fout, pickle.HIGHEST_PROTOCOL)

        # Return results
        return(res_c_total, res_emission)

    except gp.GurobiError as e:
        print("")        
        print("Error: "+e.message)