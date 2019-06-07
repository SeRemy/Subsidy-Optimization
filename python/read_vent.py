# -*- coding: utf-8 -*-
"""
Created on Thu May 23 11:19:56 2019

@author: srm-jba
"""

import xlrd
import numpy as np
import pandas as pd

def read_vent(filename="raw_inputs/vent.xlsx"):
    
    book = xlrd.open_workbook(filename)
    
    sheet_eco  = book.sheet_by_name("eco_params")    
    sheet_tec  = book.sheet_by_name("tec_params")
    sheet_sci  = book.sheet_by_name("sci_params")
    sheet_n_50_table = book.sheet_by_name("n_50_table")
    
    vent = {}
    
    vent["eco"] = {}
    vent["eco"]["phi_heat_recovery"]    = sheet_eco.cell_value(1,1)
    vent["eco"]["price_a"]              = sheet_eco.cell_value(1,1)
    vent["eco"]["price_b"]              = sheet_eco.cell_value(1,1)
    
    vent["tec"] = {}
    vent["tec"]["h_w_st"]               = sheet_tec.cell_value(1,1)
    vent["tec"]["A_w_tot"]              = sheet_tec.cell_value(2,1)
    vent["tec"]["e_z"]                  = sheet_tec.cell_value(3,1)
    
    vent["sci"] = {}
    vent["sci"]["rho_a_ref"]            = sheet_sci.cell_value(1,1)
    vent["sci"]["cp_air"]               = sheet_sci.cell_value(2,1)
    vent["sci"]["c_wnd"]                = sheet_sci.cell_value(3,1)
    vent["sci"]["c_st"]                 = sheet_sci.cell_value(4,1)
    vent["sci"]["C_D"]                  = sheet_sci.cell_value(5,1)
    vent["sci"]["g"]                    = sheet_sci.cell_value(6,1)
    vent["sci"]["H_gz"]                 = sheet_sci.cell_value(7,1)
    vent["sci"]["z_0"]                  = sheet_sci.cell_value(8,1)
    vent["sci"]["ln_H_z"]               = sheet_sci.cell_value(9,1)
    
    vent["n_50_table"] = {}
    vent["n_50_table"]["counter"] ={}
    vent["n_50_table"]["n_50"] ={}
    vent["n_50_table"]["SFH"] ={}
    vent["n_50_table"]["MFH"] ={}
    vent["n_50_table"]["x_vent"] ={}
    
    vent["n_50_table"]["SFH"]["Window"] ={}
    vent["n_50_table"]["SFH"]["Rooftop"] ={}
    vent["n_50_table"]["MFH"]["Window"] ={}
    vent["n_50_table"]["MFH"]["Rooftop"] ={}
    
    vent["n_50_table"]["SFH"]["Window"]["standard"] ={}
    vent["n_50_table"]["SFH"]["Window"]["retrofit"] ={}
    vent["n_50_table"]["SFH"]["Window"]["adv_retr"] ={}
    vent["n_50_table"]["SFH"]["Rooftop"]["standard"] ={}
    vent["n_50_table"]["SFH"]["Rooftop"]["retrofit"] ={}
    vent["n_50_table"]["SFH"]["Rooftop"]["adv_retr"] ={}
    
    vent["n_50_table"]["MFH"]["Window"]["standard"] ={}
    vent["n_50_table"]["MFH"]["Window"]["retrofit"] ={}
    vent["n_50_table"]["MFH"]["Window"]["adv_retr"] ={}
    vent["n_50_table"]["MFH"]["Rooftop"]["standard"] ={}
    vent["n_50_table"]["MFH"]["Rooftop"]["retrofit"] ={}
    vent["n_50_table"]["MFH"]["Rooftop"]["adv_retr"] ={}
    
    for n in range(0, sheet_n_50_table.nrows-3):
        vent["n_50_table"]["counter"][n] = sheet_n_50_table.cell_value(n+3,0)
        vent["n_50_table"]["n_50"][n] = sheet_n_50_table.cell_value(n+3,1)
        
        vent["n_50_table"]["SFH"]["Window"]["standard"][n] = sheet_n_50_table.cell_value(n+3,2)
        vent["n_50_table"]["SFH"]["Window"]["retrofit"][n] = sheet_n_50_table.cell_value(n+3,3)
        vent["n_50_table"]["SFH"]["Window"]["adv_retr"][n] = sheet_n_50_table.cell_value(n+3,4)
        vent["n_50_table"]["SFH"]["Rooftop"]["standard"][n] = sheet_n_50_table.cell_value(n+3,5)
        vent["n_50_table"]["SFH"]["Rooftop"]["retrofit"][n] = sheet_n_50_table.cell_value(n+3,6)
        vent["n_50_table"]["SFH"]["Rooftop"]["adv_retr"][n] = sheet_n_50_table.cell_value(n+3,7)
        
        vent["n_50_table"]["MFH"]["Window"]["standard"][n] = sheet_n_50_table.cell_value(n+3,8)
        vent["n_50_table"]["MFH"]["Window"]["retrofit"][n] = sheet_n_50_table.cell_value(n+3,9)
        vent["n_50_table"]["MFH"]["Window"]["adv_retr"][n] = sheet_n_50_table.cell_value(n+3,10)
        vent["n_50_table"]["MFH"]["Rooftop"]["standard"][n] = sheet_n_50_table.cell_value(n+3,11)
        vent["n_50_table"]["MFH"]["Rooftop"]["retrofit"][n] = sheet_n_50_table.cell_value(n+3,12)
        vent["n_50_table"]["MFH"]["Rooftop"]["adv_retr"][n] = sheet_n_50_table.cell_value(n+3,13)
        
        vent["n_50_table"]["x_vent"][n] = sheet_n_50_table.cell_value(n+3,14)
    
    df_vent=pd.read_csv("raw_inputs/vent/vent_temp_sorted.csv", sep=";", header=0, engine = "python")
    df_vent.columns=["hour", "<-5", "<0", "<3", "<6", "<9", "<12", "<15", "<18", "<21", "<24", "<27", ">27"]
    
    return(vent, df_vent)
    
    


