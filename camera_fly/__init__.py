# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Camerafly",
    "author": "Michael Schieber",
    "description": "",
    "blender": (4, 2, 0),
    "version": (1, 0, 3),
    "location": "",
    "warning": "",
    "category": "Generic",
}

import bpy
from . import auto_load
from . import ops

auto_load.init()

def get_version():
    version = bl_info["version"]
    parts = str(version).split(",")
    for i in range(len(parts)):
        parts[i] = ''.join(filter(str.isdigit, parts[i]))

    version = parts[0] + '.' + parts[1] + '.' + parts[2]
        
    return version


def register():
    auto_load.register()
    bpy.types.Scene.camerafly_settings = bpy.props.PointerProperty(type=ops.CameraFlyProperties)
    
    # Register UI property for tab control
    if not hasattr(bpy.types.WindowManager, 'camerafly_active_tab'):
        bpy.types.WindowManager.camerafly_active_tab = bpy.props.IntProperty(default=0)


def unregister():
    # Remove scene settings
    if hasattr(bpy.types.Scene, 'camerafly_settings'):
        del bpy.types.Scene.camerafly_settings
    
    # Remove UI property for tab control
    if hasattr(bpy.types.WindowManager, 'camerafly_active_tab'):
        del bpy.types.WindowManager.camerafly_active_tab
    
    auto_load.unregister()
    
    

