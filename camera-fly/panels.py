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
    row.label(text=label + ":")

    # Draw the keys
    for i, key in enumerate(keys):
        if i > 0:
            row.label(text="+")
        row.label(text=key, icon='EVENT_' + key if hasattr(bpy.types.UILayout, 'EVENT_' + key) else 'NONE')

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

    # Two column layout for shortcuts
    row = col.row()
    left_col = row.column()
    right_col = row.column()

    # Left column - Movement & Camera
    left_col.label(text="Movement:", icon='ARROW_LEFTRIGHT')
    draw_shortcut(left_col, "Forward/Back", ["W", "S"])
    draw_shortcut(left_col, "Left/Right", ["A", "D"])
    draw_shortcut(left_col, "Up/Down", ["E", "Q"])
    draw_shortcut(left_col, "Adjust Speed", ["SHIFT", "CTRL"], "Hold to modify speed")

    left_col.separator()
    left_col.label(text="Camera:", icon='CAMERA_DATA')
    draw_shortcut(left_col, "Yaw/Pitch", ["MOUSE"], "Mouse movement")
    draw_shortcut(left_col, "Toggle Mode", ["ALT"], "Camera/Aim modes")

    # Right column - Aim & Animation
    right_col.label(text="Aim:", icon='TRACKER')
    draw_shortcut(right_col, "Forward", ["WHEELUP"], "Increase focal distance")
    draw_shortcut(right_col, "Backward", ["WHEELDOWN"], "Decrease focal distance")

    right_col.separator()
    right_col.label(text="Animation:", icon='KEYINGSET')
    draw_shortcut(right_col, "Keyframe", ["I"], "Insert keyframe")
    draw_shortcut(right_col, "Loc Only", ["I", "SHIFT"], "Location keyframe")
    draw_shortcut(right_col, "Rot Only", ["I", "CTRL"], "Rotation keyframe")

    # Actions at bottom
    col.separator()
    action_row = col.row()
    action_row.label(text="Exit:", icon='PANEL_CLOSE')
    action_row.label(text="ESC / RIGHTMOUSE")


