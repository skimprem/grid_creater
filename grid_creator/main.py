#!/usr/bin/env python3

import tkinter as tk
from .functions import GeoTIFFApp

def main():
    root = tk.Tk()
    app = GeoTIFFApp(root)
    root.mainloop()