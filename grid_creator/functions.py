from os import path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import geopandas as gpd
import pandas as pd
import pygmt
import rasterio
from rasterio.transform import from_bounds
import xarray as xr

class GeoTIFFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GeoTIFF Generator")

        self.points_file = tk.StringVar()
        # self.coastline_file = tk.StringVar()
        self.grid_step = tk.DoubleVar(value=1.0)
        self.gridding_method = tk.StringVar(value="Minimal Curvature")
        self.elevation = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        self.create_label("Select Points GeoPackage File:")
        self.create_entry_button(self.points_file, "Browse", self.select_points_file)

        self.create_label("Select Elevation:")
        frame = tk.Frame(self.root)
        frame.pack(anchor="w", padx=10, pady=5)

        self.column_menu = ttk.Combobox(frame, state="readonly", textvariable=self.elevation)
        self.column_menu.pack(side=tk.LEFT)

        # self.create_label("Select Coastline GeoPackage (Optional):")
        # self.create_entry_button(self.coastline_file, "Browse", self.select_coastline_file)

        self.create_label("Grid Step (in arcsec):")
        tk.Entry(self.root, textvariable=self.grid_step).pack(padx=10, pady=5)

        self.create_label("Select Gridding Method:")
        gridding_options = ["Minimal Curvature", "Triangulate"]
        tk.OptionMenu(self.root, self.gridding_method, *gridding_options).pack(padx=10, pady=5)

        tk.Button(self.root, text="Generate GeoTIFF", command=self.generate_geotiff).pack(pady=20)
        tk.Button(self.root, text="Close", command=self.close_app).pack(pady=10)

    def create_label(self, text):
        label = tk.Label(self.root, text=text)
        label.pack(anchor="w", padx=10, pady=5)

    def create_entry_button(self, var, button_text, command):
        frame = tk.Frame(self.root)
        entry = tk.Entry(frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, padx=5)
        button = tk.Button(frame, text=button_text, command=command)
        button.pack(side=tk.LEFT)
        frame.pack(anchor="w", padx=10, pady=5)
    
    def update_column_menu(self, file_path):
        points = gpd.read_file(file_path)
        columns = points.columns.tolist()
        self.column_menu['values'] = columns
        if columns:
            self.column_menu.current(0)
            self.elevation.set(columns[0])

    def select_points_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Shapefiles", "*.gpkg")])
        if file_path:
            self.points_file.set(file_path)
            self.update_column_menu(file_path)

    # def select_coastline_file(self):
    #     file_path = filedialog.askopenfilename(filetypes=[("Shapefiles", "*.gpkg")])
    #     if file_path:
    #         self.coastline_file.set(file_path)

    def generate_geotiff(self):
        if not self.points_file.get():
            messagebox.showwarning("Warning", "Please select both contour and points files.")
            return

        points = gpd.read_file(self.points_file.get())
        # coastlines = gpd.read_file(self.coastline_file.get()) if self.coastline_file.get() else None
        x_inc = self.grid_step.get() / 3600.0
        y_inc = self.grid_step.get() / 3600.0

        netcdf_path = f'{path.splitext(self.points_file.get())[0]}_{self.gridding_method.get().lower().replace(' ', '_')}_{self.grid_step.get()}s.nc'

        self.grid_by_gmt(
            gdf=points,
            x_inc=x_inc,
            y_inc=y_inc,
            output_path=netcdf_path,
            method=self.gridding_method.get()
        )

        geotiff_path = filedialog.asksaveasfilename(
            defaultextension=".tif",
            initialfile=f'{path.splitext(netcdf_path)[0]}.tif',
            filetypes=[("GeoTIFF", "*.tif")]
        )
        self.convert_netcdf_to_geotiff(netcdf_path, geotiff_path)

        messagebox.showinfo("Success", f"GeoTIFF saved to {geotiff_path}")

    def grid_by_gmt(self, gdf, x_inc, y_inc, output_path, method='Minimal Curvature', region=None):

        data = pd.DataFrame(
            {
                "longitude": gdf.geometry.x,
                "latitude": gdf.geometry.y,
                "height": gdf[self.elevation.get()]
            }
        )

        if region is None:
            region = pygmt.info(
                data[["longitude", "latitude"]],
                per_column=True,
                spacing=f"{x_inc}/{y_inc}",
            )

        match method:
            case 'Minimal Curvature':
                blocks = pygmt.blockmedian(
                    data=data,
                    spacing=f"{x_inc}/{y_inc}",
                    region=region,
                    verbose='e'
                )

                pygmt.surface(
                    data=blocks,
                    region=region,
                    spacing=f"{x_inc}/{y_inc}",
                    outgrid=output_path,
                    verbose='w',
                )
            case 'Triangulate':
                pygmt.triangulate.regular_grid(
                    data=data,
                    region=region,
                    spacing=f"{x_inc}/{y_inc}",
                    outgrid=output_path,
                    verbose='w',
                )

    def convert_netcdf_to_geotiff(self, netcdf_path, geotiff_path):

        grid = xr.open_dataarray(netcdf_path, engine = 'netcdf4')

        left, right = grid.x.min().item(), grid.x.max().item()
        bottom, top = grid.y.min().item(), grid.y.max().item()

        data = grid.values[::-1]

        with rasterio.open(
            geotiff_path,
            "w",
            driver="GTiff",
            height=grid.shape[0],
            width=grid.shape[1],
            count=1,
            dtype=str(grid.dtype),
            crs="EPSG:4326",
            transform=from_bounds(left, bottom, right, top, grid.shape[1], grid.shape[0]),
        ) as dst:
            dst.write(data, 1)

        return True

    def close_app(self):
        self.root.quit()


