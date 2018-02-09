# -*- coding: utf-8 -*-
"""
Created on Fri Feb  9 14:46:01 2018

@author: srm
"""
area = 101 
vol_fac = 3.125
Volume = 0.76 * area * vol_fac

#Ventilation losses
ro_cp = 0.34 #Wh/m³K
n = 0.7 #1/h 
H_v = ro_cp * n * Volume
      
# Total heating losses
G_t = 3380 #Kd - Gradtagzahl
f_na = 0.95 #Parameter for switching off the heater in the night
f_ql = 0.024 * G_t * f_na
Q_l =  H_v * f_ql /8760#kWh