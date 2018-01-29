# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import tkinter as tki

def close_window():
    root.destroy()
    

root = tki.Tk()
root.title("Ente")
root.geometry("600x600")


menu = tki.Menu(root)
root.config(menu=menu)

filmenu = tki.Menu(menu)
menu.add_cascade(label="1", menu=filmenu)

button1 = tki.Button(root, text = "OK")
button1.place(x=30, y=300)
#
entry1  = tki.Entry(root)
entry1.place(x=30, y=220)

button = tki.Button(root, text='Stop', width=25, command=close_window)
button.place(x=150, y=300)


#
#var1 = tki.IntVar()
#tki.Checkbutton(root, text="male", variable=var1).grid(row=1)
#var2 = tki.IntVar()
#tki.Checkbutton(root, text="female", variable=var2).grid(row=2)
#
#tki.Button(root, text='Quit', command = close_window).grid(row=3)

#radio1 = tki.Radiobutton()
#radio1.pack()
#
#spin1 = tki.Spinbox(cnf={"1","2","3"})
#spin1.pack()


logo = tki.PhotoImage(file="ente.png")
w1 = tki.Label(root, image=logo).pack(side="right")

root.mainloop()

