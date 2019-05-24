# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:46:11 2019

@author: srm-jba
"""
import pickle 
import python.read_basic as reader
import pandas as pd

def pick_read(filename):
    
    Outputs = reader.read_results(filename)

    
    return (Outputs["res_heat_mod"], Outputs["res_Q_vent_loss"], Outputs["res_Q_v_Inf_wirk"], Outputs["inputs_clustered"] ["weights"])

filename = "ClusterB_1958 1978_window_rooftop"

Outputs=pick_read(filename)

