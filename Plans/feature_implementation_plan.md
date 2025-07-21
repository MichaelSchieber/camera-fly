# CameraFly Add-on Feature Implementation Plan

## Overview
This document outlines the implementation plan for new features in the CameraFly Blender add-on. These features will enhance camera movement controls, add new rotation behaviors, improve usability, and add animation capabilities.

## Features and Implementation Tasks

### 1. Rotation Around World Z Axis
**Description:** Overhaul rotation to use world Z axis instead of local Z axis for more predictable camera movements.

**Implementation Tasks:**
- Modify the `modal()` method in `POSE_OT_move_rotate_bone_local_pivot` class
- Replace local rotation logic with world-space rotation
- Create a world-space rotation matrix using the global Z vector `(0, 0, 1)`
- Update rotation calculations to maintain camera orientation while rotating around world Z
- Test rotation behavior with different camera orientations

**Files to Modify:**
- `ops.py` - Update rotation logic in the operator class

---

### 2. Camera Pitch Control via Mouse Y Movement
**Description:** Add vertical camera rotation (pitch) controlled by mouse Y movement, giving more control over camera angle.

**Implementation Tasks:**
- Add mouse Y-axis movement detection in the `modal()` method
- Create a pitch rotation calculation based on mouse Y delta
- Implement two rotation modes for pitch control:
  1. Camera mode: pitch rotation around the camera's local X axis
  2. Aim mode: pitch rotation around the aim bone, similar to Z rotation
- Apply pitch rotation independently of the world Z rotation
- Support using the same rotation_mode property as Z rotation
- Test combined pitch and yaw rotations in both modes

**Files to Modify:**
- `ops.py` - Add pitch rotation logic to operator with both rotation modes
- `panels.py` - Add UI options for pitch control

---

### 3. Automatic Root Bone Selection
**Description:** Automatically select and move the root bone of the Add Camera Rigs addon's dolly rig to ensure the add-on works correctly regardless of user bone selection.

**Implementation Tasks:**
- Target specifically the 'root' bone of the Add Camera Rigs addon's dolly rig
- Implement a function to verify and select the root bone of the rig
- Add automatic root bone selection when the operator is invoked
- Show clear error message if the root bone cannot be found
- Ensure the add-on only works with the proper dolly rig structure
- Add additional validation checks for the dolly rig structure

**Files to Modify:**
- `ops.py` - Add root bone identification and selection logic
- `panels.py` - Add information about automatic bone selection

---

### 4. Keyframe Creation Shortcut
**Description:** Add functionality to create keyframes for the current camera position with a keyboard shortcut.

**Implementation Tasks:**
- Add a new key detection in the `modal()` method for keyframe creation (e.g., 'I')
- Implement a keyframe insertion function for location, rotation, and scale
- Support different keyframing modes (location only, rotation only, or both)
- Create user feedback when keyframes are inserted
- Ensure keyframes are inserted at the current frame
- Test with animation playback

**Files to Modify:**
- `ops.py` - Add keyframe insertion functionality
- `panels.py` - Add keyframe shortcut information to UI

---

### 5. Aim Bone Control with Mouse Wheel
**Description:** Add the ability to move the aim bone forward and backward using the mouse wheel for quick focal point adjustments.

**Implementation Tasks:**
- Add mouse wheel event detection in the `modal()` method
- Calculate aim bone movement direction based on camera's forward vector
- Implement aim bone translation logic based on wheel rotation
- Add a sensitivity control for wheel movement
- Test with different camera rig setups and aim bones

**Files to Modify:**
- `ops.py` - Add mouse wheel event handling and aim bone movement
- `panels.py` - Add mouse wheel shortcut information and sensitivity controls

---

### 6. UI Updates
**Description:** Update the UI to reflect the current state of the tools and all new features.

**Implementation Tasks:**
- Streamline the UI organization to better group related controls
- Update all shortcut descriptions to accurately reflect implemented changes:
  - World Z axis rotation instead of local rotation
  - Mouse-based camera pitch control
  - Mouse wheel aim bone control
  - Keyframe insertion with 'I' key and modifiers
- Add visual indicators for:
  - Current rotation mode (CAMERA vs. AIM)
  - Automatic Root bone selection status
  - Active camera selection
  - Current keyframe type being used
- Add a settings section with all user-adjustable properties:
  - Movement speed
  - Rotation speed
  - Aim distance step for mouse wheel
- Create a tabbed interface to separate:
  - Movement controls
  - Rotation controls
  - Animation controls
  - Settings
- Add help tooltips for all controls
- Ensure consistent spacing and alignment throughout the panel
- Add responsive UI elements that update based on current state
- Implement visual feedback for keyframing and aim bone movement
- Test UI with different Blender themes and screen resolutions

**Files to Modify:**
- `panels.py` - Comprehensive update of UI components and layout
- `ops.py` - Add additional state properties for UI feedback

---

## Implementation Phases

### Phase 1: Core Rotation and Movement Changes
- Implement world Z rotation (Feature 1)
- Add pitch control (Feature 2)
- Update mouse movement handling

### Phase 2: Usability Improvements
- Add automatic root bone selection (Feature 3)
- Implement mouse wheel aim control (Feature 5)

### Phase 3: Animation and UI Enhancements
- Add keyframe shortcut functionality (Feature 4)
- Complete UI updates (Feature 6)
- Final testing and refinement

## Testing Procedure
For each feature:
1. Test with standard camera object
2. Test with camera rigs (especially Dolly Rig)
3. Verify behavior in different Blender viewport modes
4. Check for unexpected interactions with other Blender features
5. Verify UI responsiveness and feedback

## Estimated Completion Time
- Phase 1: 2-3 days
- Phase 2: 2 days
- Phase 3: 2-3 days
- Testing and refinement: 2 days

Total estimated time: 8-10 days
