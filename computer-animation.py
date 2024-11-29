import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from svgpathtools import svg2paths
import matplotlib.animation as animation

data = pd.read_csv("carp_data.csv")  

map_image = Image.open("map_image.png")

def get_region_coordinates(region_number):
    file_name = f'region{region_number}.svg'
    
    # Load the SVG file
    paths, attributes = svg2paths(file_name)
    
    region_coordinates = []
    for path in paths:
        for segment in path:
            if segment.__class__.__name__ == 'Line':
                region_coordinates.append((segment.start.real, segment.start.imag))
                region_coordinates.append((segment.end.real, segment.end.imag))
            elif segment.__class__.__name__ == 'CubicBezier':
                region_coordinates.append((segment.start.real, segment.start.imag))
                region_coordinates.append((segment.control1.real, segment.control1.imag))
                region_coordinates.append((segment.control2.real, segment.control2.imag))
                region_coordinates.append((segment.end.real, segment.end.imag))
    
    return region_coordinates

region_paths = {}
for i in range(1, 6):  # Assuming there are 5 regions, from 1 to 5
    region_paths[f"Region {i}"] = get_region_coordinates(i)

# Initialize the plot
fig, ax = plt.subplots(figsize=(10, 10))
ax.imshow(map_image)
ax.axis('off')

# Function to update the plot for each year
def update(year_idx):
    row = data.iloc[year_idx]
    year = row["Year"]
    active_regions = [region for region in row.index if row[region] == "Y" and region != "Year"]
    
    # Clear previous frame
    ax.clear()
    
    # Show the map again
    ax.imshow(map_image)
    ax.set_title(f"Year: {year}", fontsize=16)
    ax.axis('off')
    
    # Highlight the region paths (lines along the river)
    for region, path in region_paths.items():
        if region in active_regions:
            color = "gold"  # Highlight active regions in gold
        else:
            color = "gray"  # Inactive regions in gray
        
        # Plot the path for each region (line along the river)
        ax.plot(*zip(*path), color=color, linewidth=3, linestyle='-', label=region)
        
        # Optionally, add labels or text for each region
        midpoint = path[len(path) // 2]  # Get the midpoint for labeling
        ax.text(midpoint[0], midpoint[1], region, ha="center", color="black", fontsize=12)

# Create an animation object
ani = animation.FuncAnimation(fig, update, frames=len(data), repeat=False)

# Set up the video writer
writer = animation.FFMpegWriter(fps=1, metadata=dict(artist='Me'), bitrate=1800)

# Save the animation as an MP4 file
ani.save('region_highlighting_animation.mp4', writer=writer)

# Optionally, display the plot (if you still want to show it)
plt.show()


def get_region_coordinates(region_number):
    file_name = f'region{region_number}.svg'
    
    # Load the SVG file
    paths, attributes = svg2paths(file_name)
    
    region_coordinates = []
    for path in paths:
        for segment in path:
            if segment.__class__.__name__ == 'Line':
                region_coordinates.append((segment.start.real, segment.start.imag))
                region_coordinates.append((segment.end.real, segment.end.imag))
            elif segment.__class__.__name__ == 'CubicBezier':
                region_coordinates.append((segment.start.real, segment.start.imag))
                region_coordinates.append((segment.control1.real, segment.control1.imag))
                region_coordinates.append((segment.control2.real, segment.control2.imag))
                region_coordinates.append((segment.end.real, segment.end.imag))
    
    return region_coordinates