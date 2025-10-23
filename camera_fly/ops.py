import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty
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
    _camera_bone = None

    # Store the last keyframe type
    _last_keyframe_type = 'ALL'  # Default to keyframe all (loc, rot, scale)

    _forward = None
    _right = None
    _up = None
    _local_matrix = None
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


        if event.type == 'LEFTMOUSE' or event.type == 'SPACE':
            self.cancel(context)
            self.report({'INFO'}, "Accepted changes")
            return {'FINISHED'}

        if event.type == 'RIGHTMOUSE' or event.type == 'ESC':
            print("Right mouse button pressed")
            if self._initial_aim_pos and self._initial_root_pos:
                print("Restoring initial positions")

                print("self._initial_root_pos", self._initial_root_pos)
                print("self._initial_camera_pos", self._initial_camera_pos)
                print("self._initial_aim_pos", self._initial_aim_pos)
                
                self._root_bone.matrix_basis = self._initial_root_pos
                #print("self._root_bone.matrix", self._root_bone.matrix)
                print("self._camera_bone.matrix", self._camera_bone.matrix)
                self._camera_bone.matrix_basis = self._initial_camera_pos
                print("self._camera_bone.matrix", self._camera_bone.matrix)
                self._aim_bone.matrix_basis = self._initial_aim_pos
                #print("self._aim_bone.matrix", self._aim_bone.matrix)
                

                self.cancel(context)
                self.report({'INFO'}, "Reversed changes")
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
            if context.mode != 'POSE' or not self._camera_rig or self._camera_rig.type != 'ARMATURE':
                self.report({'WARNING'}, "Not in Pose Mode or camera rig not found")
                self.cancel(context)
                return {'CANCELLED'}

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
            
            self.move_cam_mode(context)

            if not 'Y' in self.keys_pressed and not 'C' in self.keys_pressed:
                self.initial_aim_set = False

            # Handle rotation based on mouse movement
            if not event.type == 'TIMER':
                print(event.type)
        if event.type == 'MOUSEMOVE':


            self.rotate_cam_mode(context, event)
            return {'RUNNING_MODAL'}
            

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
    
    def get_camera_bone(self, camera):
        """Get the camera bone of the camera's dolly rig."""
        if not camera or not camera.parent or camera.parent.type != 'ARMATURE':
            return None

        rig = camera.parent
        if 'Camera' in rig.pose.bones:
            return rig.pose.bones['Camera']

        return None
    
    def prepare_scene(self, camera):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        rig = camera.parent
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        rig.pose.bones["Camera"].constraints["Track To"].influence = 1
        bpy.ops.object.mode_set(mode='POSE')

    def invoke(self, context, event):

        self.prepare_scene(context.scene.camerafly_settings.active_camera)

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
            
            # Get the camera bone of the rig
            self._camera_bone = self.get_camera_bone(camera)
            if not self._camera_bone:
                self.report({'ERROR'}, "Could not find 'camera' bone in the dolly rig")
                return {'CANCELLED'}

            # Store the initial positions of the bones
            self._initial_aim_pos = self._aim_bone.matrix_basis.copy()
            self._initial_root_pos = self._root_bone.matrix_basis.copy()
            self._initial_camera_pos = self._camera_bone.matrix_basis.copy()

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
        bones_to_keyframe = [self._camera_bone, self._aim_bone]
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
        aim_matrix = self._camera_bone.matrix
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
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def move_root_bone(self, context):
        self.last_matrix = self._root_bone.matrix_basis.copy()

        # Get local axes from bone's matrix_basis
        local_matrix = self._root_bone.matrix_basis.to_3x3()
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
        
        self._root_bone.location += delta.normalized() * self.move_speed

    def move_cam_mode(self, context):
        self.last_matrix_camera = self._camera_bone.matrix_basis.copy()
        self.last_matrix_aim = self._aim_bone.matrix_basis.copy()

        self.set_directions(self._camera_bone)
        delta = self.get_delta()
        self.translate_bone(self._camera_bone, delta)
        self.translate_bone(self._aim_bone, delta)

    def rotate_cam_mode(self, context, mouse_event):
        self.set_angles(mouse_event)
        self.set_directions(self._camera_bone)
        if bpy.context.scene.camerafly_settings.rotation_mode == 'AIM':
            self.rotate_around_bone(self._camera_bone, self._aim_bone)
        else:
            self.rotate_around_bone(self._aim_bone, self._camera_bone, invert_yaw = True, invert_pitch = True)
    
    def rotate_around_bone(self, bone_a, bone_b, invert_yaw = False, invert_pitch = False):
        # rotates bone a around bone b (only location)
        bone_a_mat_world = self._camera_rig.matrix_world @ bone_a.matrix
        bone_b_mat_world = self._camera_rig.matrix_world @ bone_b.matrix
        
        bone_a_loc_world = bone_a_mat_world.translation
        bone_b_loc_world = bone_b_mat_world.translation

        offset_world = bone_a_loc_world - bone_b_loc_world
        print(offset_world)

        # set axes to rotate around in world space
        # World Z axis for yaw rotation
        yaw_axis = Vector((0, 0, 1))

        # right vector (bone's local X) converted to world space for pitch rotation
        pitch_axis = self._camera_rig.matrix_world.to_3x3() @ self._right.normalized()

        # Create rotation matrices
        yaw_mat = Matrix.Rotation(self._yaw_angle if not invert_yaw else -self._yaw_angle, 4, yaw_axis)
        pitch_mat = Matrix.Rotation(-self._pitch_angle if not invert_pitch else self._pitch_angle, 4, pitch_axis)

        # Combine rotations (pitch first, then yaw)
        combined_rot = yaw_mat @ pitch_mat

        # Apply combined rotation to the offset
        rotated_offset = combined_rot @ offset_world.normalized() * offset_world.length #Couldnt this just be offset? Normalize and multiply by length cancels each other out?
        print("rotated offset", rotated_offset)
        # Calculate new bone position
        new_pos_world = bone_b_loc_world + rotated_offset

        # Convert back to local space
        new_pos_local = self._camera_rig.matrix_world.inverted() @ new_pos_world
        print("new pos local", new_pos_local)

        pose_bone_offset = bone_a.matrix.translation - bone_a.matrix_basis.translation
        print("pose bone offset", pose_bone_offset)
        # Update bone location
        bone_a.location = new_pos_local - pose_bone_offset        
    
    def set_directions(self, bone):
        self._local_matrix = bone.matrix.to_3x3()
        self._forward = self._local_matrix @ Vector((0, 1, 0))
        self._right = self._local_matrix @ Vector((1, 0, 0))
        self._up = self._local_matrix @ Vector((0, 0, 1))
    
    def set_angles(self, mouse_event):
        # Calculate yaw angle based on mouse X movement
        self._yaw_angle = radians(self.rotate_speed_deg) * (mouse_event.mouse_x - mouse_event.mouse_prev_x) / 100.0

        # Calculate pitch angle based on mouse Y movement
        self._pitch_angle = radians(self.rotate_speed_deg) * (mouse_event.mouse_y - mouse_event.mouse_prev_y) / 100.0
    
    def translate_bone(self, bone, delta):
        bone.location += delta.normalized() * self.move_speed
    
    def get_delta(self):
        delta = Vector()
        if 'W' in self.keys_pressed:
            delta += self._forward
        if 'S' in self.keys_pressed:
            delta -= self._forward
        if 'D' in self.keys_pressed:
            delta += self._right
        if 'A' in self.keys_pressed:
            delta -= self._right
        if 'E' in self.keys_pressed:
            delta += self._up
        if 'Q' in self.keys_pressed:
            delta -= self._up
        return delta