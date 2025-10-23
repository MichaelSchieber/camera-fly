import bpy
from bpy.types import Panel, UILayout, Operator
from .__init__ import get_version

# Store help visibility state
if not hasattr(bpy.types.WindowManager, 'camerafly_show_help'):
    bpy.types.WindowManager.camerafly_show_help = bpy.props.BoolProperty(default=False)

# UI Helper Functions
def draw_shortcut(layout: UILayout, label: str, keys: list, description: str = ""):
    """Simplified helper function to draw keyboard shortcuts"""
    row = layout.row(align=True)
    control_col = row.column(align=True)
    control_col.label(text=label + ":")

    key_col = row.column(align=True)
    key_row = key_col.row(align=True)
    key_row.alignment = 'RIGHT'
    # Draw the keys
    for i, key in enumerate(keys):
        if i > 0:
            key_row.label(text="+")
        key_row.label(text=key, icon='EVENT_' + key if hasattr(bpy.types.UILayout, 'EVENT_' + key) else 'NONE')

    # Add description as tooltip
    #if description:
    #    row.label(text="", icon='INFO')
    #    row.tooltip_text = description

def draw_setting(layout, settings, prop_name, label, suffix=""):
    """Simplified helper function to draw a setting"""
    row = layout.row(align=True)
    row.label(text=label + ":")
    row.prop(settings, prop_name, text="")
    if suffix:
        row.label(text=suffix)

def draw_help_section(layout):
    """Draw the help section with all shortcuts organized by function"""
    help_box = layout.box()
    help_box.label(text="Shortcuts Reference", icon='HELP')

    col = help_box.column()

    # Left column - Movement & Camera
    col.label(text="Movement:", icon='ARROW_LEFTRIGHT')
    draw_shortcut(col, "Forward/Back", ["W", "S"])
    draw_shortcut(col, "Left/Right", ["A", "D"])
    draw_shortcut(col, "Up/Down", ["E", "Q"])
    draw_shortcut(col, "Adjust Speed", ["SHIFT", "CTRL"], "Hold to modify speed")

    col.separator()
    col.label(text="Camera:", icon='CAMERA_DATA')
    draw_shortcut(col, "Yaw/Pitch", ["MOUSE"], "Mouse movement")
    draw_shortcut(col, "Toggle Mode", ["ALT"], "Camera/Aim modes")

    # Right column - Aim & Animation
    col.separator()
    col.label(text="Aim:", icon='TRACKER')
    draw_shortcut(col, "Forward", ["WHEELUP"], "Increase focal distance")
    draw_shortcut(col, "Backward", ["WHEELDOWN"], "Decrease focal distance")

    col.separator()
    col.label(text="Animation:", icon='KEYINGSET')
    draw_shortcut(col, "Keyframe", ["I"], "Insert keyframe")
    # draw_shortcut(col, "Loc Only", ["I", "SHIFT"], "Location keyframe")
    # draw_shortcut(col, "Rot Only", ["I", "CTRL"], "Rotation keyframe")


    # Actions at bottom
    col.separator()
    action_row_1 = col.row()
    action_col_1 = action_row_1.column()
    action_col_2 = action_row_1.column()
    action_col_1.alignment = 'LEFT'
    action_col_2.alignment = 'RIGHT'
    action_col_1.label(text="Accept:", icon='CHECKMARK')
    action_col_2.label(text="LEFTMOUSE / SPACE")
    action_col_1.label(text="Exit:", icon='X')
    action_col_2.label(text="RIGHTMOUSE / ESC")


class CAMERAFLY_PT_main_panel(Panel):
    """Creates a Panel in the 3D Viewport Toolbar"""
    bl_label = "Camera Fly Controls"
    bl_idname = "CAMERAFLY_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_context = ""
    bl_order = 10000

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        wm = context.window_manager

        # Check if camera fly settings exist
        has_settings = hasattr(scene, 'camerafly_settings') and scene.camerafly_settings is not None
        settings = scene.camerafly_settings if has_settings else None

        # Minimal compact header with help toggle
        header_row = layout.row(align=True)
        header_row.label(text=f"Camera Fly", icon='CAMERA_DATA')

        # Help toggle
        help_icon = 'HIDE_ON' if wm.camerafly_show_help else 'HELP'
        header_row.operator("wm.context_toggle", text="", icon=help_icon).data_path = "window_manager.camerafly_show_help"

        # Show help if enabled
        if wm.camerafly_show_help:
            draw_help_section(layout)

        layout.separator()
        content_area = layout.column(align=True)
        content_area.scale_y = 0.9  # Slightly more compact content
        col = content_area.column(align=True)

        if has_settings:
            # All settings in compact layout
            
            # Camera selection
            cam_box = col.box()
            cam_box.label(text="Camera", icon='OUTLINER_OB_CAMERA')
            cam_col = cam_box.column()
            cam_row = cam_col.row()
            cam_row.prop_search(settings, "active_camera", scene, "objects", text="", icon='CAMERA_DATA')

            col.separator()
            # Rotation Mode
            mode_box = col.box()
            mode_box.label(text="Rotation Mode", icon='ORIENTATION_GIMBAL')
            mode_col = mode_box.column()
            row = mode_col.row()
            mode_icon = 'CAMERA_DATA' if settings.rotation_mode == 'CAMERA' else 'PIVOT_BOUNDBOX'
            row.label(text=f"Mode:", icon=mode_icon)
            row.prop(settings, "rotation_mode", text="")

            # Brief mode description
            info = "Camera rotates directly" if settings.rotation_mode == 'CAMERA' else "Camera rotates around Aim target"
            mode_col.label(text=info, icon='INFO')

            col.separator()

            # Speed settings in compact rows
            speeds_box = col.box()
            speeds_box.label(text="Speed Settings", icon='SORTTIME')
            speeds_col = speeds_box.column()
            draw_setting(speeds_col, settings, "move_speed", "Movement", "units")
            draw_setting(speeds_col, settings, "rotate_speed_deg", "Rotation", "deg")
            draw_setting(speeds_col, settings, "aim_distance_step", "Aim", "units")

            # Key shortcuts reminder
            col.separator()
            shortcut_box = col.box()
            shortcut_box.label(text="Key Shortcuts", icon='KEYINGSET')
            shortcut_col = shortcut_box.column(align=True)
            shortcut_col.label(text="• SHIFT/CTRL - Adjust speed")
            shortcut_col.label(text="• ALT - Toggle rotation mode")
            shortcut_col.label(text="• I - Insert keyframe")
            
            # Fly button
            fly_row = layout.row()
            fly_row.scale_y = 1.5
            fly_op = fly_row.operator("pose.move_rotate_bone_local_pivot", text="Fly", icon='PLAY')


        # Add some space at the bottom
        layout.separator()


        cancel_col = layout.column(align=True)
        cancel_col.label(text="Exit Operator", icon='INFO')

        accept_row = cancel_col.row()
        accept_row.label(text="To Accept", icon='CHECKMARK')
        accept_row.label(text="SPACE")

        cancel_row = cancel_col.row()
        cancel_row.label(text="To Cancel", icon='X')
        cancel_row.label(text="RIGHT MOUSE")

        layout.separator()

        version_row = layout.row()
        version_row.alignment = 'CENTER'
        version_row.label(text="CameraFly v" + str(get_version()))