
import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import FloatProperty, PointerProperty
from math import radians
from mathutils import Matrix, Vector


class CameraFlyProperties(PropertyGroup):
    """Properties for the CameraFly addon"""

    def camera_poll(self, obj):
        if not obj or obj.type != 'CAMERA':
            return False

        # Check if the camera is part of a valid dolly rig
        if not self.is_valid_dolly_rig(obj):
            return False

        return True

    def is_valid_dolly_rig(self, camera):
        """Check if the camera is part of a valid dolly rig."""
        if not camera or not camera.parent or camera.parent.type != 'ARMATURE':
            return False

        rig = camera.parent
        if 'Root' not in rig.pose.bones or 'Aim' not in rig.pose.bones:
            return False

        return True

    move_speed: FloatProperty(
        name="Move Speed",
        description="Movement speed for bone transformation",
        default=0.1,
        min=0.01,
        max=100.0,
        update=lambda self, context: None  # Needed for undo/redo
    )

    rotate_speed_deg: FloatProperty(
        name="Rotate Speed",
        description="Rotation speed in degrees",
        default=5.0,
        min=0.1,
        max=90.0,
        update=lambda self, context: None  # Needed for undo/redo
    )

    aim_distance_step: FloatProperty(
        name="Aim Distance Step",
        description="Distance to move the aim bone on each mouse wheel movement",
        default=0.2,
        min=0.01,
        max=10.0,
        update=lambda self, context: None  # Needed for undo/redo
    )

    active_camera: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Active Camera",
        description="Camera to use for the fly controls",
        poll=camera_poll
    )

    rotation_mode: bpy.props.EnumProperty(
        name="Rotation Mode",
        description="How the camera rotation is controlled",
        items=[
            ('CAMERA', "Camera", "Rotate the camera directly"),
            ('AIM', "Aim", "Rotate the aim target (Dolly Rig only)")
        ],
        default='AIM' if bpy.app.version >= (2, 80) else 'CAMERA',
        update=lambda self, context: None  # Needed for undo/redo
    )