class CAMERAFLY_PT_main_panel(Panel):
    """Creates a Panel in the 3D Viewport Toolbar"""
    bl_label = "Camera Fly Controls"
    bl_idname = "CAMERAFLY_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tools'
    bl_context = ""

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        wm = context.window_manager

        # Check if camera fly settings exist
        has_settings = hasattr(scene, 'camerafly_settings') and scene.camerafly_settings is not None
        settings = scene.camerafly_settings if has_settings else None

        # Minimal compact header with help toggle
        header_row = layout.row(align=True)
        # Title and status in one
        status_text = "Ready" if context.mode == 'POSE' else "Needs Pose Mode"
        status_icon = 'CHECKMARK' if context.mode == 'POSE' else 'ERROR'
        header_row.label(text=f"Camera Fly", icon='CAMERA_DATA')
        header_row.label(text=status_text, icon=status_icon)

        # Help toggle
        help_icon = 'HIDE_ON' if wm.camerafly_show_help else 'HELP'
        header_row.operator("wm.context_toggle", text="", icon=help_icon).data_path = "window_manager.camerafly_show_help"

        # Show help if enabled
        if wm.camerafly_show_help:
            draw_help_section(layout)

        # Compact action row with camera selection and fly button
        if has_settings:
            camera_row = layout.row(align=True)
            # Camera dropdown
            camera_row.prop_search(settings, "active_camera", scene, "objects", text="", icon='CAMERA_DATA')

            # Fly button
            fly_row = layout.row()
            fly_row.scale_y = 1.5
            fly_op = fly_row.operator("pose.move_rotate_bone_local_pivot", text="Fly", icon='PLAY')

            # Compact mode indicator
            mode_row = layout.row()
            mode_icon = 'PIVOT_CURSOR' if settings.rotation_mode == 'CAMERA' else 'PIVOT_BOUNDBOX'
            mode_row.label(text=f"{settings.rotation_mode} Mode", icon=mode_icon)
        else:
            # Fallback if no settings
            layout.label(text="Camera settings not available", icon='ERROR')

        # Create tabs for different control categories
        tab_row = layout.row(align=True)

        # Get active tab (make sure property exists)
        if not hasattr(wm, 'camerafly_active_tab'):
            wm.camerafly_active_tab = 0

        # Compact tab buttons
        tabs = ["Movement", "Camera", "Animation", "Settings"]
        icons = ['ARROW_LEFTRIGHT', 'ORIENTATION_GIMBAL', 'KEYINGSET', 'PREFERENCES']
        for i, (tab, icon) in enumerate(zip(tabs, icons)):
            op = tab_row.operator(
                "wm.context_set_int",
                text=tab,
                icon=icon,
                depress=(wm.camerafly_active_tab == i)
            )
            op.data_path = "window_manager.camerafly_active_tab"
            op.value = i

        # Content area for the active tab
        active_tab = wm.camerafly_active_tab
        content_area = layout.column(align=True)
        content_area.scale_y = 0.95  # Slightly more compact content

        # Movement Tab
        if active_tab == 0:
            col = content_area.column(align=True)

            # Compact key controls - basic movement
            move_box = col.box()
            move_box.label(text="Basic Movement", icon='CON_LOCLIKE')
            move_col = move_box.column()
            draw_shortcut(move_col, "Forward/Back", ["W", "S"])
            draw_shortcut(move_col, "Left/Right", ["A", "D"])
            draw_shortcut(move_col, "Up/Down", ["E", "Q"])

            col.separator()

            # Mouse rotation controls
            rot_box = col.box()
            rot_box.label(text="Mouse Rotation", icon='MOUSE_MOVE')
            rot_col = rot_box.column()
            draw_shortcut(rot_col, "Yaw (Left/Right)", ["MOUSE"], "World Z axis rotation")
            draw_shortcut(rot_col, "Pitch (Up/Down)", ["MOUSE"], "Local X axis rotation")

            col.separator()

            # Mode controls
            mode_box = col.box()
            mode_box.label(text="Rotation Mode", icon='PIVOT_BOUNDBOX')
            mode_col = mode_box.column()
            draw_shortcut(mode_col, "Toggle Mode", ["ALT"], "Switch Camera/Aim modes")

            if has_settings:
                row = mode_col.row()
                mode_icon = 'PIVOT_CURSOR' if settings.rotation_mode == 'CAMERA' else 'PIVOT_BOUNDBOX'
                row.label(text=f"Mode:", icon=mode_icon)
                row.prop(settings, "rotation_mode", text="")

                col.separator()

                # Speed settings in one compact area
                speed_box = col.box()
                speed_box.label(text="Speed Settings", icon='SORTTIME')
                speed_col = speed_box.column()
                draw_setting(speed_col, settings, "move_speed", "Movement", "units/step")
                draw_setting(speed_col, settings, "rotate_speed_deg", "Rotation", "deg/step")

                # Speed tip
                tip_row = speed_box.row()
                tip_row.label(text="Press SHIFT/CTRL to modify speed", icon='INFO')
                tip_row.scale_y = 0.8

        # Camera Tab
        elif active_tab == 1:
            col = content_area.column(align=True)
            # Aim controls
            aim_box = col.box()
            aim_box.label(text="Aim Controls", icon='TRACKER')
            aim_col = aim_box.column()
            draw_shortcut(aim_col, "Forward", ["WHEELUP"], "Increase focus distance")
            draw_shortcut(aim_col, "Backward", ["WHEELDOWN"], "Decrease focus distance")

            col.separator()

            if has_settings:
                col.separator()

                # Speed settings in one compact area
                speed_box = col.box()
                speed_box.label(text="Speed Settings", icon='SORTTIME')
                speed_col = speed_box.column()
                draw_setting(speed_col, settings, "aim_distance_step", "Aim", "units/wheel")




        # Animation Tab
        elif active_tab == 2:
            col = content_area.column(align=True)

            # Keyframe shortcuts
            key_box = col.box()
            key_box.label(text="Keyframe Controls", icon='KEYFRAME')
            key_col = key_box.column()

            # Main keyframe shortcut
            main_row = key_col.row()
            main_row.scale_y = 1.2
            draw_shortcut(main_row, "Insert Keyframe", ["I"], "Insert full keyframe")



            if has_settings:
                col.separator()

                # Targets in compact layout
                target_box = col.box()
                target_box.label(text="Keyframe Targets", icon='ARMATURE_DATA')
                target_col = target_box.column()

                row = target_col.row()
                row.label(text="Root Bone", icon='BONE_DATA')


                row = target_col.row()
                row.label(text="Aim Bone", icon='CONSTRAINT_BONE')

        # Settings Tab
        elif active_tab == 3:
            col = content_area.column(align=True)

            if has_settings:
                # All settings in compact layout

                # Camera selection
                cam_box = col.box()
                cam_box.label(text="Camera", icon='OUTLINER_OB_CAMERA')
                cam_col = cam_box.column()
                cam_row = cam_col.row()
                cam_row.prop_search(settings, "active_camera", scene, "objects", text="")

                col.separator()

                # Rotation Mode
                mode_box = col.box()
                mode_box.label(text="Rotation Mode", icon='ORIENTATION_GIMBAL')
                mode_col = mode_box.column()
                mode_col.prop(settings, "rotation_mode", expand=True)

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
                col.label(text="Key Shortcuts", icon='KEYINGSET')
                shortcut_box = col.box()
                shortcut_col = shortcut_box.column(align=True)
                shortcut_col.label(text="• SHIFT/CTRL - Adjust speed")
                shortcut_col.label(text="• ALT - Toggle rotation mode")
                shortcut_col.label(text="• I - Insert keyframe")

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