class POSE_OT_move_rotate_bone_local_pivot(bpy.types.Operator):
    """Move and Rotate pose bone using local orientation and rotate around its own pivot"""
    bl_idname = "pose.move_rotate_bone_local_pivot"
    bl_label = "Move Pose Bone (Local with Pivot)"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    @property
    def move_speed(self):
        # Safely get move_speed from scene properties
        if hasattr(bpy.context.scene, 'camerafly_settings'):
            return bpy.context.scene.camerafly_settings.move_speed
        return 20.0  # Default value if settings not found

    @property
    def rotate_speed_deg(self):
        # Safely get rotate_speed_deg from scene properties
        if hasattr(bpy.context.scene, 'camerafly_settings'):
            return bpy.context.scene.camerafly_settings.rotate_speed_deg
        return 5.0  # Default value if settings not found

    _timer = None
    keys_pressed = set()
    last_matrix = None
    speed_change = False
    rot_mode_change = False
    initial_aim_set = False
    _initial_aim_pos = None
    _initial_root_pos = None

    # Store the camera rig and root bone when the operator is invoked
    _camera_rig = None
    _root_bone = None
    _aim_bone = None

    # Store the last keyframe type
    _last_keyframe_type = 'ALL'  # Default to keyframe all (loc, rot, scale)

    # Property for accessing the aim distance step now moved to CameraFlyProperties

    def modal(self, context, event):
        # Use the stored root bone instead of the active pose bone
        if not self._root_bone or not self._camera_rig:
            # If somehow we lost the root bone reference, try to get it again
            if hasattr(context.scene, 'camerafly_settings') and context.scene.camerafly_settings.active_camera:
                camera = context.scene.camerafly_settings.active_camera
                self._root_bone = self.get_root_bone(camera)
                if self._root_bone:
                    self._camera_rig = camera.parent

            # If still no root bone, cancel
            if not self._root_bone:
                self.report({'ERROR'}, "Lost reference to root bone")
                self.cancel(context)
                return {'CANCELLED'}

        # Use the stored references
        obj = self._camera_rig
        bone = self._root_bone

        if event.type == 'ESC' or event.type == 'SPACE':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'RIGHTMOUSE':
            print("Right mouse button pressed")
            if self._initial_aim_pos and self._initial_root_pos:
                print("Restoring initial positions")


                self._root_bone.matrix = self._initial_root_pos
                self._aim_bone.location = self._initial_aim_pos

                self.cancel(context)
                return {'CANCELLED'}
            return {'RUNNING_MODAL'}

        # Handle keyframe insertion with 'I' key
        if event.type == 'I' and event.value == 'PRESS':
            # Insert keyframes based on modifier keys
            if self.insert_keyframes(context):
                return {'RUNNING_MODAL'}

        # Handle mouse wheel for aim bone control
        if event.type in ['WHEELUPMOUSE', 'WHEELDOWNMOUSE'] and event.value == 'PRESS':
            if self.move_aim_bone(context, forward=(event.type == 'WHEELUPMOUSE')):
                return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':
            print(event.type)

        if event.value == 'PRESS':
            self.keys_pressed.add(event.type)
        elif event.value == 'RELEASE':
            self.keys_pressed.discard(event.type)

        if event.type == 'TIMER' and context.area:
            if context.mode != 'POSE' or not obj or obj.type != 'ARMATURE':
                self.report({'WARNING'}, "Not in Pose Mode or camera rig not found")
                self.cancel(context)
                return {'CANCELLED'}

            self.last_matrix = bone.matrix_basis.copy()

            # Get local axes from bone's matrix_basis
            local_matrix = bone.matrix_basis.to_3x3()
            forward = local_matrix @ Vector((0, 1, 0))
            right = local_matrix @ Vector((1, 0, 0))
            up = local_matrix @ Vector((0, 0, 1))

            delta = Vector()

            if 'W' in self.keys_pressed:
                delta += forward
            if 'S' in self.keys_pressed:
                delta -= forward
            if 'D' in self.keys_pressed:
                delta += right
            if 'A' in self.keys_pressed:
                delta -= right
            if 'E' in self.keys_pressed:
                delta += up
            if 'Q' in self.keys_pressed:
                delta -= up



            if event.shift and not self.speed_change:
                # Update the scene property directly with new max of 100.0
                if hasattr(bpy.context.scene, 'camerafly_settings'):
                    settings = bpy.context.scene.camerafly_settings
                    settings.move_speed = min(settings.move_speed * 2.0, 100.0)
                    self.speed_change = True
            elif event.ctrl and not self.speed_change:
                # Update the scene property directly with new min of 0.01
                if hasattr(bpy.context.scene, 'camerafly_settings'):
                    settings = bpy.context.scene.camerafly_settings
                    settings.move_speed = max(settings.move_speed * 0.5, 0.01)
                    self.speed_change = True

            if not event.shift and not event.ctrl:
                self.speed_change = False

            if event.alt and not self.rot_mode_change:
                if hasattr(bpy.context.scene, 'camerafly_settings'):
                    settings = bpy.context.scene.camerafly_settings
                    settings.rotation_mode = 'AIM' if settings.rotation_mode == 'CAMERA' else 'CAMERA'
                    self.rot_mode_change = True

            if not event.alt:
                self.rot_mode_change = False

            # if delta.length > 0:
            #     # Apply speed multiplier with Shift/Ctrl
            #     speed = self.move_speed
            #     if event.shift:
            #         speed *= 2.0
            #     elif event.ctrl:
            #         speed *= 0.5
            bone.location += delta.normalized() * self.move_speed

            if not 'Y' in self.keys_pressed and not 'C' in self.keys_pressed:
                self.initial_aim_set = False

            # Handle rotation based on mouse movement
            if not event.type == 'TIMER':
                print(event.type)
        if event.type == 'MOUSEMOVE':
            # Calculate yaw angle based on mouse X movement
            yaw_angle = radians(self.rotate_speed_deg) * (event.mouse_x - event.mouse_prev_x) / 100.0

            # Calculate pitch angle based on mouse Y movement
            pitch_angle = radians(self.rotate_speed_deg) * (event.mouse_y - event.mouse_prev_y) / 100.0

            local_matrix = bone.matrix_basis.to_3x3()
            forward = local_matrix @ Vector((0, 1, 0))
            right = local_matrix @ Vector((1, 0, 0))
            up = local_matrix @ Vector((0, 0, 1))

            if hasattr(bpy.context.scene, 'camerafly_settings'):
                settings = bpy.context.scene.camerafly_settings

                if settings.rotation_mode == 'AIM' and settings.active_camera and settings.active_camera.parent:
                    # In AIM mode, rotate around the aim bone's location
                    rig = settings.active_camera.parent
                    if rig and rig.type == 'ARMATURE' and 'MCH-Aim_shape_rotation' in rig.pose.bones:
                        aim_bone = rig.pose.bones['MCH-Aim_shape_rotation']

                        # Get the initial aim bone position in world space (only once)
                        #if not hasattr(self, '_initial_aim_pos'):
                        #    self._initial_aim_mat = rig.matrix_world @ aim_bone.matrix
                        #    self._initial_aim_pos = self._initial_aim_mat.translation
                        if not self.initial_aim_set:
                            self.initial_aim_set = True
                            self._initial_aim_mat = rig.matrix_world @ aim_bone.matrix
                            self._initial_aim_loc = self._initial_aim_mat.translation
                        # Use the initial position to keep the aim bone fixed
                        aim_pos = self._initial_aim_loc

                        # Get the bone's world matrix and position
                        bone_world = obj.matrix_world @ bone.matrix
                        bone_pos = bone_world.translation

                        # Calculate the offset from the aim bone to the current bone
                        offset = bone_pos - aim_pos

                        # Use world Z axis for yaw rotation
                        yaw_axis = Vector((0, 0, 1))
                        # Use right vector (bone's local X) for pitch rotation in world space
                        pitch_axis = obj.matrix_world.to_3x3() @ right.normalized()

                        # Create rotation matrices
                        yaw_mat = Matrix.Rotation(yaw_angle, 4, yaw_axis)
                        pitch_mat = Matrix.Rotation(-pitch_angle, 4, pitch_axis)

                        # Combine rotations (pitch first, then yaw)
                        combined_rot = yaw_mat @ pitch_mat

                        # Apply combined rotation to the offset
                        rotated_offset = combined_rot @ offset.normalized() * offset.length

                        # Calculate new bone position
                        new_pos = aim_pos + rotated_offset

                        # Convert back to local space
                        new_pos_local = obj.matrix_world.inverted() @ new_pos

                        # Update bone location
                        bone.location = new_pos_local

                        # Restore the aim bone's original position
                        aim_bone.matrix.translation = self._initial_aim_mat.translation

                        # Maintain the bone's rotation relative to the aim bone
                        # by applying the combined rotation to the bone's rotation
                        bone_rot = bone_world.to_quaternion()
                        new_rot = (combined_rot.to_quaternion() @ bone_rot).to_euler()
                        bone.rotation_euler = new_rot

                        # Update the matrix to apply changes
                        bone.matrix_basis = bone.matrix_basis

                        # Skip the default rotation logic
                        context.area.tag_redraw()
                        return {'RUNNING_MODAL'}

            # Default rotation (CAMERA mode or fallback)
            # Apply both yaw (around world Z) and pitch (around local X) rotations
            pivot = Matrix.Translation(bone.location)

            # Get world Z for yaw and local X for pitch
            world_z = Vector((0, 0, 1))  # World Z axis vector for yaw
            pitch_axis = right.normalized()  # Local X axis for pitch

            # Create rotation matrices for yaw and pitch
            yaw_rotation = Matrix.Rotation(-yaw_angle, 4, world_z)
            pitch_rotation = Matrix.Rotation(pitch_angle, 4, pitch_axis)

            # Apply pitch first, then yaw (order matters for correct camera control)
            # This method preserves the bone's pivot point for both rotations
            bone.matrix_basis = pivot @ yaw_rotation @ pitch_rotation @ pivot.inverted() @ bone.matrix_basis

            context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def is_valid_dolly_rig(self, context, camera):
        """Check if the camera is part of a valid Dolly Rig from the Add Camera Rigs addon."""
        if not camera:
            return False

        # Check if the camera has a parent that's a rig
        rig = camera.parent
        if not rig or rig.type != 'ARMATURE':
            return False

        # Check if the rig has the expected bones for a Dolly Rig
        # Must include root bone and aim control bones
        required_bones = {'Root', 'Aim', 'MCH-Aim_shape_rotation'}
        if not all(bone in rig.pose.bones for bone in required_bones):
            return False

        return True

    def get_root_bone(self, camera):
        """Get the root bone of the camera's dolly rig."""
        if not camera or not camera.parent or camera.parent.type != 'ARMATURE':
            return None

        rig = camera.parent
        if 'Root' in rig.pose.bones:
            return rig.pose.bones['Root']

        return None

    def get_aim_bone(self, camera):
        """Get the aim bone of the camera's dolly rig."""
        if not camera or not camera.parent or camera.parent.type != 'ARMATURE':
            return None

        rig = camera.parent
        if 'Aim' in rig.pose.bones:
            return rig.pose.bones['Aim']

        return None

    def invoke(self, context, event):




        # Check for valid Dolly Rig first
        if hasattr(context.scene, 'camerafly_settings') and context.scene.camerafly_settings.active_camera:
            camera = context.scene.camerafly_settings.active_camera
            if not self.is_valid_dolly_rig(context, camera):
                self.report(
                    {'ERROR'},
                    "Selected camera must be part of a valid Dolly Rig from the 'Add Camera Rigs' addon"
                )
                return {'CANCELLED'}

            # Get the root bone of the rig
            self._root_bone = self.get_root_bone(camera)
            if not self._root_bone:
                self.report({'ERROR'}, "Could not find 'root' bone in the dolly rig")
                return {'CANCELLED'}

            # Get the aim bone of the rig
            self._aim_bone = self.get_aim_bone(camera)
            if not self._aim_bone:
                self.report({'ERROR'}, "Could not find 'aim' bone in the dolly rig")
                return {'CANCELLED'}

            # Store the initial positions of the bones
            self._initial_aim_pos = self._aim_bone.location.copy()
            self._initial_root_pos = self._root_bone.matrix.copy()

            # Ensure we're in pose mode
            if context.mode != 'POSE':
                self.report({'WARNING'}, "Must be in Pose Mode to use this tool")
                return {'CANCELLED'}

            # Select the root bone automatically
            rig = camera.parent
            context.view_layer.objects.active = rig

            # Deselect all bones
            for bone in rig.pose.bones:
                bone.bone.select = False

            # Select only the root bone
            self._root_bone.bone.select = True
            rig.data.bones.active = self._root_bone.bone

            # Store references to the camera rig and root bone for use in modal method
            self._camera_rig = rig

            self.report({'INFO'}, "Automatically selected Root bone of dolly rig")
        else:
            self.report({'ERROR'}, "No camera selected")
            return {'CANCELLED'}

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.02, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return {'FINISHED'}

    def insert_keyframes(self, context):
        """Insert keyframes for the bone based on modifier keys.

        Args:
            context: Blender context

        Returns:
            True if keyframes were inserted
        """
        if not self._camera_rig:
            self.report({'ERROR'}, "No bone to keyframe")
            return False

        # Define keyframe types
        keyframe_types = {
            'LOC': 'Location only',
            'ROT': 'Rotation only',
            'SCALE': 'Scale only',
            'ALL': 'Location, Rotation & Scale'
        }
        bones_to_keyframe = [self._root_bone, self._aim_bone]
        # Determine keyframe type based on modifier keys
        keyframe_type = 'ALL'


        # Insert keyframes based on type
        frame = context.scene.frame_current
        for key_bone in bones_to_keyframe:
            if keyframe_type in ['LOC', 'ALL']:
                key_bone.keyframe_insert(data_path='location', frame=frame)

            if keyframe_type in ['ROT', 'ALL']:
                if key_bone.rotation_mode == 'QUATERNION':
                    key_bone.keyframe_insert(data_path='rotation_quaternion', frame=frame)
                else:
                    key_bone.keyframe_insert(data_path='rotation_euler', frame=frame)

            if keyframe_type in ['SCALE', 'ALL']:
                key_bone.keyframe_insert(data_path='scale', frame=frame)


        # Show a message about what was keyframed
        self.report({'INFO'}, f"Inserted keyframe: {keyframe_types[keyframe_type]} at frame {frame}")
        return True

    def move_aim_bone(self, context, forward=True):
        """Move the aim bone forward or backward based on mouse wheel movement.

        Args:
            context: Blender context
            forward: True to move the aim bone forward, False to move it backward

        Returns:
            True if aim bone was moved successfully
        """
        if not self._aim_bone or not self._camera_rig:
            return False

        # Check if we have an active camera and are in AIM mode
        settings = getattr(context.scene, 'camerafly_settings', None)
        if not settings or not settings.active_camera:
            return False

        # Get the camera's forward direction in world space
        aim_matrix = self._aim_bone.matrix_basis
        forward_vec = aim_matrix.to_3x3() @ Vector((0, 1, 0))  # Camera looks down -Z

        # Get aim distance step from scene properties
        aim_step = 0.2  # Default value
        if hasattr(context.scene, 'camerafly_settings'):
            aim_step = context.scene.camerafly_settings.aim_distance_step

        # Calculate the movement amount based on direction
        direction = 1 if forward else -1
        movement = forward_vec.normalized() * aim_step * direction

        # Move the aim bone
        self._aim_bone.location += movement

        # Report the action
        action = "forward" if forward else "backward"
        self.report({'INFO'}, f"Moved aim bone {action} by {aim_step} units")

        return True

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.keys_pressed.clear()
